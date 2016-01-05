# Pass Poller

An interface program between IrssiNotifier and WSDOT mountain pass RSS feeds.

This program periodically polls WSDOT RSS feeds for road condition changes.
When updated, notifications are sent to IrssiNotifier. IrssiNotifier uses GCM
(Google Cloud Messaging) to deliver notifications to Android phones for timely,
low power updates of changing road conditions.

## Setup

### Phone Side
Follow instructions on https://irssinotifier.appspot.com/. Ensure the Android
device registers as "working" on the profile tab.

### Server Side
Modify config.yaml. Copy the API token from the profile tab and set an
encryption password if configured in the app (default is "password"). You may
also wish to update the RSS feed URL. Currently only support for WSDOT pass
urls is supported.
