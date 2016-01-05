import threading

class MultiNotifier(object):
  """Multithreaded notifier implementation."""
  
  def __init__(self, notifiers):
    self.notifiers = notifiers

  def send(self, *args, **kwargs):
    threads = [threading.Thread(target=n.send, args=args, kwargs=kwargs)
               for n in self.notifiers]
    for t in threads:
      t.start()
    for t in threads:
      t.join()

