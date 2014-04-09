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
# TODO 
# - Look at velocity distribution for all transitions. 
# - track2: construct DAG from all transitions. 
# - For real time implementation, use overlapping windows and stitch
#   critcal paths together. 

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
  return np.abs(Pj - Pi)

def speed(v, w):
  return np.abs((w.P - v.P) / (w.t - v.t))

def acceleration(u, v, w): 
  V1 = (v.P - u.P) / (v.t - u.t) 
  V2 = (w.P - v.P) / (w.t - v.t) 
  t1 = (v.t + u.t) / 2
  t2 = (w.t + v.t) / 2  
  return np.abs((V2 - V1) / (t2 - t1))

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
    :param M: Maximum foot speed of target (m/s), given
              transition time
    :type M: lambda (t) -> float
    :param C: Constant hop cost in critical path calculation.
    :type C: float
  '''
  
  def _fetch(self, db_con, t_start, t_end, tx_id): 
    cur = db_con.cursor()
    cur.execute('''SELECT northing, easting, timestamp, likelihood
                     FROM Position
                    WHERE (%f <= timestamp) 
                      AND (timestamp <= %f)
                      AND txid = %d
                    ORDER BY timestamp ASC''' % (t_start, t_end, tx_id))
    self.pos = cur.fetchall()
  
  def _fetchall(self, db_con, tx_id):
    cur = db_con.cursor()
    cur.execute('''SELECT northing, easting, timestamp, likelihood
                     FROM Position
                    WHERE txid = %d
                    ORDER BY timestamp ASC''' % tx_id)
    self.pos = cur.fetchall()

  def __init__(self, db_con, t_start, t_end, tx_id, M, C=1):
    self._fetch(db_con, t_start, t_end, tx_id)
    roots = self.graph(self.pos, M)
    self.track = self.critical_path(self.toposort(roots), C)
  
  def recompute(self, M, C=1):
    roots = self.graph(self.pos, M)
    self.track = self.critical_path(self.toposort(roots), C)

  def __getiter__(self): # TODO __getiter__ ? 
    return self.track

  def __getitem__(self, i):
    return self.track[i]
  
  def __len__(self):
    return len(self.track)

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

        w = Node(P, Tj, ll)
        ok = False
        for v in leaves:
          if speed(v, w) < M(w.t - v.t):
            ok = True
            w.adj_in.append(v)
            v.adj_out.append(w)
            # TODO Union
        
        if not ok: # New root. 
          roots.append(w) 
          newLeaves.append(w)

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
    # TODO map : CC -> (cost, node) 

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

  def stats(self):
    ''' Piecewise velocity and acceleration along critcal path. '''   
    
    V = []
    for i in range(len(self.track)-1):
      v = (self.track[i+1][0] - self.track[i][0]) / (self.track[i+1][1] - self.track[i][1])
      V.append((v, (self.track[i][1] + self.track[i+1][1]) / 2))

    A = []
    for i in range(len(V)-1):
      a = (V[i+1][0] - V[i][0]) / (V[i+1][1] - V[i][1])
      A.append((a, (V[i][1] + V[i+1][1]) / 2))

    return (map(lambda(v, t) : np.abs(v), V), map(lambda(a, t) : np.abs(a), A))

  @classmethod
  def transition_distribution(cls, db_con, t_start, t_end, tx_id):
    ''' TODO '''
    cur = db_con.cursor()
    cur.execute('''SELECT northing, easting, timestamp, likelihood
                     FROM Position
                    WHERE (%f <= timestamp) 
                      AND (timestamp <= %f)
                      AND txid = %d
                    ORDER BY timestamp ASC''' % (t_start, t_end, tx_id))
    pos = cur.fetchall()
    return [] # TODO 

  def

  @classmethod
  def maxspeed_linear(cls, burst, sustained):
    return lambda (t) : max(0.01, (t - burst[0]) * (
            float(sustained[1] - burst[1]) / (sustained[0] - burst[0])) + burst[1])

  @classmethod
  def maxspeed_exp(cls, burst, sustained, limit):
    (t1, y1) = burst; (t2, y2) = sustained
    C = limit

    r = np.log((y2 - C) / (y1 - C)) / (t1 - t2) 
    B = np.exp(r * t2) * (y2 - C)
    r *= -1
    
    return lambda (t) : (B * np.exp(r * t) + C)

  @classmethod
  def maxspeed_const(cls, m):
    return lambda (t) : m

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
  
  ''' Transmitter tracks over the entire position table. '''
    

  def __init__(self, db_con, tx_id, M, C=1):
    self._fetchall(db_con, tx_id)
    roots = self.graph(self.pos, M)
    self.track = self.critical_path(self.toposort(roots), C)
  


class trackall2 (track): 
 
  ''' Test all possible transitions, i.e. overload graph(). ''' 

  def __init__(self, db_con, tx_id, M):
    self._fetchall(db_con, tx_id)
    roots = self.graph(self.pos)
    self.track = self.critical_path(self.toposort(roots), M)

  def graph(self, pos): 
    
    nodes = []
    for i in range(min(len(pos),100)): # FIXME stop gap
      (P, t, ll) = (np.complex(pos[i][0], pos[i][1]), float(pos[i][2]), float(pos[i][3]))
      nodes.append(Node(P, t, ll)) 

    for i in range(len(nodes)):
      for j in range(i+1, len(nodes)):
        if nodes[i].t < nodes[j].t: # and speed(nodes[i], nodes[j]) < M(nodes[j].t - nodes[i].t): 
          nodes[i].adj_out.append(nodes[j])
          nodes[j].adj_in.append(nodes[i]) 
  
    roots = [] 
    for u in nodes:
      if len(u.adj_in) == 0:
        roots.append(u) 
   
    return roots
  
  def critical_path(self, sorted_nodes, M): 
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
      if mparent:
        ll = v.ll / sum(map(lambda(w) : w.ll, mparent.adj_out))
        v.dist = mdist + (ll * np.exp((-1) * M(v.t - mparent.t) * speed(mparent, v))) 
      else: v.dist = mdist + 0.01
      if v.dist > cost:
        cost = v.dist
        node = v
      
    path = []
    while node != None:
      path.append((node.P, node.t))
      node = node.parent
    
    path.reverse()
    return path





if __name__ == '__main__': 
  
  tx_id = 6
  M = track.maxspeed_exp((10, 1), (180, 0.1), 0)
  C = 1

  db_con = util.get_db('reader')
  
  # NOTE still experimenting with this. 
  #(t_start_feb2, t_end_feb2, tx_id_feb2) = (1391390700.638165 - (3600 * 6), 1391396399.840252 + (3600 * 6), 54)
  #fella = track2(db_con, t_start_feb2, t_end_feb2, tx_id_feb2, M) 

  # Testing track output ... 
  # NOTE I'm experimenting now with calculating the critical path for each CC 
  # and stitching them together in post processing. Could I prove the optimality 
  # of this approach? 
  fella = trackall(db_con, tx_id, M, C) 
  
  t = time.localtime(fella[0][1])
  s = time.localtime(fella[-1][1])
  print '%04d-%02d-%02d  %02d:%02d - %04d-%02d-%02d  %02d:%02d  txID=%d' % (
       t.tm_year, t.tm_mon, t.tm_mday,
       t.tm_hour, t.tm_min,
       s.tm_year, s.tm_mon, s.tm_mday,
       s.tm_hour, s.tm_min,
       tx_id)

  print 'Length of critical path: %d (out of %d)' % (len(fella), len(fella.pos))

  if True:

    import matplotlib.pyplot as pp

    # Plot sites.
    sites = csv(db_con=db_con, db_table='sitelist')
    pp.plot(
     [s.easting for s in sites], 
     [s.northing for s in sites], 'ro')

    # Plot locations. 
    pp.plot( 
     map(lambda (P, t): P.imag, fella), 
     map(lambda (P, t): P.real, fella), '.', alpha=0.3)

    pp.savefig("test.png")
 
     


