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
#
# TODOs 
#  - Stackify DFS in toposort(). 
#  - Fix mean / stddev calculation of target speed. 
#  - Clean up class track, class Node. 
#  - Interface for class track, include in __init__.py. 


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
    # Position.  
    self.P = P
    self.t = t
    self.ll = ll

    # Connected component analysis. 
    self.c_size   = 1
    self.c_height = 0
  
    # Topological sorting. 
    self.t_visited = False
    self.t_sorted = False

    # Critical path. 
    self.distance = 0

    # Generic. 
    self.parent = None
    self.adj_in = []
    self.adj_out = []

  def dist (self, aNode):
    return dist(self.P, aNode.P)

  def c_find(self):
    p = self
    while (p.parent != None): 
      p = p.parent
    return p

  def c_union(self, u): 
    x = self.c_find()
    y = u.c_find()

    if (x == y): # This and u are in the same component. 
      p = x
    
    elif (x.c_height == y.c_height): # x and y have the same height.
      y.parent  = x
      x.c_height += 1
      x.c_size   += y.c_size
      p = x

    elif (x.c_height > y.c_height): # x is taller than y.
      y.parent = x
      x.c_size  += y.c_size
      p = x

    else: # y is taller than x.
      x.parent = y
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
    
    # Average speed.
    mean_speed = 0;
    for i in range(len(pos)-1): 
      Pi = np.complex(pos[i][3], pos[i][4])
      Pj = np.complex(pos[i+1][3], pos[i+1][4])
      t_delta = float(pos[i+1][2]) - float(pos[i][2])
      assert t_delta > 0 # TODO 
      mean_speed += dist(Pi, Pj) / t_delta
    mean_speed /= len(pos)
    
    # TODO make this a method. 
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
            node.adj_in.append(leaves[k])
            leaves[k].adj_out.append(node)
        
        if not ok: # New root. 
          roots.append(node) 
          leaves.append(node)

        j += 1
  
      # Recalculate leaves. 
      newLeaves = []
      for u in leaves:
        if len(u.adj_out) == 0: 
          newLeaves.append(u)
        else: 
          for v in u.adj_out:
            if v not in newLeaves:
              newLeaves.append(v)
      leaves = newLeaves

      i = j

    self.track = self.critical_path(self.toposort(roots), C=-10)
    self.track.reverse()


  def visit(self, u, sorted_nodes): 
    # TODO combine with toposort to do stack-style DFS. 
    if u.t_visited and not u.t_sorted: 
      raise "A cycle!"
    elif not u.t_visited:
      u.t_visited = True
      for v in u.adj_out: 
        self.visit(v, sorted_nodes)
      u.t_sorted = True
      sorted_nodes.append(u)
    
  def toposort(self, roots): 
    sorted_nodes = [] 
    for u in roots:
      self.visit(u, sorted_nodes)
    sorted_nodes.reverse()
    return sorted_nodes

  def critical_path(self, sorted_nodes, C): 
    cost = 0
    node = None 
    for v in sorted_nodes: 
      mdistance = 0
      mparent = None
      for u in v.adj_in:
        if u.distance > mdistance:
          mdistance = u.distance
          mparent = u
      v.parent = mparent
      v.distance = mdistance + C + v.ll 
      
      if v.distance > cost:
        cost = v.distance
        node = v
      
    path = []
    while node != None:
      path.append((node.P, node.t))
      node = node.parent
    return path
    

 



if __name__ == '__main__': 
  
  db_con = util.get_db('reader')

  (t_start, t_end, tx_id) = (1376420800.0, 1376442000.0, 51)
  t_end_short = 1376427650.0 # short

  (t_start_feb2, t_end_feb2, tx_id_feb2) = (1391390700.638165, 1391396399.840252, 54)

  fella = track(db_con, t_start_feb2, t_end_feb2, tx_id_feb2, 4.4)

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


        
     


