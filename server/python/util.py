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
import numpy as np

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
  except KeyError:
    raise qraat.error.QraatError("undefined environment variables. Try `source rmg_env`")
  except IOError, e:
    raise qraat.error.QraatError("missing DB credential file '%s'" % e.filename)
    
  # Connect to the database.
  db_con = mdb.connect(db_config.host,
                       db_config.user,
                       db_config.password,
                       db_config.name)
  return db_con


def datetime_to_timestamp(string): 
  return time.mktime(datetime.datetime.strptime(
          string, '%Y-%m-%d %H:%M:%S').timetuple())

def timestamp_to_datetime(t): 
  return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(t)) 


### Common miscellaneous computations. ########################################

def compute_time_windows(t_start, t_end, t_step, t_window):
  half = t_window / 2.0
  t_start = int(t_start + half); t_end = int(t_end - half) + 1
  for i in range(t_start - (t_start % t_step), 
                 t_end, 
                 t_step):
    yield (i - half, i + half)


### Common database accessors. ################################################

def get_center(db_con):
  ''' Get the center defined in the database. '''
  cur = db_con.cursor()
  cur.execute('''SELECT northing, easting, utm_zone_number, utm_zone_letter
                   FROM qraat.location
                  WHERE name = 'center' ''')
  (n, e, number, letter) = cur.fetchone()
  return np.complex(n, e), (number, letter)

def get_sites(db_con):
  ''' Get receiver locations defined in the database. 
      
    Return a map from site ID's to positions.
  '''
  cur = db_con.cursor()
  cur.execute('''SELECT ID, northing, easting
                   FROM qraat.site''')
  sites = {}
  for (id, n, e) in cur.fetchall():
    sites[int(id)] = np.complex(n, e)
  return sites

def get_utm_zone(db_con):
  ''' Get UTM zone of receiver locations. 
    
    Assert that all of the sites have the same zone. 
  '''
  cur = db_con.cursor()
  cur.execute('''SELECT utm_zone_number, utm_zone_letter
                   FROM qraat.site''')
  rows = cur.fetchall()
  (number, letter) = rows[0]
  for row in rows:
    assert row == (number, letter)
  return (number, letter)
