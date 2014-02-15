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
    self.c_size   = 1
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
      x.c_size   += y.c_size
      p = x

    elif (x.c_height > y.c_height): # x is taller than y.
      y.c_parent = x
      x.c_size  += y.c_size
      p = x

    else: # y is taller than x.
      x.c_parent = y
      y.c_size  += x.c_size
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
                    ORDER BY timestamp''' % (t_start, t_end, tx_id))
    
    pos = cur.fetchall()
    nodes = [node(i) for i in range(len(pos))]

    # Index and size of largest component. 
    m_p = None; m_size =  0
    edge_ct = 0

    # Add feasible edges to graph, keeping track of largest component. 
    for i in range(len(pos)):
      Pi = np.complex(pos[i][3], pos[i][4])
      for j in range(i+1, len(pos)):  
        Pj = np.complex(pos[j][3], pos[j][4])
        if dist(Pj, Pi) / (float(pos[j][2]) - float(pos[i][2])) < max_speed: 
          edge_ct += 1
          nodes[i].adj.append(j) # If there is only one calculation per unit
                                 # time, finding the largest component may 
                                 # suffice. 
          p = nodes[i].c_union(nodes[j])
          if p.c_size > m_size:
            m_p    = p
            m_size = p.c_size
    
    print m_size, "/", len(pos), "[%d]" % m_p.c_height, "edges=%d" % edge_ct

    # TODO Enumerate positions in largest component, plot them. 





if __name__ == '__main__': 
  
  db_con = util.get_db('reader')

  t_start = 1376420800.0
  t_end   = 1376442000.0
  t_end_short = 1376427800.0 # short
  cal_track = track(db_con, t_start, t_end, 51, 0.201) 

  import matplotlib.pyplot as pp

  # Plot sites.
  sites = csv(db_con=db_con, db_table='sitelist')
  pp.plot(
   [s.easting for s in sites], 
   [s.northing for s in sites], 'ro')

  # Plot locations. 
  #pp.plot( 
  # map(lambda (t, e, n, ll): e, pos_est), 
  # map(lambda (t, e, n, ll): n, pos_est), '.', alpha=0.3)

  pp.show()


        
     


