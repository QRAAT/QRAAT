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

# NOTE Where I'm going next. 
#
# Feasibility metric
# 
#   Assume the transition speed is exponentially distributed, paramterized 
#   by the maximum speed given the time interval. Since the observed speed
#   is calculated from a straight line drawn between the two points, it 
#   is the minimum speed that the target could have traveled. Thus, the 
#   probability of the transition is prob. mass function integratedd from
#   S to infinity. 
# 
#   TODO [track.transition_distribution()] Verify that the transition
#        speeds are indeed approximately exponential. 
# 
#   TODO [track.graph()] A more sophisticated feasibility metric would 
#        calculate the probability of the observed speed. If the event is
#        is probable, than add its edge to the graph. 
#
#   TODO Think about composing this probability with the position 
#        likelihood. These would need to be normalized (see notes.)  
#
# TODO 
#  - Make this module look more like position; i.e., move all classmethods 
#    out of track. 

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

  def __init__(self, P, t, ll, pos_id): 
    # Position.  
    self.P = P
    self.t = t
    self.ll = ll
    self.pos_id = pos_id

    # Connected component analysis. 
    self.c_size   = 1
    self.c_height = 0
    self.c_parent = None
  
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
    self.c_parent = None
    self.dist     = 0 
    self.parent   = None

  def distance(self, u):
    ''' Compute Euclidean distance to another node. ''' 
    return distance(self.P, u.P)

  def c_find(self):
    ''' Disjoint-set find operation for CC-analysis. ''' 
    p = self
    while (p.c_parent != None): 
      p = p.c_parent
    return p

  def c_union(self, u):
    ''' Disjoint-set union operation for CC-analysis. ''' 

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

  ''' Transmitter tracks. 

    A subset of positions. Feasible transitions between positions
    are modeled as a directed, acycle graph, from which we compute
    the critical path. 

    :param db_con: DB connector for MySQL. 
    :type db_con: MySQLdb.connections.Connection
    :param M: Maximum foot speed of target (m/s), given
              transition time
    :type M: lambda (t) -> float
    :param C: Constant hop cost in critical path calculation.
    :type C: float
    :param optimal: If False, use windowed tracking algorithm. 
    :type optiomal: bool
  '''
  
  (zone, letter) = 10, 'S' # TODO Add UTM zone to position table, modify 
                           # code to insert it automatically. 

  window_length = 250  
  overlap_length = 25 

  def __init__(self, db_con, pos_ids, tx_id, M, C=1, optimal=False):
    self.tx_id = tx_id
    
    # Get positions. 
    self._fetch(db_con, pos_ids)
    
    # Calculate tracks. 
    if optimal:
      self._calc_tracks(M, C)
    else:
      self._calc_tracks_windowed(M, C)
    

  def _calc_tracks_windowed(self, M, C):
    ''' Calculate tracks over overlapping windows of positions. 
    
      Note that the solution may be sub-optimal over the entire time window. 
      The optimal algorithm necessarily has a quadratic factor, which we 
      mitigate here by running it over a small, fixed number of positions. 
    '''
    pos_dict = {}
    self.track = []
    i = 0; j = self.window_length 

    while i < len(self.pos):
      
      t = self.pos[i][2]
      while self.pos[i-1][2] == t:
        i -= 1

      j =  min(len(self.pos) - 1, i + self.window_length)
      
      t = self.pos[j][2]
      while self.pos[j-1][2] == t:
        j -= 1
      
      roots = self.graph(self.pos[i:j+1], M)
      guy = self.critical_path(self.toposort(roots), C)
      
      for (P, t, pos_id, ll) in guy: 
        if not pos_dict.get(t):
          pos_dict[t] = set()
        pos_dict[t].add((P, pos_id, ll))

      i += self.window_length - self.overlap_length

    # When there are many possibilities for a timestep, choose the
    # position with higher likelihood. (NOTE that it may be better 
    # to rerun the critical path algorithm over the tree created 
    # in this process.)
    for (t, val) in sorted(pos_dict.items(), key=lambda(m) : m[0]):
      (P, pos_id, ll) = min(val, key=lambda(row) : row[2])
      self.track.append((P, t, pos_id))
  

  def _calc_tracks(self, M, C):
    ''' Calculate optimal tracks over all positions. 
    
      This track algorithm considers all possible transitions, 
      resulting in a quadratic factor in the running time. However,
      the solution is optimal for the time window.
    ''' 
    roots = self.graph(self.pos, M)
    self.track = map(lambda(row) : row[:3], self.critical_path(self.toposort(roots), C))
  

  def _fetch(self, db_con, pos_ids): 
    cur = db_con.cursor()
    cur.execute('''SELECT northing, easting, timestamp, likelihood, ID
                     FROM Position
                    WHERE ID in (%s)
                    ORDER BY timestamp ASC''' % ','.join(map(lambda(x) : str(x), pos_ids)))
    self.pos = cur.fetchall()
  
  def __getiter__(self): 
    return self.track

  def __getitem__(self, i):
    return self.track[i]
  
  def __len__(self):
    return len(self.track)
  
  #
  # DAG-building algorithms. 
  #

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
    
    nodes = []
    for i in range(len(pos)): 
      (P, t, ll, pos_id) = (np.complex(pos[i][0], pos[i][1]), 
                            float(pos[i][2]), 
                            float(pos[i][3]), 
                            int(pos[i][4]))
      nodes.append(Node(P, t, ll, pos_id)) 

    for i in range(len(nodes)):
      for j in range(i+1, len(nodes)):
        if nodes[i].t < nodes[j].t and speed(nodes[i], nodes[j]) < M(nodes[j].t - nodes[i].t): 
          nodes[i].adj_out.append(nodes[j])
          nodes[j].adj_in.append(nodes[i]) 
  
    roots = [] 
    for u in nodes:
      if len(u.adj_in) == 0:
        roots.append(u) 
   
    return roots
    
  def graph_alt(self, pos): 
    ''' Alternative DAG-building algorithm. 
    
      This is an attempt to reduce the complexity of the graph. The number 
      of possible edges is O(n choose 2). We test a new node for a feasible
      transition from a set of graph leaves. The problem is that segments of
      the true track of the target can be orphaned by the process. More
      thinking is required. **TODO** 
    '''
    
    # TODO update this code to include posID in Node() constructor. 
    roots = []; leaves = []
    i = 0 
    while i < len(pos) - 1:
      
      j = i
      Ti = Tj = float(pos[i][2])
      newLeaves = []
      while j < len(pos) - 1 and Ti == Tj: # Candidates for next time interval. 
        (P, ll, pos_id) = (np.complex(pos[j][0], pos[j][1]), float(pos[j][3]), pos[j][4])

        w = Node(P, Tj, ll, pos_id)
        ok = False
        for v in leaves:
          if speed(v, w) < M(w.t - v.t):
            ok = True
            w.adj_in.append(v)
            v.adj_out.append(w)
            w.c_union(v)
        
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

    # Exclude isolated nodes.
    #retRoots = []
    #for node in roots:
    #  if node.c_find().c_size > 1:
    #    retRoots.append(node)
    #return retRoots
    
    return roots
  
  #
  # Methods for calculating the critical path over the graph.
  #

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
      path.append((node.P, node.t, node.ll, node.pos_id))
      node = node.parent
    
    path.reverse()
    return path

  #
  # Some statistical features of the tracks. 
  #

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

  # 
  # A few families of max speed given time interval functions. 
  # TODO I'm somewhat abusing the API structure here. Move these
  # class methods out and make htis module look more like position.
  # (Or make position look more like track.)
  #

  @classmethod
  def maxspeed_linear(cls, burst, sustained, limit):
    return lambda (t) : max(limit, (t - burst[0]) * (
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

  @classmethod
  def get_pos_ids(cls, db_con, tx_id, t_start, t_end):
    cur = db_con.cursor()
    cur.execute('''SELECT ID 
                     FROM Position
                    WHERE txID=%d
                      AND timestamp >= %f 
                      AND timestamp <= %f''' % (tx_id, t_start, t_end))
    return [ int(row[0]) for row in cur.fetchall() ]
  


# TODO This will be the Python interface for tracks in the DB. 

class Track:

  def __init__(self, db_con, track_id, t_start, t_end):
    self.table = []
    pass # Read track from DB. 

  def insert_db(self, db_con): 
    for (pos_id, dep_id, t, easting, northing, utm_zone_number, 
         utm_zone_letter, likelihood, activity):
      pass # TODO 

  def export_kml(self, name, tx_id):

    # E.g.: https://developers.google.com/kml/documentation/kmlreference#gxtrack 
    # TODO The file is way longer than it needs to be, since I wanted to display
    # the coordinates and datetime in the tooltip that appears in Google Earth.
    # Perhaps what we want is not a gx:track, but something fucnctionally 
    # similar.

    # TODO Add northing, easting to output. 

    fd = open('%s_track.kml' % name, 'w')
    fd.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    fd.write('<kml xmlns="http://www.opengis.net/kml/2.2"\n')
    fd.write(' xmlns:gx="http://www.google.com/kml/ext/2.2">\n')
    fd.write('<Folder>\n')
    fd.write('  <Placemark>\n')
    fd.write('    <name>%s (txID=%d)</name>\n' % (name, tx_id))
    fd.write('    <gx:Track>\n')
    for (P, t, pos_id) in self.track: 
      tm = time.gmtime(t)
      t = '%04d-%02d-%02dT%02d:%02d:%02dZ' % (tm.tm_year, tm.tm_mon, tm.tm_mday,
                                              tm.tm_hour, tm.tm_min, tm.tm_sec)
      fd.write('      <when>%s</when>\n' % t)
    for (P, t, pos_id) in self.track: 
      (lat, lon) = utm.to_latlon(P.imag, P.real, self.zone, self.letter) 
      fd.write('      <gx:coord>%f %f 0</gx:coord>\n' % (lon, lat))
    fd.write('      <ExtendedData>\n')
    fd.write('        <SchemaData schemaUrl="#schema">\n')
    fd.write('          <gx:SimpleArrayData name="Time">\n')
    for (P, t, pos_id) in self.track: 
      tm = time.gmtime(t)
      t = '%04d-%02d-%02d %02d:%02d:%02d' % (tm.tm_year, tm.tm_mon, tm.tm_mday,
                                              tm.tm_hour, tm.tm_min, tm.tm_sec)
      fd.write('          <gx:value>%s</gx:value>\n' % t)
    fd.write('          </gx:SimpleArrayData>\n')
    fd.write('          <gx:SimpleArrayData name="(lat, long)">\n')
    for (P, t, pos_id) in self.track: 
      (lat, lon) = utm.to_latlon(P.imag, P.real, self.zone, self.letter) 
      fd.write('          <gx:value>%fN, %fW</gx:value>\n' % (lat, lon))
    fd.write('          </gx:SimpleArrayData>\n')
    fd.write('          <gx:SimpleArrayData name="posID">\n')
    for (P, t, pos_id) in self.track: 
      tm = time.gmtime(t)
      t = '%04d-%02d-%02d %02d:%02d:%02d' % (tm.tm_year, tm.tm_mon, tm.tm_mday,
                                              tm.tm_hour, tm.tm_min, tm.tm_sec)
      fd.write('          <gx:value>%d</gx:value>\n' % pos_id)
    fd.write('          </gx:SimpleArrayData>\n')
    fd.write('        </SchemaData>\n')
    fd.write('      </ExtendedData>\n')
    fd.write('    </gx:Track>\n')
    fd.write('  </Placemark>\n')
    fd.write('</Folder>\n')
    fd.write('</kml>')
    fd.close() 


# TODO This will be the Python interface for positions in the DB. 
 
class Position:
  
  def __init__(self, db_con=None, tx_id=None, t_start=None, t_end=None): 
    self.table = []
    pass # TODO read from database. 

  def insert_db(self, db_con):
    for (id, tx_id, timestamp, easting, northing, 
         utm_zone_number, utm_zone_letter, likelihood, activity) in self.table: 
      pass # TODO 

  def export_kml(self, name, tx_id):

    fd = open('%s_pos.kml' % name, 'w')
    fd.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    fd.write('<kml xmlns="http://www.opengis.net/kml/2.2"\n')
    fd.write(' xmlns:gx="http://www.google.com/kml/ext/2.2">\n')
    fd.write('<Folder>\n')
    fd.write('  <Placemark>\n')
    fd.write('  <MultiGeometry>\n')
    fd.write('    <name>%s (txID=%d) position cloud</name>\n' % (name, tx_id))
    for row in self.table:
      (P, t, ll, pos_id) = (np.complex(row[0], row[1]), 
                            float(row[2]), 
                            float(row[3]), 
                            int(row[4]))
      tm = time.gmtime(t)
      t = '%04d-%02d-%02d %02d:%02d:%02d' % (tm.tm_year, tm.tm_mon, tm.tm_mday,
                                              tm.tm_hour, tm.tm_min, tm.tm_sec)
      (lat, lon) = utm.to_latlon(P.imag, P.real, self.zone, self.letter) 
      fd.write('    <Point id="%d">\n' % pos_id)
      fd.write('      <coordinates>%f,%f,0</coordinates>\n' % (lon, lat))
      fd.write('    </Point>\n')
    fd.write('  </MultiGeometry>\n')
    fd.write('  </Placemark>\n')
    fd.write('</Folder>\n')
    fd.write('</kml>')
    fd.close() 

# TODO This will be the Python interface for bearings in the DB. 

class Bearing: 
  
  def __init__(self, db_con=None, tx_id=None, site_id=None, t_start=None, t_end=None):
    self.table = []
    pass # TODO read from database. 

  def insert_db(db_con):
    for (id, tx_id, site_id, pos_id, timestamp, bearing, 
         likelihood, activity) in self.table: 
      pass # TODO 

  def export_kml(self, name, tx_id, site_id):
    pass # TODO 



def tx_name(db_con):
  cur = db_con.cursor()
  cur.execute('SELECT id, name FROM qraat.txlist')
  d = {}
  for (id, name) in cur.fetchall():
    d[id] = name
  return d


if __name__ == '__main__': 
  
  tx_id = 54
  
  import commands
  t_start = int(commands.getoutput('date --date="20140202 1200" +%s'))
  t_end   = int(commands.getoutput('date --date="20140202 1600" +%s'))

  print t_start, t_end
  M = track.maxspeed_exp((10, 1), (360, 0.1), 0.05)
  #M = track.maxspeed_linear((10, 1), (180, 0.1), 0.05)
  C = 1

  db_con = util.get_db('writer')
  
  fella = track(db_con, t_start, t_end, tx_id, M, C) 
  #fella = trackall(db_con, tx_id, M, C) 
  #fella.export_kml(tx_name(db_con)[tx_id], tx_id)

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
     map(lambda (P, t, pos_id): P.imag, fella), 
     map(lambda (P, t, pos_id): P.real, fella), '.', alpha=0.3)

    pp.savefig("test.png")
 
     


