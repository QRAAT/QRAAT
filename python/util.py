# util.py -- Various functions. This file is part of QRAAT, an 
# automated animal tracking system based on GNU Radio. 
#
# Copyright (C) 2013 Sean Riddle, Christopher Patton
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

import MySQLdb as mdb
import os 
from csv import csv


def remove_field(l, i):
  ''' Provenance function. *TODO* '''  
  return tuple([x[:i] + x[i+1:] for x in l])

def get_field(l, i):
  ''' Provenance function. *TODO* '''  
  return tuple([x[i] for x in l])


def enum(*sequential, **named):
  """ 
    Create an enumerated type as a Python class. For example, see
  """
  enums = dict(zip(sequential, range(len(sequential))), **named)
  Enum = type('Enum', (), enums)
  return Enum


def get_db(view):
  ''' Get database credentials. ''' 
  try:
    db_config = csv("%s/db_auth" % os.environ['RMG_SERVER_DIR']).get(view=view)

  except KeyError:
    print >>sys.stderr, "position: error: undefined environment variables. Try `source rmg_env.`"
    sys.exit(1)

  except IOError, e:
    print >>sys.stderr, "position: error: missing DB credential file '%s'." % e.filename
    sys.exit(1)

  # Connect to the database.
  db_con = mdb.connect(db_config.host,
                       db_config.user,
                       db_config.password,
                       db_config.name)
  return db_con
  
