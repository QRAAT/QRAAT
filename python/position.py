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

import MySQLdb as mdb
import numpy as np
import time, os, sys

from csv import csv
from util import get_field, remove_field



# Get database credentials.
def get_db(view):
  try:
    db_config = csv("%s/db_auth" % os.environ['RMG_SERVER_DIR']).get(view=view)

  except KeyError:
    print >>sys.stderr, "position: error: undefined environment variables. Try `source rmg_env.`"
    sys.exit(1)

  except IOError, e:
    print >>sys.stderr, "position: error: missing DB credential file '%s'." % e.filename
    sys.exit(1)

  # Connect to the database.
  db_con = mdb.connect(db_config.host,
                       db_config.user,
                       db_config.password,
                       db_config.name)
  return db_con
  


#: Center of Quail Ridge reserve (northing, easting). This is the first
#: "candidate point" used to construct the search space grid. TODO: 
#: I think this should be a row in qraat.sitelist with name='center'.
#:  ~ Chris 1/2/14
center = np.complex(4260500, 574500)




class fella:  # TODO better name.
  
  def __init__(self, db_con, cal_id, tx_id, t_start, t_end):
    ''' TODO 

      This class contains the data structures for doing positiion estimation. 
    ''' 
    self.get_site_data(db_con, cal_id)
    self.get_est_data(db_con, t_start, t_end, tx_id)
    self.calc_likelihoods()

  def get_site_data(self, db_con, cal_id):
    print "position: fetching site and cal data"

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
      prov_sv_ids = get_field(raw_data, 0)
      data_no_ids = remove_field(raw_data, 0)
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

    # FIXME Minimizing code changes until I can verify prov workflow. 
    (self.sites, self.bearings, self.steering_vectors, 
     self.prov_sv_ids, self.deps, self.sv_deps_by_site) = (sites, bearings, steering_vectors, 
                                                           prov_sv_ids, deps, sv_deps_by_site)

  def get_est_data(self, db_con, t_start, t_end, tx_id):
    print "position: fetching pulses for transmitter and time range"
    
    cur = db_con.cursor()

    # Get pulses in time range.
    cur.execute('''SELECT ID, siteid, timestamp,
                          ed1r, ed1i, ed2r, ed2i,
                          ed3r, ed3i, ed4r, ed4i
                     FROM est
                    WHERE timestamp >= %s
                      AND timestamp <= %s
                      AND txid = %s
                    ORDER BY timestamp ASC''', (t_start,
                                                t_end,
                                                tx_id))

    raw_data = cur.fetchall()
    prov_est_ids = get_field(raw_data, 0)
    signal_data = np.array(raw_data, dtype=float)
    est_ct = signal_data.shape[0]
    if est_ct == 0:
      print >>sys.stderr, "position: fatal: no est records for selected time range."
      sys.exit(1)
    else: print "position: processing %d records" % est_ct

    sig_id =   np.array(signal_data[:,0], dtype=int)
    site_id =  np.array(signal_data[:,1], dtype=int)
    est_time = signal_data[:,2]
    signal =   signal_data[:,3::2]+np.complex(0,-1)*signal_data[:,4::2]

    # FIXME
    (self.sig_id, self.site_id, self.est_time, 
     self.signal, self.est_ids) = (sig_id, site_id, est_time, 
                                        signal, prov_est_ids)


  # Calculate the likelihood of each bearing for each pulse.
  def calc_likelihoods(self): 

    record_provenance_from_site_data = False

    print "position: calculating pulse bearing likelihoods"

    likelihoods = np.zeros((self.signal.shape[0],360))
    for i in range(self.signal.shape[0]):
      try:
        sv =  self.steering_vectors[self.site_id[i]]
        sv_deps = self.sv_deps_by_site[self.site_id[i]]
      except KeyError:
        print >>sys.stderr, "position: error: no steering vectors for site ID=%d" % self.site_id[i]
        sys.exit(1)

      sig = self.signal[i,np.newaxis,:]
      sig_dep = self.est_ids[i]
      left_half = np.dot(sig, np.conj(np.transpose(sv)))
      bearing_likelihood = (left_half * np.conj(left_half)).real
      bearing_likelihood_deps = [('Steering_Vectors', x) for x in sv_deps]
      bearing_likelihood_deps.append(('est', sig_dep))

      likelihood_deps = {}
      for j, value in enumerate(self.bearings[self.site_id[i]]):
        likelihoods[i, value] = bearing_likelihood[0, j]
        likelihood_deps[i, value] = bearing_likelihood_deps

    # FIXME
    self.likelihoods = likelihoods
    if record_provenance_from_site_data:
      self.likelihood_deps = likelihood_deps
    else:
      self.likelihood_deps = [] 
    return (self.likelihoods, self.likelihood_deps)


  def position_estimation(self, index_list, center, scale, half_span=15):
    ''' Estimate the position of a transmitter over time interval ``[i, j]``.

      Generate a set of candidate points centered around ``center``.
      Calculate the bearing to the receiver sites from each of this points.
      The log likelihood of a candidate corresponding to the actual location
      of the target transmitter over the time window is equal to the sum of
      the likelihoods of each of these bearings given the signal characteristics
      of the ESTs in the window.
    '''

    #: Generate candidate points centered around ``center``.
    grid = np.zeros((half_span*2+1, half_span*2+1),np.complex)
    for e in range(-half_span,half_span+1):
      for n in range(-half_span,half_span+1):
        grid[e + half_span, n + half_span] = center + np.complex(n * scale, e * scale)

    #: The third dimension of the search space: bearings from each
    #: candidate point to each receiver site.
    #site_bearings = np.zeros(np.hstack((grid.shape,len(self.sites))))
    site_bearings = {}
    for site in self.sites:
      #site_bearings[:,:,sv_index] = np.angle(grid - site.pos) * 180 / np.pi
      site_bearings[site.ID] = np.angle(grid - site.pos) * 180 / np.pi

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







def calc_positions(cal_id, tx_id, t_start, t_end, t_delta, t_window, verbose = False):
  db_con = get_db('writer')

  stuff = fella(db_con, cal_id, tx_id, t_start, t_end)

  pos_est, pos_est_deps = estimate_positions(stuff, t_window, t_delta, verbose) 

  insert_positions(db_con, pos_est, pos_est_deps, tx_id)
  return pos_est, stuff.sites


def estimate_positions(stuff, t_window, t_delta, verbose=False):
  #: Calculated positions (time, pos).
  pos_est = []
  pos_est_deps = []
  est_ct = stuff.likelihoods.shape[0]
  #: The time step (in seconds) for the position estimation
  #: calculation.
  #t_delta = options.t_delta

  #: Time averaging window (in seconds).
  #t_window = options.t_window


  print "position: calculating position"
  if verbose:
    print "%15s %-19s %-19s %-19s" % ('time window',
              '100 meters', '10 meters', '1 meter')
  start_step = np.ceil(stuff.est_time[0] / t_delta)
  while start_step*t_delta - (t_window / 2.0) < stuff.est_time[0]:
    start_step += 1
  start_step -= 1

  end_step = np.floor(stuff.est_time[-1] / t_delta)
  while end_step*t_delta + (t_window / 2.0) > stuff.est_time[-1]:
    end_step -= 1
  end_step += 1


  try:
    for time_step in range(int(start_step),int(end_step)):

      # Find the indexes corresponding to the time window.
      est_index_list = np.where(np.abs(stuff.est_time - time_step*t_delta - t_window / 2.0) <= t_window / 2.0)[0]#where returns a tuple for some reason

      if len(est_index_list) > 0 and len(set(stuff.site_id[est_index_list])) > 1:
        if verbose: print "Time window {0} - {1}".format(time_step*t_delta - t_window / 2.0, time_step*t_delta + t_window)
        scale = 100
        pos = center
        while scale >= 1: # 100, 10, 1 meters ...
          pos = stuff.position_estimation(est_index_list, pos, scale)
          if verbose:
            print "%8dn,%de" % (pos.real, pos.imag),
          scale /= 10
        pos_deps = []
        # Determine components of est that contribute to the computed position.
        for est_index in est_index_list:
          pos_deps.append(stuff.est_ids[est_index])
        pos_est.append((time_step*t_delta,
                        pos.imag,  # easting
                        pos.real)) # northing

        pos_est_deps.append({'est':tuple(pos_deps)})
        if verbose: print

  except KeyboardInterrupt: pass

  return pos_est, pos_est_deps

def insert_positions(db_con, pos_est, pos_est_deps, tx_id):
    cur = db_con.cursor()

    insert_statement = '''INSERT INTO Position
                        (txid, timestamp, easting, northing)
                       VALUES (%s, %s, %s, %s)'''
    # Insert results into database.
    #cur.executemany(, [(tx_id, pe[0], pe[1], pe[2]) for pe in pos_est])

    all_insertions = []
    for pos_est_index in range(len(pos_est)):
      this_pos_est = pos_est[pos_est_index]
      this_pos_est_deps = pos_est_deps[pos_est_index]
      cur.execute(insert_statement, (tx_id, this_pos_est[0], this_pos_est[1], this_pos_est[2]))
      pos_est_insertion_id = cur.lastrowid
      all_insertions.append(pos_est_insertion_id)
      handle_provenance_insertion(cur, this_pos_est_deps, {'Position':(pos_est_insertion_id,)})

def compress(s):

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
  query = 'insert into provenance (obj_table, obj_id, dep_table, dep_id) values (%s, %s, %s, %s);'
  prov_args = []
  for dep_k in depends_on.keys():
    for dep_v in depends_on[dep_k]:
      for obj_k in obj.keys():
        for obj_v in obj[obj_k]:
          args = (obj_k, obj_v, dep_k, dep_v)
          prov_args.append(args)
  # FIXME temporarily commented this out until I have the prov schema.
  #cur.executemany(query, prov_args) 

