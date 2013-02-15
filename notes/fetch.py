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
# 

import os, re, time, sys

prog = re.compile(".*([0-9]{4})\/([0-9]{2})\/([0-9]{2})\/([0-9]{2})\/([0-9]{2}).*") 

now = time.localtime(time.time() - 120) # Exclude last two minutes, actually. This 
                                        # is to account for possible synchronization 
                                        # issues-up to one minute of clock slippage. 
                                        
t = [now.tm_year, now.tm_mon, now.tm_mday, now.tm_hour, now.tm_min]

for line in sys.stdin.readlines():
  m = prog.match(line)
  if m: 
    
    # Fetch if directory is sufficiently old. 
    ts = map(lambda n: int(n), m.group(1,2,3,4,5))
    fetch = True
    for i in range(5):
      if ts[i] < t[i]: break
      elif ts[i] > t[i]: 
        fetch = False
        break 

    # Emit whole directory
    if fetch:
      print line.strip()




