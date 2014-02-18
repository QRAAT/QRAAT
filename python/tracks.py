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


class Node: 

  def __init__(self, P, t, ll): 
    self.c_parent = None
    self.c_size   = 1
    self.c_height = 0
    self.P = P
    self.t = t
    self.ll = ll
    self.visited = False
    self.adj = []
    self.children = []

  def dfs(self):
    S = [self]; 
    ct = 0
    while (len(S) != 0): 
      u = S.pop()
      if not u.visited: 
        u.visited = True
        ct += 1
        for v in u.adj:
          S.append(v)
    return ct

  def dist (self, aNode):
    return dist(self.P, aNode.P)

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
        if dist(P_j, P_i) / (t_i - t_j) <= mean_speed/2:
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
 

class track2:

  ''' Track2.

  :param max_speed: Maximum foot speed of target (m/s). 
  :type max_speed: float
  '''

  def __init__(self, db_con, t_start, t_end, tx_id, max_speed):
    cur = db_con.cursor()
    cur.execute('''SELECT ID, txID, timestamp, northing, easting, likelihood
                     FROM Position
                    WHERE (%f <= timestamp) AND (timestamp <= %f)
                      AND txid = %d
                    ORDER BY timestamp ASC''' % (t_start, t_end, tx_id))
    
    pos = cur.fetchall()
    
    # Average speed.
    mean_speed = 0;
    for i in range(len(pos)-1): 
      Pi = np.complex(pos[i][3], pos[i][4])
      Pj = np.complex(pos[i+1][3], pos[i+1][4])
      t_delta = float(pos[i+1][2]) - float(pos[i][2])
      assert t_delta > 0 # TODO 
      mean_speed += dist(Pi, Pj) / t_delta
    mean_speed /= len(pos)

    # Build tracks DAG.
    nodes = []
    roots = []; leaves = []
    i = 0 
    while i < len(pos):
      
      j = i
      Tj = Ti = float(pos[i][2])
      while j < len(pos) and (Ti - Tj == 0): # Candidates for next time interval. 
        (Pj, Tj, ll) = (np.complex(pos[j][3], pos[j][4]), float(pos[j][2]), float(pos[j][5]))

        node = Node(Pj, Tj, ll)
        nodes.append(node)
        ok = False
        for k in range(len(leaves)):
          if leaves[k].dist(node) / (node.t - leaves[k].t) < mean_speed: 
            ok = True
            node.adj.append(leaves[k])
            leaves[k].children.append(node)
        
        if not ok: # New root. 
          roots.append(node) 
          leaves.append(node)

        j += 1
  
      # Recalculate leaves. 
      newLeaves = []
      for u in leaves:
        if len(u.children) == 0: 
          newLeaves.append(u)
        else: 
          for v in u.children:
            if v not in newLeaves:
              newLeaves.append(v)
      leaves = newLeaves

      i = j

    # I observed that the number of leaves is generally smaller than 
    # the number of roots. Reverse the direction of the edges (using
    # node.adj as the adjacency list) and find the path with the 
    # highest likelihood. TODO  
    for leaf in leaves: 
      print leaf.dfs()
      for node in nodes:
        node.visited = False

    print len(roots)
    print len(leaves)
    self.track = []

  def critical_path(self, s): 
    # TODO Return most likely path, using ``ll``. 
    # w(i -> j) = nodes[i].ll. Probably negate the edge 
    # weights and do Bellman-Ford (http://en.wikipedia.org/wiki/
    # Longest_path_problem#Acyclic_graphs_and_critical_paths).
    return []

    




if __name__ == '__main__': 
  
  db_con = util.get_db('reader')

  (t_start, t_end, tx_id) = (1376420800.0, 1376442000.0, 51)
  t_end_short = 1376427650.0 # short

  (t_start_feb2, t_end_feb2, tx_id_feb2) = (1391390700.638165, 1391396399.840252, 54)

  fella = track2(db_con, t_start, t_end, tx_id, 4.4)
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


        
     


