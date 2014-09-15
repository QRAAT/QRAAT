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

import numpy as np
import time, os, sys
import random

BURST_INTERVAL = 60        # 1 minute
SUSTAINED_INTERVAL = 1800  # 30 minutes

try:
  import MySQLdb as mdb
  import utm, xml
except ImportError: pass

def get_pos_ids(db_con, dep_id, t_start, t_end): 
  cur = db_con.cursor()
  cur.execute('''SELECT ID 
                   FROM position
                  WHERE deploymentID=%d
                    AND timestamp >= %f 
                    AND timestamp <= %f''' % (dep_id, t_start, t_end))
  return [ int(row[0]) for row in cur.fetchall() ]


# 
# A few families of max speed given time interval functions. 
#

def maxspeed_linear(burst, sustained, limit):
  return lambda (t) : max(limit, (t - burst[0]) * (
          float(sustained[1] - burst[1]) / (sustained[0] - burst[0])) + burst[1])

def maxspeed_exp(burst, sustained, limit):
  (t1, y1) = burst; (t2, y2) = sustained
  C = limit

  r = np.log((y2 - C) / (y1 - C)) / (t1 - t2) 
  B = np.exp(r * t2) * (y2 - C)
  r *= -1
  
  return lambda (t) : (B * np.exp(r * t) + C)

def maxspeed_const(m):
  return lambda (t) : m


#
# Run tracker. 
#

def calc_tracks(db_con, pos, dep_id, C=1):
  cur = db_con.cursor()
  cur.execute('''SELECT target.ID, max_speed_family, 
                        speed_burst, speed_sustained, speed_limit
                   FROM target 
                   JOIN deployment ON target.ID = deployment.targetID
                  WHERE deployment.ID = %s''', (dep_id,))
  (_, family, burst, sustained, limit) = cur.fetchone()
  if family == 'const':
    M = maxspeed_const(limit)
  elif family == 'exp': 
    M = maxspeed_exp((BURST_INTERVAL, burst), (SUSTAINED_INTERVAL, sustained), limit)
  elif family == 'linear':
    M = maxspeed_linear((BURST_INTERVAL, burst), (SUSTAINED_INTERVAL, sustained), limit)
  
  return Track.calc(db_con, pos, dep_id, M, C, optimal=False) 





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

  def __init__(self, P, t, ll, pos_id, utm_number, utm_letter, activity): 
    # Position.  
    self.P = P
    self.t = t
    self.ll = ll
    self.pos_id = pos_id
    self.utm_number = utm_number
    self.utm_letter = utm_letter
    self.activity = activity

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



class Track:

  ''' Transmitter tracks. 

    A subset of positions. Feasible transitions between positions
    are modeled as a directed, acycle graph, from which we compute
    the critical path. 

  '''

  window_length = 250 
  overlap_length = 10

  def __init__(self, db_con=None, dep_id=None, t_start=None, t_end=None): 
    self.dep_id = dep_id
    self.table = []
    if db_con:
      cur = db_con.cursor()
      
      cur.execute('''SELECT positionID, position..deploymentID, track_pos.timestamp, easting, northing, 
                            utm_zone_number, utm_zone_letter, likelihood, activity
                       FROM position
                       JOIN track_pos ON track_pos.positionID = position.ID
                      WHERE deploymentID = %d
                        AND track_pos.timestamp >= %f AND track_pos.timestamp <= %f 
                      ORDER BY timestamp ASC''' % (dep_id, t_start, t_end))
      
      for row in cur.fetchall():
        self.table.append((row[0], row[1], float(row[2]), float(row[3]), float(row[4]), 
                           row[5], row[6], row[7], row[8]))
        

  @classmethod
  def calc(cls, db_con, pos, dep_id, M, C, optimal=False):
    track = cls()
    track.dep_id = dep_id
    
    # Get positions. 
    track.pos = pos
    
    # Calculate tracks. 
    if optimal:
      track._calc_tracks(M, C)
    else:
      track._calc_tracks_windowed(M, C)
    
    for node in track.track:
      track.table.append((node.pos_id, None, node.t, node.P.imag, node.P.real, 
                          node.utm_number, node.utm_letter, node.ll, node.activity))

    return track
    
 
  def insert_db(self, db_con):
    # Overwrite existing tracks for time window. 
    cur = db_con.cursor()
    cur.execute('''DELETE fROM qraat.track_pos 
                         WHERE timestamp >= %s 
                           AND timestamp <= %s
                           AND deploymentID = %s''', (self.table[0][2], self.table[-1][2], self.dep_id)) 
    for (pos_id, dep_id, t, easting, northing, utm_zone_number, 
         utm_zone_letter, likelihood, activity) in self.table:
      cur.execute('''INSERT INTO track_pos (positionID, deploymentID, timestamp)
                          VALUES (%d, %d, %d)''' % (pos_id, self.dep_id, t))

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
      
      for node in guy: 
        if not pos_dict.get(node.t):
          pos_dict[node.t] = set()
        pos_dict[node.t].add(node)

      i += self.window_length - self.overlap_length

    # When there are many possibilities for a timestep, choose the
    # position with higher likelihood. (NOTE that it may be better 
    # to rerun the critical path algorithm over the tree created 
    # in this process.)
    for (t, val) in sorted(pos_dict.items(), key=lambda(m) : m[0]):
      node = max(val, key=lambda(row) : node.t)
      self.track.append(node)
    


  def _calc_tracks(self, M, C):
    ''' Calculate optimal tracks over all positions. 
    
      This track algorithm considers all possible transitions, 
      resulting in a quadratic factor in the running time. However,
      the solution is optimal for the time window.
    ''' 
    roots = self.graph(self.pos, M)
    self.track = self.critical_path(self.toposort(roots), C)
  
  def __getiter__(self): 
    return self.table

  def __getitem__(self, i):
    return self.table[i]
  
  def __len__(self):
    return len(self.table)
  
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
    
    # pos row: (id, tx_id, timestamp, easting, northing, 
    # utm_zone_number, utm_zone_letter, likelihood, activity)
    nodes = []
    for i in range(len(pos)): 
      nodes.append(Node(np.complex(pos[i][4], pos[i][3]), # P 
                        float(pos[i][2]),                 # t
                        float(pos[i][7]),                 # ll 
                        int(pos[i][0]),                   # pos_id
                        pos[i][5], pos[i][6],             # UTM
                        float(pos[i][8])))                # actiivty
      
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
    
    # TODO update this code to include positionID in Node() constructor.
    # TODO row format has changed!!
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
      path.append(node)
      node = node.parent
    
    path.reverse()
    return path


  def export_kml(self, name, tx_id):
    # TODO I've changed some stuff ... make sure this output is still sensible. 
  
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
    fd.write('    <name>%s (deploymentID=%d)</name>\n' % (name, tx_id))
    fd.write('    <gx:Track>\n')
    for (pos_id, dep_id, t, easting, northing, utm_number, utm_letter, ll, activity) in self.table: 
      tm = time.gmtime(t)
      t = '%04d-%02d-%02dT%02d:%02d:%02dZ' % (tm.tm_year, tm.tm_mon, tm.tm_mday,
                                              tm.tm_hour, tm.tm_min, tm.tm_sec)
      fd.write('      <when>%s</when>\n' % t)
    for (pos_id, dep_id, t, easting, northing, utm_number, utm_letter, ll, activity) in self.table: 
      (lat, lon) = utm.to_latlon(easting, northing, utm_number, utm_letter) 
      fd.write('      <gx:coord>%f %f 0</gx:coord>\n' % (lon, lat))
    fd.write('      <ExtendedData>\n')
    fd.write('        <SchemaData schemaUrl="#schema">\n')
    fd.write('          <gx:SimpleArrayData name="Time">\n')
    for (pos_id, dep_id, t, easting, northing, utm_number, utm_letter, ll, activity) in self.table: 
      tm = time.gmtime(t)
      t = '%04d-%02d-%02d %02d:%02d:%02d' % (tm.tm_year, tm.tm_mon, tm.tm_mday,
                                              tm.tm_hour, tm.tm_min, tm.tm_sec)
      fd.write('          <gx:value>%s</gx:value>\n' % t)
    fd.write('          </gx:SimpleArrayData>\n')
    fd.write('          <gx:SimpleArrayData name="(lat, long)">\n')
    for (pos_id, dep_id, t, easting, northing, utm_number, utm_letter, ll, activity) in self.table: 
      (lat, lon) = utm.to_latlon(easting, northing, utm_number, utm_letter) 
      fd.write('          <gx:value>%fN, %fW</gx:value>\n' % (lat, lon))
    fd.write('          </gx:SimpleArrayData>\n')
    fd.write('          <gx:SimpleArrayData name="positionID">\n')
    for (pos_id, dep_id, t, easting, northing, utm_number, utm_letter, ll, activity) in self.table: 
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

  #
  # Some statistical features of the tracks. 
  #

  def speed(self):
    ''' Calculate mean and standard deviation of the target's speed. 
    
      :return: (mean, std) tuple. 
    '''
    # TODO Rewrite
    #if len(self.table) > 0: 
    #  speeds = []
    #  for i in range(len(self.table)-1): 
    #    # (pos_id, dep_id, t, easting, northing, utm_number, letter, ll, activity) 
    #    P = np.complex(self.table[i+1][4], self.table[i+1][3])
    #    Q = np.complex(self.table[i][4], self.table[i][3])
    #    t_p = self.table[i+1][2]
    #    t_q = self.table[i][2]
    #    speeds.append( distance(P, Q) / (t_p - t_q) )
    #  return (np.mean(speeds), np.std(speeds))
    # 
    # else: return (np.nan, np.nan)
    return (np.nan, np.nan)

  def stats(self):
    ''' Piecewise velocity and acceleration along critcal path. '''   
    # TODO rewrite
    #    V = []
    #    for i in range(len(self.table)-1):
    #      v = (self.table[i+1].P - self.table[i].P) / (self.table[i+1].t - self.table[i].t)
    #      V.append((v, (self.table[i].t + self.table[i+1].t) / 2))
    #
    #    A = []
    #    for i in range(len(V)-1):
    #      a = (V[i+1].P - V[i].P) / (V[i+1].t - V[i].t)
    #      A.append((a, (V[i].t + V[i+1].t) / 2))
    #
    #    return (map(lambda(v, t) : np.abs(v), V), map(lambda(a, t) : np.abs(a), A))
    


# Testing, testing ... 

if __name__ == '__main__': 
     
  pass

