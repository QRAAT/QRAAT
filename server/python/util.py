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

import os, sys
import qraat
import time, datetime

def remove_field(l, i):
  ''' Provenance function. *TODO* '''  
  return tuple([x[:i] + x[i+1:] for x in l])

def get_field(l, i):
  ''' Provenance function. *TODO* '''  
  return tuple([x[i] for x in l])

def get_db(view):
  ''' Get database credentials. ''' 

  try:
    db_config = qraat.csv.csv(os.environ['RMG_SERVER_DB_AUTH']).get(view=view)
    
    # Connect to the database.
    db_con = mdb.connect(db_config.host,
                         db_config.user,
                         db_config.password,
                         db_config.name)
    return db_con

  except KeyError:
    raise qraat.error.QraatError("undefined environment variables. Try `source rmg_env`")

  except IOError, e:
    raise qraat.error.QraatError("missing DB credential file '%s'" % e.filename)


def datetime_to_timestamp(string): 
  return time.mktime(datetime.datetime.strptime(
          string, '%Y-%m-%d %H:%M:%S').timetuple())

def timestamp_to_datetime(t): 
  return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(t)) 
