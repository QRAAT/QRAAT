# tracks.py - Calculate a highly likely track for a transmitter from
# estimated positoins. 
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
#  - Fix mean / stddev calculation of target speed. 


import numpy as np
import time, os, sys
import random

import util
from csv import csv

try:
  import MySQLdb as mdb
except ImportError: pass


class TrackError (Exception):
  """ Exception class for building tracks. """

  def __init__(self, msg):
    self.msg = msg

  def __str__(self):
    return msg


class Node:

  ''' Node of track graph. 
  
    :param P: Position
    :type P: np.complex
    :param t: Time (UNIX timestamp) 
    :type t: float
    :param ll: Likelihood of position
    :type ll: float
  '''

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

    # Generic. 
    self.dist = 0
    self.parent = None
    self.adj_in = []
    self.adj_out = []

  def reset(self):
    ''' Reset algorithm paramaters. ''' 
    self.c_size   = 1
    self.c_height = 0
    self.dist     = 0 
    self.parent   = None

  def distance(self, u):
    ''' Compute Euclidean distance to another node. ''' 
    return np.sqrt((self.P.real - u.P.real)**2 + (self.P.imag - u.P.imag)**2)

  def c_find(self):
    ''' Disjoint-set find operation for CC-analysis. ''' 
    p = self
    while (p.parent != None): 
      p = p.parent
    return p

  def c_union(self, u):
    ''' Disjoint-set union operation for CC-analysis. ''' 

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

  ''' Transmitter tracks. 

    A subset of positions. Feasible transitions between positions
    are modeled as a directed, acycle graph, from which we compute
    the critical path. 

    :param db_con: DB connector for MySQL. 
    :type db_con: MySQLdb.connections.Connection
    :param t_start: Time start (Unix). 
    :type t_start: float 
    :param t_end: Time end (Unix).
    :type t_end: float
    :param tx_id: Transmitter ID. 
    :type tx_id: int
    :param M: Maximum foot speed of target (m/s). 
    :type M: float
    :param C: Constant hop cost in critical path calculation.
    :type C: float
  '''

  def __init__(self, db_con, t_start, t_end, tx_id, M, C):
    cur = db_con.cursor()
    cur.execute('''SELECT northing, easting, timestamp, likelihood
                     FROM Position
                    WHERE (%f <= timestamp) 
                      AND (timestamp <= %f)
                      AND txid = %d
                    ORDER BY timestamp ASC''' % (t_start, t_end, tx_id))
    pos = cur.fetchall()
    roots = self.track_graph(pos, M)
    self.track = self.critical_path(self.toposort(roots), C)
    self.track.reverse()

  def __iter__(self):
    return self.track

  def __getitem__(self, i):
    return self.track[i]

  def track_graph(self, pos, M): 
    ''' Create a graph from positions. 
          
      Each position corresponds to a node. An edge is drawn between nodes with 
      a feasible transition, i.e. distance(Pi, Pj) / (Tj - Ti) < M. The result
      will be a directed, acyclic graph. We define the roots of this graph to 
      be a set of nodes from which all nodes are reachable.

      :param pos: A list of 4-tuples (northing, easting, t, ll) sorted by t 
                  corresponding to positions. 
      :type pos: (np.complex, float, float) list 
      :param M: Maximum target speed. 
      :type M: float
      :return: The roots of the graph. 
      :rtype: Node list
    '''
  
    roots = []; leaves = []
    i = 0 
    while i < len(pos):
      
      j = i
      Tj = Ti = float(pos[i][2])
      while j < len(pos) and (Ti - Tj == 0): # Candidates for next time interval. 
        (Pj, Tj, ll) = (np.complex(pos[j][0], pos[j][1]), 
                                           float(pos[j][2]), float(pos[j][3]))

        node = Node(Pj, Tj, ll)
        ok = False
        for k in range(len(leaves)):
          if leaves[k].distance(node) / (node.t - leaves[k].t) < M: 
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
            if v not in newLeaves: # FIXME O(n)
              newLeaves.append(v)
      leaves = newLeaves

      i = j
    
    return roots


  def _visit(self, u, sorted_nodes): 
    if u.t_visited and not u.t_sorted: 
      raise TrackError("cycle discovered in track graph")
    elif not u.t_visited:
      u.t_visited = True
      for v in u.adj_out: 
        self._visit(v, sorted_nodes)
      u.t_sorted = True
      sorted_nodes.append(u)
    

  def toposort(self, roots): 
    ''' Compute a topological sorting of the track graph. 
    
      :param roots: Roots of the graph.
      :type roots: Node list
      :return: The sorted nodes.
      :rtype: Node list
    ''' 
    sorted_nodes = [] 
    for u in roots:
      self._visit(u, sorted_nodes)
    sorted_nodes.reverse()
    return sorted_nodes


  def critical_path(self, sorted_nodes, C): 
    ''' Calculate the critical path of the track graph.

      :param sorted_nodes: Topologically sorted graph nodes. 
      :type sorted_nodes: NOde list
      :param C: Constant hop cost. 
      :type C: float
    ''' 
    cost = 0
    node = None 
    for v in sorted_nodes: 
      mdist = 0
      mparent = None
      for u in v.adj_in:
        if u.dist > mdist:
          mdist = u.dist
          mparent = u
      v.parent = mparent
      v.dist = mdist + C + v.ll 
      
      if v.dist > cost:
        cost = v.dist
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

  fella = track(db_con, t_start, t_end, tx_id, 5.3, 1)

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


        
     


