#!/usr/bin/python
# sitelist.py
# Input a CSV formatted site list on STDIN, return an entry or 
# modify the file and output to STDOUT. This script is part of the 
# QRAAT system. 
#
# Copyright (C) 2013 Christopher Patton
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import sys

if len(sys.argv) < 3 or len(sys.argv) > 4:
  print >> sys.stderr, "usage: sitelist <site> <parameter> [<value>]" 
  sys.exit(1)

sys.argv.append(None)

(row, col, value) = sys.argv[1:4]

headers = sys.stdin.readline().strip().split(',')
print headers
header = { headers[i] : i for i in range(len(headers)) }

if value: 
  print ','.join(headers)

for line in sys.stdin.readlines(): 
  line = line.strip().split(',')
  try: 
    if value == None and line[header["name"]] == row: # Just get value
      print line[header[col]]
      sys.exit(0)
    elif value: 
      if line[header["name"]] == row:
        line[header[col]] = value
      print ','.join(line)
  except IndexError: 
    pass

if value == None: # If we got here, site doesn't appear in site list
  sys.exit(1)
else:
  sys.exit(0)