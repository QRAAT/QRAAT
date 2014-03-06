# tracks.py - Calculate a highly likely track for a transmitter from
# estimated positions. 
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
#  - Look at acceleration for determining if a transition is feasible. 

import numpy as np
import time, os, sys
import random
import util
from csv import csv

try:
  import MySQLdb as mdb
  import utm, xml
except ImportError: pass

def distance(Pi, Pj):
  ''' Calculate Euclidean distance between two points. ''' 
  return np.sqrt((Pi.real - Pj.real)**2 + (Pi.imag - Pj.imag)**2)

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
    return distance(self.P, u.P)

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

  def __init__(self, db_con, t_start, t_end, tx_id, M, C=1):
    cur = db_con.cursor()
    cur.execute('''SELECT northing, easting, timestamp, likelihood
                     FROM Position
                    WHERE (%f <= timestamp) 
                      AND (timestamp <= %f)
                      AND txid = %d
                    ORDER BY timestamp ASC''' % (t_start, t_end, tx_id))
    self.pos = cur.fetchall()
    roots = self.graph(self.pos, M)
    self.track = self.critical_path(self.toposort(roots), C)
  
  def recompute(self, M, C=1):
    roots = self.graph(self.pos, M)
    self.track = self.critical_path(self.toposort(roots), C)

  def __iter__(self):
    return self.track

  def __getitem__(self, i):
    return self.track[i]

  def graph(self, pos, M): 
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
    while i < len(pos) - 1:
      
      j = i
      Ti = Tj = float(pos[i][2])
      newLeaves = []
      while j < len(pos) - 1 and Ti == Tj: # Candidates for next time interval. 
        (P, ll) = (np.complex(pos[j][0], pos[j][1]), float(pos[j][3]))

        node = Node(P, Tj, ll)
        ok = False
        for k in range(len(leaves)):
          if leaves[k].distance(node) / (node.t - leaves[k].t) < M: 
            ok = True
            node.adj_in.append(leaves[k])
            leaves[k].adj_out.append(node)
        
        if not ok: # New root. 
          roots.append(node) 
          newLeaves.append(node)

        j += 1
        Tj = float(pos[j][2])

      # Recalculate leaves. 
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

  def toposort(self, roots): 
    ''' Compute a topological sorting of the track graph. Return None if 
        no sorting exists, i.e. graph has a cycle. 
    
      :param roots: Roots of the graph.
      :type roots: Node list
      :return: The sorted nodes.
      :rtype: Node list or None
    ''' 
    sorted_nodes = [] 

    for r in roots:
      S = [r]
      while (len(S) != 0):
        u = S[-1]
        u.t_visited = True
        ok = False
        for v in u.adj_out:
          if v.t_visited and not v.t_sorted:
            return None # Graph contains cycle. 
          elif not v.t_visited:
            S.append(v)
            ok = True
        if not ok: # No children to visit.  
          u.t_sorted = True
          sorted_nodes.append(u) 
          S.pop()

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
    
    path.reverse()
    return path
    

  def speed(self):
    ''' Calculate mean and standard deviation of the target's speed. 
    
      :return: (mean, std) tuple. 
    '''

    if len(self.track) > 0: 
      speeds = []
      for i in range(len(self.track)-1): 
        speeds.append( distance(self.track[i+1][0], self.track[i][0]) / \
                               (self.track[i+1][1] - self.track[i][1]) )
      return (np.mean(speeds), np.std(speeds))
    
    else: return (np.nan, np.nan)
    
  def acceleration(self): 
    ''' Calculate mean and standard deviation of the target's acceleration. 

      :return: (mean, std) tuple. 
    ''' 

    if len(self.track) > 0: 
      
      V = []
      for i in range(len(self.track)-1):
        v = (self.track[i+1][0] - self.track[i][0]) / (self.track[i+1][1] - self.track[i][1])
        V.append((v, (self.track[i][1] + self.track[i+1][1]) / 2))

      A = []
      for i in range(len(V)-1):
        a = (V[i+1][0] - V[i][0]) / (V[i+1][1] - V[i][1])
        A.append((a, (V[i][1] + V[i+1][1]) / 2))

      # Keeping V and A around like this just in case I want to get at the
      # timestamp or generate plots. For reporting, using magnitude of the 
      # acceleration. 
      A_mag = map(lambda(a, t) : mp.abs(a), A) 
      return (np.mean(A_mag), np.std(A_mag))

    else: return (np.nan, np.nan) 

  def insert_db(self, db_con): 
    pass # TODO

  def export_kml(self, fn):

    # E.g.: https://developers.google.com/kml/documentation/kmlreference#gxtrack 
    # <?xml version="1.0" encoding="UTF-8"?>
    # <kml xmlns="http://www.opengis.net/kml/2.2"
    #  xmlns:gx="http://www.google.com/kml/ext/2.2">
    # <Folder>
    #   <Placemark>
    #     <gx:Track>
    #       <when>2010-05-28T02:02:09Z</when>
    #       <when>2010-05-28T02:02:35Z</when>
    #       <when>2010-05-28T02:02:44Z</when>
    #       <when>2010-05-28T02:02:53Z</when>
    #       <when>2010-05-28T02:02:54Z</when>
    #       <when>2010-05-28T02:02:55Z</when>
    #       <when>2010-05-28T02:02:56Z</when>
    #       <gx:coord>-122.207881 37.371915 156.000000</gx:coord>
    #       <gx:coord>-122.205712 37.373288 152.000000</gx:coord>
    #       <gx:coord>-122.204678 37.373939 147.000000</gx:coord>
    #       <gx:coord>-122.203572 37.374630 142.199997</gx:coord>
    #       <gx:coord>-122.203451 37.374706 141.800003</gx:coord>
    #       <gx:coord>-122.203329 37.374780 141.199997</gx:coord>
    #       <gx:coord>-122.203207 37.374857 140.199997</gx:coord>
    #     </gx:Track>
    #   </Placemark>
    # </Folder>
    # </kml>

    (zone, letter) = 10, 'S' # TODO Add UTM zone to position table, modify 
                             # code to insert it automatically. 

    for (P, t) in self.track: 
      (lat, lon) = utm.to_latlon(P.imag, P.real, zone, letter) 
      tm = time.localtime(t)
      t = '%04d-%02d-%02dT%02d:%02d:%02dZ' % (tm.tm_year, tm.tm_mon, tm.tm_mday,
                                              tm.tm_hour, tm.tm_min, tm.tm_sec)



class trackall (track): 
  
  ''' Transmitter tracks over the entire position table. 

    A subset of positions. Feasible transitions between positions
    are modeled as a directed, acycle graph, from which we compute
    the critical path. 

    :param db_con: DB connector for MySQL. 
    :type db_con: MySQLdb.connections.Connection
    :param tx_id: Transmitter ID. 
    :type tx_id: int
    :param M: Maximum foot speed of target (m/s). 
    :type M: float
    :param C: Constant hop cost in critical path calculation.
    :type C: float
  '''

  def __init__(self, db_con, tx_id, M, C=1):
    cur = db_con.cursor()
    cur.execute('''SELECT northing, easting, timestamp, likelihood
                     FROM Position
                    WHERE txid = %d
                    ORDER BY timestamp ASC''' % tx_id)
    self.pos = cur.fetchall()
    roots = self.graph(self.pos, M)
    self.track = self.critical_path(self.toposort(roots), C)
  
    


if __name__ == '__main__': 
 
  M = 4
  C = 1

  db_con = util.get_db('reader')

  (t_start, t_end, tx_id) = (1376420800.0, 1376442000.0, 51)
  t_end_short = 1376427650.0 # short

  (t_start_feb2, t_end_feb2, tx_id_feb2) = (1391390700.638165, 1391396399.840252, 54)

  # A possible way to calculate good tracks. Compute the tracks
  # with some a priori maximum speed that's on the high side. For
  # the calibration data, we could safely assume that the gator 
  # won't exceed 10 m/s. 
  fella = track(db_con, t_start, t_end, tx_id, M, C) 

  # We then calculate statistics on the transition speeds in the 
  # critical path. Plotting the tracks might reveal spurious points
  # that we want to filter out. 
  (mean, std) = fella.speed()
  print "(mu=%.4f, sigma=%.4f)" % (mean, std)

  # Recompute the tracks, using the mean + one standard deviation as
  # the maximum speed. 
  fella.recompute(mean + (std), C)
  fella.export_kml("fella.kml")

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


        
     


