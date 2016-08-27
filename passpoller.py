#!/usr/bin/env python
"""Interface program between WSDOT pass RSS feeds and IRSSINotifier.

Periodically polls the WSDOT pass RSS feed. When road conditions change, the
RSS feed is dumped to IrssiNotifier (http://irssinotifier.appspot.com) via
Google Cloud Messaging (GCM). Multiple IrssiNotifier API tokens are supported
allowing a single server to provide notifications to multiple Android devices.

Author: Jeff Heidel
"""
from BeautifulSoup import BeautifulSoup
import collections
import feedparser
import logging
import sys
from time import sleep
import yaml

import irssi_post
import multi_notifier


def parse_pass_rss(txt):
  """Parses a WSDOT pass summary block into a python ordered dict."""
  soup = BeautifulSoup(txt)
  lines = soup.contents

  # Indicies of heading lines
  strongs = [i for i, t in list(enumerate(lines))
             if getattr(t, 'name', None) == 'strong']

  # Chunkify lines based on heading lines
  chunk_bounds = zip(strongs, strongs[1:] + [len(lines)])
  chunks = [lines[start:end] for start,end in chunk_bounds]

  # Convert a chunk into a key value pair using fairly arbitary semicolon
  # parsing (silly wsdot...)
  def chunk_to_kv(c):
    head, tail = '', ''
    node_text = lambda n: str(getattr(n, 'text', n))
    if len(c) >= 1:
      s = node_text(c[0]).split(':')
      head += s[0]
      if len(s) > 1:
        tail += ' '.join(s[1:])
    if len(c) >= 2:
      tail += ' '.join(node_text(l) for l in c[1:])
    return head.upper().strip(), tail.strip()

  return collections.OrderedDict(chunk_to_kv(c) for c in chunks)


class PassParser(object):
  """Manages a wsdot URL and handles fetching and parsing.
  
  Duplicates are filtered out by keeping history.
  """

  def __init__(self, url):
    self.url = url
    self.hist = []

  def get(self):
    feed = feedparser.parse(self.url)['entries'][0]
    key = feed.id
    data = parse_pass_rss(feed.summary)
    if key in self.hist:
      return None
    else:
      logging.debug('Appending key %s to history', key)
      self.hist.append(key)
      return data


class PassDiffer(object):
  """Checks for diffs between a new and old pass report."""

  KEYS = ['EASTBOUND', 'WESTBOUND']
  
  def __init__(self, initial_diff=False):
    """Initializer.
    
    Args:
      initial_diff: Whether to consider the first check new update.
    """
    self.last = None
    self.skip = not initial_diff

  def map(self, new_data):
    return [new_data.get(k, None) for k in self.KEYS]

  def check(self, new_data):
    m = self.map(new_data)

    has_diff = (m != self.last) and not self.skip

    self.skip = False
    self.last = m

    if has_diff:
      logging.debug('Differ returning true; value is %s', m)
    return has_diff


def format(d):
  """Pretty prints a wsdot ordered dict."""
  return '\n' + '\n'.join('%s: %s' % (k,v) for k, v in d.iteritems())


def Poll(config_file):
  """Main passpoller loop."""
  logging.basicConfig(
      filename='passpoller.log', level=logging.DEBUG,
      format=('%(asctime)s.%(msecs)d %(levelname)s %(module)s - %(funcName)s: '
              '%(message)s'),
      datefmt='%Y-%m-%d %H:%M:%S')

  logging.info('Loading poller config from %s', config_file)
  with open(config_file, 'r') as f:
    config = yaml.load(f)
  logging.info('Successfully loaded config.')
  logging.debug('Config loaded: %s', config)

  parser = PassParser(config['wsdot_url'])
  differ = PassDiffer(initial_diff=False)

  notifier = multi_notifier.MultiNotifier(
      notifiers=[
          irssi_post.IrssiNotifier(n['api_token'], n['password'])
          for n in config['notifiers']
      ],
  )

  logging.info('Starting pass polling for %s on URL %s',
      config['passname'], config['wsdot_url'])
  while True:
    try:
      data = parser.get()
      if data is not None:
        logging.debug('New Data, checking for diff.')
        if differ.check(data):
          txt = format(data)
          logging.info('New %s pass update: %s', config['passname'], txt)
          notifier.send(txt, chan='#%s' % config['passname'], nick='wsdot')
          logging.info('Notification complete.')
    except Exception as e:
      logging.error('Exception: ' + str(e))

    sleep(config['poll_interval_sec'])


if __name__ == '__main__':
  if len(sys.argv) < 2:
    print 'Usage: python passpoller.py [path to config.yaml]'
    sys.exit(1)
  Poll(sys.argv[1])
