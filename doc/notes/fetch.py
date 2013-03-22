#!/usr/bin/python
# Chris ~15 Feb 2013
#
# The pulse detector in the RMG module emits .det files into a directory 
# structure like YYYY/MM/DD/HH/mm/ssuuuuuu.det. We want to be able to copy 
# these files from RMG remotes to the server, but exclude the directory 
# that is being mutated. 
# 
# One solution would be to implement a hot-directory locking mechanism on 
# the RMG remote side. Since we don't want to burden the site computers 
# with this extra work, we decided to take advantage of the fact that the 
# real clock time must be synchronized across all nodes of the network. 
# We fetch all directories that are older than one minute because the  
# pulse detector will never mutate these directories again.  
# 
# Read a list of directories, typically 'find -type d', and output all 
# .det containing directories that are atleast one minute old.
#
# 20 Feb 2013: Modified this program to combine directories that are not
#  hot. This improves the efficiency of scp, since TCP connections 
#  remain persistent for a large group of files. 
# 

import os, re, time, sys

class Tree: 
# Correpsonds to a directory tree. A node is marked as hot if one of 
# its children is marked hot. copiable() outputs all subdirectories that 
# are not hot. 

  def __init__(self, parent=None, hot=False):
    self.hot = hot
    self.parent = parent
    self.children = {}
  
  def insert(self, branch, hot): 
  # insert a branch
    if not self.hot and hot:  # if hot once, hot forever
      self.hot = hot
    if branch == []:
      return
    else:
      try:  
        self.children[branch[0]].insert(branch[1:], hot)
      except KeyError: 
        self.children[branch[0]] = Tree(self)
        self.children[branch[0]].insert(branch[1:], hot)        

  def display(self):
    names = self.children.keys()
    if len(names) > 0:
      for name in names:
        print name,
      print
      for name in names: 
        print "%s[hot=%s]:" % (name, self.children[name].hot)
        self.children[name].display()
      print

  def copiable(self, directory=None): 
  # emit non-hot, i.e. copiable,  directories.
    if self.parent == None: # root directory
      (name, child) = (self.children.keys()[0], self.children.values()[0])
      child.copiable(directory + "/" + name)
    elif self.hot == False: # no children hot, this whole directory can be copied
      print directory
    else:                   # directory has a hot child, recurse
      for (name, child) in self.children.iteritems():
        child.copiable(directory + "/" + name)


prog = re.compile("([0-9]{4})(\/([0-9]{2})){4}") 

now = time.localtime(time.time() - (120)) # Exclude last two minutes, actually. This 
                                          # is to account for possible synchronization 
                                          # issues-up to one minute of clock slippage. 
                                        
t = [now.tm_year, now.tm_mon, now.tm_mday, now.tm_hour, now.tm_min]

tree = Tree()

for line in sys.stdin.readlines():
  if prog.search(line): 
    
    # Fetch if directory is sufficiently old. 
    d = line.strip().split("/")
    ts = map(lambda n: int(n), d[1:])
    fetch = True
    for i in range(len(ts)):
      if ts[i] < t[i]: break
      elif ts[i] > t[i]: 
        fetch = False
        break 

    tree.insert(d[1:], hot=not fetch)

tree.copiable(d[0])

