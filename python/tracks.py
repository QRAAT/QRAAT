# tracks.py
#
# Copyright (C) 2014 Christopher Patton
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

import numpy as np
import time, os, sys
import random

import util
from csv import csv

try:
  import MySQLdb as mdb
except ImportError: pass

def dist(Pi, Pj): 
  ''' Euclidean distance between points Pi and Pj. ''' 
  return np.sqrt((Pi.real - Pj.real)**2 + (Pi.imag - Pj.imag)**2)


class node: 

  def __init__(self, index): 
    self.c_parent = None
    self.c        = [index]
    self.c_height = 0
    self.index = index
    self.visited = False
    self.adj = []

  def c_find(self):
    p = self
    while (p.c_parent != None): 
      p = p.c_parent
    return p

  def c_union(self, u): 
    x = self.c_find()
    y = u.c_find()

    if (x == y): # This and u are in the same component. 
      p = x
    
    elif (x.c_height == y.c_height): # x and y have the same height.
      y.c_parent  = x
      x.c_height += 1
      x.c        += y.c
      p = x

    elif (x.c_height > y.c_height): # x is taller than y.
      y.c_parent = x
      x.c       += y.c
      p = x

    else: # y is taller than x.
      x.c_parent = y
      y.c       += x.c
      p = y
      
    return p


class track:
  ''' Track.

  :param max_speed: Maximum foot speed of target (m/s). 
  :type max_speed: float
  '''

  def __init__(self, db_con, t_start, t_end, tx_id, max_speed):
    # TODO Assumming (n, e) in meters for the moment.

    cur = db_con.cursor()
    cur.execute('''SELECT ID, txID, timestamp, northing, easting, likelihood
                     FROM Position
                    WHERE (%f <= timestamp) AND (timestamp <= %f)
                      AND txid = %d
                    ORDER BY timestamp ASC''' % (t_start, t_end, tx_id))
    
    pos = cur.fetchall()
    
    # Average.
    mean_speed = 0;
    for i in range(len(pos)-1): 
      Pi = np.complex(pos[i][3], pos[i][4])
      Pj = np.complex(pos[i+1][3], pos[i+1][4])
      t_delta = float(pos[i+1][2]) - float(pos[i][2])
      assert t_delta > 0
      mean_speed += dist(Pi, Pj) / t_delta

    mean_speed /= len(pos)

    # NOTE This approach seems to be reasonable for one candidate per time 
    #  unit. 
    
    # Standard deviation.
    #stddev_speed = 0
    #for i in range(len(pos)-1): 
    #  Pi = np.complex(pos[i][3], pos[i][4])
    #  Pj = np.complex(pos[i+1][3], pos[i+1][4])
    #  t_delta = float(pos[i+1][2]) - float(pos[i][2])
    #  assert t_delta > 0
    #  stddev_speed += ((dist(Pi, Pj) / t_delta) - mean_speed) ** 2
    #stddev_speed = np.sqrt(stddev_speed / len(pos))
    #print (mean_speed, stddev_speed)
    
    tracks = [[ (np.complex(pos[0][3], pos[i][4]), float(pos[0][2])) ]]
    for i in range(1, len(pos)): 
      P_i = np.complex(pos[i][3], pos[i][4])
      t_i = float(pos[i][2])
      guy = False
      for track in tracks:
        (P_j, t_j) = track[-1]
        assert (t_i - t_j > 0)
        if dist(P_j, P_i) / (t_i - t_j) <= mean_speed/1:
          track.append( (P_i, t_i) )
          guy = True
          break
      if not guy: 
        tracks.append( [(P_i, t_i)] )

    print [ len(track) for track in tracks ]

    m_track = None
    m_size = 0
    for track in tracks:
      if len(track) > m_size:
        m_track = track
        m_size = len(track)

    self.track = m_track
 


  def dfs(self, v):
    S = [v]; 
    while (len(S) != 0): 
      u = S.pop()
      if not u.visited: 
        u.visited = True
        for i in u.adj:
          S.append(self.nodes[i])



if __name__ == '__main__': 
  
  db_con = util.get_db('reader')

  (t_start, t_end, tx_id) = (1376420800.0, 1376442000.0, 51)
  t_end_short = 1376427650.0 # short

  (t_start_feb2, t_end_feb2, tx_id_feb2) = (1391390700.638165, 1391396399.840252, 54)

  fella = track(db_con, t_start, t_end, tx_id, 4.4)
  # With max_spaeed = 0.201, results are strange. 
  # I expect see the largest component to be free of most 
  # the false estimations. Instead I'm seeing a range of 
  # values along the path missing. TODO

  import matplotlib.pyplot as pp

  # Plot sites.
  sites = csv(db_con=db_con, db_table='sitelist')
  pp.plot(
   [s.easting for s in sites], 
   [s.northing for s in sites], 'ro')

  # Plot locations. 
  pp.plot( 
   map(lambda (P, t): P.imag, fella.track), 
   map(lambda (P, t): P.real, fella.track), '.', alpha=0.3)

  pp.show()


        
     


