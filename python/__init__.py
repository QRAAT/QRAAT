#
# Copyright 2008,2009 Free Software Foundation, Inc.
#
# This application is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# This application is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

'''
This is the Python ``qraat`` module, comprising our application programming
interface. *This doc string is in python/__init__.py*. 
'''

#: Create an enumerated type as a Python class. 
def enum(*sequential, **named):
  enums = dict(zip(sequential, range(len(sequential))), **named)
  Enum = type('Enum', (), enums)
  return Enum

#: Convert table cell value to a pretty string suitable for displaying.
def pretty_printer(val):
  if type(val) in [float, np.float64]:
    if len(str(val)) > 6: 
      return '{0:e}'.format(val)
    else: return str(val)
  elif type(val) == time.struct_time: 
    return time.strftime("%Y-%m-%d %H:%M:%S", val)
  elif val == None: 
    return '' 
  else:
    return str(val)

from csv import * 
from det import det 
from est import est, data_arrays, est_data

