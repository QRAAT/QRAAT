# position.py - Routines and classes related to direction finding 
# and target position estimation. This file is part of QRAAT, an 
# automated animal tracking system based on GNU Radio. 
#
# Copyright (C) 2013 Todd Borrowman, Christopher Patton, Sean Riddle
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

import util
from csv import csv

try:
  import MySQLdb as mdb
except ImportError: pass

#: Center of Quail Ridge reserve (northing, easting). This is the first
#: "candidate point" used to construct the search space grid. TODO: 
#: I think this should be a row in qraat.sitelist with name='center'.
#:  ~ Chris 1/2/14
center = np.complex(4260500, 574500)

class steering_vectors:
  
  def __init__(self, db_con, cal_id):
    ''' TODO ''' 
    deps = []

    # Get site locations.
    sites = csv(db_con=db_con, db_table='sitelist')

    sv_deps_by_site = {}

    for row in sites:
      deps.append(('sitelist', row.ID))

    # Get steering vector data.
    steering_vectors = {} # site.ID -> sv
    bearings = {}         # site.ID -> bearing
    to_be_removed = []
    cur = db_con.cursor()
    for site in sites:
      cur.execute('''SELECT ID, Bearing,
                            sv1r, sv1i, sv2r, sv2i,
                            sv3r, sv3i, sv4r, sv4i
                       FROM Steering_Vectors
                      WHERE SiteID=%d and Cal_InfoID=%d''' % (site.ID, cal_id))
      raw_data = cur.fetchall()
      prov_sv_ids = util.get_field(raw_data, 0)
      data_no_ids = util.remove_field(raw_data, 0)
      sv_data = np.array(data_no_ids,dtype=float)
      if sv_data.shape[0] > 0:
        steering_vectors[site.ID] = np.array(sv_data[:,1::2] + np.complex(0,1) * sv_data[:,2::2])
        sv_deps_by_site[site.ID] = prov_sv_ids
        bearings[site.ID] = np.array(sv_data[:,0])
      else:
        to_be_removed.append(site)
    while len(to_be_removed) > 0:
      sites.table.remove(to_be_removed.pop())

    # Format site locations as np.complex's.
    for site in sites:
      setattr(site, 'pos', np.complex(site.northing, site.easting))

    (self.sites, self.bearings, self.steering_vectors, 
     self.prov_sv_ids, self.deps, self.sv_deps_by_site) = (sites, bearings, steering_vectors, 
                                                           prov_sv_ids, deps, sv_deps_by_site)



class bearing: 
  ''' TODO ''' 

  def __init__(self, sv, est): 
  
    self.sites   = sv.sites
    self.id      = est.id
    self.site_id = est.site_id
    self.time    = est.timestamp

    record_provenance_from_site_data = False

    likelihoods = np.zeros((len(est), 360))
    for i in range(len(est)):
      try:
        G      = sv.steering_vectors[self.site_id[i]]
        G_deps = sv.sv_deps_by_site[self.site_id[i]]
      except KeyError:
        print >>sys.stderr, "position: error: no steering vectors for site ID=%d" % self.site_id[i]
        sys.exit(1)

      V     = est.ed[i, np.newaxis,:]
      V_dep = est.id[i]

      left_half = np.dot(V, np.conj(np.transpose(G)))
      bearing_likelihood = (left_half * np.conj(left_half)).real

      bearing_likelihood_deps = [('Steering_Vectors', x) for x in G_deps]
      bearing_likelihood_deps.append(('est', V_dep))

      likelihood_deps = {}
      for j, theta in enumerate(sv.bearings[self.site_id[i]]):
        likelihoods[i, theta] = bearing_likelihood[0, j]
        likelihood_deps[i, theta] = bearing_likelihood_deps

    self.likelihoods = likelihoods
    if record_provenance_from_site_data:
      self.likelihood_deps = likelihood_deps
    else:
      self.likelihood_deps = [] 


  def __len__(self): 
    return self.likelihoods.shape[0]

  def position_estimation(self, index_list, center, scale, half_span=15):
    ''' Estimate the position of a transmitter over time interval ``[i, j]``.

      Generate a set of candidate points centered around ``center``.
      Calculate the bearing to the receiver sites from each of this points.
      The log likelihood of a candidate corresponding to the actual location
      of the target transmitter over the time window is equal to the sum of
      the likelihoods of each of these bearings given the signal characteristics
      of the ESTs in the window. This method uses Bartlet's estimator. 
    '''

    #: Generate candidate points centered around ``center``.
    grid = np.zeros((half_span*2+1, half_span*2+1),np.complex)
    for e in range(-half_span,half_span+1):
      for n in range(-half_span,half_span+1):
        grid[e + half_span, n + half_span] = center + np.complex(n * scale, e * scale)

    #: The third dimension of the search space: bearings from each
    #: candidate point to each receiver site.
    site_bearings = {}
    for site in self.sites:
      #site_bearings[:,:,sv_index] = np.angle(grid - site.pos) * 180 / np.pi
      site_bearings[site.ID] = np.angle(grid - site.pos) * 180 / np.pi
    #site_bearings = np.zeros(np.hstack((grid.shape,len(self.sites))))

    #: Based on bearing self.likelihoods for EST's in time range, calculate
    #: the log likelihood of each candidate point.
    pos_likelihood = np.zeros(site_bearings[self.sites[0].ID].shape[0:2])
    for est_index in index_list:
      sv_index = self.site_id[est_index]
      try:
        pos_likelihood += np.interp(site_bearings[sv_index],
                                  range(-360, 360),
                                  np.hstack((self.likelihoods[est_index,:],
                                  self.likelihoods[est_index,:])) )
        # SEAN: Would use self.likelihood_deps right here if I was using them
      except KeyError:
        pass # Skip sites in the site list where we don't collect data. 
             # TODO perhaps there should be a row in qraat.sitelist that 
             # designates sites as qraat nodes. ~ Chris 1/2/14 

    return grid.flat[np.argmax(pos_likelihood)]




def calc_positions(bl, t_window, t_delta, verbose=False):
  ''' Calculate positions of a transmitter over a time interval. 
  
    The calculation is based on Bartlet's estimator. '''
  pos_est = []
  pos_est_deps = []
  est_ct = bl.likelihoods.shape[0]

  print "position: calculating position"
  if verbose:
    print "%15s %-19s %-19s %-19s" % ('time window',
              '100 meters', '10 meters', '1 meter')

  start_step = np.ceil(bl.time[0] / t_delta)
  while start_step*t_delta - (t_window / 2.0) < bl.time[0]:
    start_step += 1
  start_step -= 1

  end_step = np.floor(bl.time[-1] / t_delta)
  while end_step*t_delta + (t_window / 2.0) > bl.time[-1]:
    end_step -= 1
  end_step += 1

  try:
    for time_step in range(int(start_step),int(end_step)):

      # Find the indexes corresponding to the time window.
      est_index_list = np.where(
        np.abs(bl.time - time_step*t_delta - t_window / 2.0) 
          <= t_window / 2.0)[0]

      if len(est_index_list) > 0 and len(set(bl.site_id[est_index_list])) > 1:

        if verbose: 
          print "Time window {0} - {1}".format(
            time_step*t_delta - t_window / 2.0, time_step*t_delta + t_window)

        scale = 100
        pos = center
        while scale >= 1: # 100, 10, 1 meters ...
          pos = bl.position_estimation(est_index_list, pos, scale)
          if verbose:
            print "%8dn,%de" % (pos.real, pos.imag),
          scale /= 10

        pos_deps = []

        # Determine components of est that contribute to the computed position.
        for est_index in est_index_list:
          pos_deps.append(bl.id[est_index])
        pos_est.append((time_step*t_delta,
                        pos.imag,  # easting
                        pos.real)) # northing

        pos_est_deps.append({'est':tuple(pos_deps)})
        if verbose: print

  except KeyboardInterrupt: 
    pass

  return pos_est, pos_est_deps



def insert_positions(db_con, pos_est, pos_est_deps, tx_id):
    ''' Insert positions into database with provenance. ''' 
    cur = db_con.cursor()

    query = '''INSERT INTO Position
                (txid, timestamp, easting, northing)
               VALUES (%s, %s, %s, %s)'''
    #cur.executemany(, [(tx_id, pe[0], pe[1], pe[2]) for pe in pos_est])

    # Insert results into database.
    all_insertions = []
    for pos_est_index in range(len(pos_est)):
      this_pos_est = pos_est[pos_est_index]
      this_pos_est_deps = pos_est_deps[pos_est_index]
      cur.execute(query, (tx_id, this_pos_est[0], this_pos_est[1], this_pos_est[2]))
      pos_est_insertion_id = cur.lastrowid
      all_insertions.append(pos_est_insertion_id)
      handle_provenance_insertion(cur, this_pos_est_deps, {'Position':(pos_est_insertion_id,)})



def compress(s):
  ''' What's this for? *TODO* ''' 
  strings = []
  ss = sorted(s, reverse=True)

  last_num = None
  sequence_start = None

  while len(ss) != 0:
    i = ss.pop()
    if last_num is None:
      # the start
      sequence_start = i
    elif last_num + 1 == i:
      # still in sequence
      pass
    else:
      # sequence over
      if sequence_start == last_num:
        strings.append(str(sequence_start))
      else:
        strings.append('%d-%d' % (sequence_start, last_num))
      sequence_start = i
    last_num = i

  # add last
  if sequence_start == last_num:
    strings.append(str(sequence_start))
  else:
    strings.append('%d-%d' % (sequence_start, last_num))

  return ','.join(strings)


def handle_provenance_insertion(cur, depends_on, obj):
  ''' *TODO* add doc string ''' 
  query = 'insert into provenance (obj_table, obj_id, dep_table, dep_id) values (%s, %s, %s, %s);'
  prov_args = []
  for dep_k in depends_on.keys():
    for dep_v in depends_on[dep_k]:
      for obj_k in obj.keys():
        for obj_v in obj[obj_k]:
          args = (obj_k, obj_v, dep_k, dep_v)
          prov_args.append(args)
  cur.executemany(query, prov_args) 



class halfplane: 
  ''' A two-dimensional linear inequality. 

    Compute the slope and y-intercept of the line defined by point ``p`` 
    and bearing ``theta``. Format of ``p`` is np.complex(real=northing, 
    imag=easting). Also, ``pos`` is set to True if the vector theta goes 
    in a positive direction along the x-axis. 
  ''' 
  
  #: The types of plane constrains:
  #: greater than, less than, greater than
  #: or equal to, less than or equal to. 
  plane_t = util.enum('GT', 'LT', 'GE', 'LE')
  plane_string = { plane_t.GT : '>', 
                   plane_t.LT : '<', 
                   plane_t.GE : '>=', 
                   plane_t.LE : '<=' }

  def __init__ (self, p, theta):

    self.x_p = p.imag
    self.y_p = p.real
    self.m = np.tan(np.pi * theta / 180) 
    self.plane = None

    if (0 <= theta and theta <= 90) or (270 <= theta and theta <= 360):
      self.pos = True
    else: self.pos = False 

    if (0 <= theta and theta <= 180):
      self.y_pos = True
    else: self.y_pos = False

  def __repr__ (self): 
    s = 'y %s %.02f(x - %.02f) + %.02f' % (self.plane_string[self.plane], 
                                           self.m, self.x_p, self.y_p)
    return '%-37s' % s

  def __call__ (self, x): 
    return self.m * (x - self.x_p) + self.y_p

  def inverse(self, y): 
    return ((y - self.y_p) + (self.m * self.x_p)) / self.m

  @classmethod
  def from_bearings(cls, p, theta_i, theta_j):
    # TODO get plane constraints right.
    Ti = cls(p, theta_i)
    Ti.plane = cls.plane_t.GT
    Tj = cls(p, theta_j) 
    Tj.plane = cls.plane_t.GT
    return (Ti, Tj)    

  
