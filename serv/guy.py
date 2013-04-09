from HTMLParser import HTMLParser
import sys

class PBRelayStatus(HTMLParser): 

  relay = None
  state = None
  relays = {}

  def handle_starttag(self, tag, attrs): 
    if tag == "select": 
      for (attr, value) in attrs:
        if attr == "name":
          self.relay = value[5:] # 'Relay'

    elif tag == "option" and self.relay:
      for (attr, value) in attrs: 
        if attr == 'value': 
          self.state = value
        elif attr == 'selected': 
          self.relays[self.relay] = self.state

  def handle_endtag(self, tag):
    if tag == "select": 
      self.relay = None

    elif tag == "option" and self.relay:
      self.state = None

  def handle_data(self, data):
    pass

parser = PBRelayStatus()
parser.feed(sys.stdin.read())
print parser.relays
