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

import qraat
import numpy as np
import time, os, sys
import random

try:
  import MySQLdb as mdb
except ImportError: pass

query_insert_pos = '''INSERT INTO position
                       (deploymentID, timestamp, easting, northing, 
                        utm_zone_number, utm_zone_letter, likelihood, activity)
                      VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''' 

query_insert_bearing = '''INSERT INTO bearing 
                           (deploymentID, siteID, timestamp, bearing, likelihood, activity)
                          VALUES (%s, %s, %s, %s, %s, %s)''' 

def get_center(db_con):
  cur = db_con.cursor()
  cur.execute('''SELECT northing, easting 
                   FROM qraat.location
                  WHERE name = 'center' ''')
  (n, e) = cur.fetchone()
  return np.complex(n, e)


# Get est's from the database, applying a filter. Return a set of
# estID's which are fed to the class signal. 
# TODO Curry these?  
# TODO Grab band filte rfalues from tx_pulse.  

def get_est_ids_timefilter(db_con, dep_id, t_start, t_end, thresh):
  cur = db_con.cursor()
  cur.execute('''SELECT ID 
                   FROM est
                   JOIN estscore ON est.ID = estscore.estID
                  WHERE deploymentID=%d
                    AND timestamp >= %f 
                    AND timestamp <= %f
                    AND thresh >= %f''' % (dep_id, t_start, t_end, thresh))
  return [ int(row[0]) for row in cur.fetchall() ]

def get_est_ids_bandfilter(db_con, dep_id, t_start, t_end):
  cur = db_con.cursor()
  cur.execute('''SELECT ID 
                   FROM est
                  WHERE deploymentID=%d
                    AND timestamp >= %f 
                    AND timestamp <= %f 
                    AND band3 < 150 
                    AND band10 < 900''' % (dep_id, t_start, t_end))
  return [ int(row[0]) for row in cur.fetchall() ]

def get_est_ids(db_con, dep_id, t_start, t_end):
  cur = db_con.cursor()
  cur.execute('''SELECT ID 
                   FROM est
                  WHERE deploymentID=%d
                    AND timestamp >= %f 
                    AND timestamp <= %f''' % (dep_id, t_start, t_end))
  return [ int(row[0]) for row in cur.fetchall() ]


class steering_vectors:
  ''' Encapsulate steering vectors. 
    
    The bearings and their corresponding steering vectors are stored
    in dictionaries indexed by site ID. This class also stores 
    provenance information for bearing likelihood calculation and 
    position estimation. 

    :param cal_id: Calibration ID. 
    :type cal_id: int
  ''' 
  
  def __init__(self, db_con, cal_id):
    deps = []

    # Get site locations.
    sites = qraat.csv.csv(db_con=db_con, db_table='site')
    sv_deps_by_site = {}

    for row in sites:
      deps.append(('site', row.ID))

    # Get steering vector data.
    steering_vectors = {} # site.ID -> sv
    bearings = {}         # site.ID -> bearing
    to_be_removed = []
    cur = db_con.cursor()
    for site in sites:
      cur.execute('''SELECT ID, Bearing,
                            sv1r, sv1i, sv2r, sv2i,
                            sv3r, sv3i, sv4r, sv4i
                       FROM steering_vectors
                      WHERE SiteID=%d and Cal_InfoID=%d''' % (site.ID, cal_id))
      raw_data = cur.fetchall()
      prov_sv_ids = qraat.util.get_field(raw_data, 0)
      data_no_ids = qraat.util.remove_field(raw_data, 0)
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


  def get_utm_zone(self):
    ''' Get utm zone letter and number for position estimation. 
    
      We expect all sites to have the same UTM zone. If this isn't 
      true, throw an error. 
    ''' 
    (utm_zone_letter, utm_zone_number) = (self.sites[0].utm_zone_letter, 
                                          self.sites[0].utm_zone_number)
    for site in self.sites: 
      if site.utm_zone_letter != utm_zone_letter or site.utm_zone_number != utm_zone_number: 
        raise qraat.error.QraatError('UTM zone doesn\'t match for all sites; can\'t compute positions.')
    return (utm_zone_letter, utm_zone_number)



class signal:
  ''' Encapsulate pulse signal data. 
  
    I'm evaluating what functionality I want from the est object so 
    that the data is more chewable in bearing and position calculation.
    My thinking now is that this could replace est entirely and be 
    the interface between det's, DB, and file. For now, it will serve
    useful for exploring. 
  ''' 

  #: Number of channels. 
  N = 4

  def __init__(self, db_con, est_ids): 

    if len(est_ids) == 0:
      self.id = self.site_id = self.dep_id = self.timestamp = np.array([])
      self.edsp = self.ed = self.nc = np.array([])
      self.signal_ct = 0

    else: 
      # Store eigenvalue decomposition vectors and noise covariance
      # matrices in NumPy arrays. 
      
      cur = db_con.cursor()
      cur.execute('''SELECT ID, siteID, deploymentID, timestamp, edsp, 
                            ed1r,  ed1i,  ed2r,  ed2i,  ed3r,  ed3i,  ed4r,  ed4i, 
                            nc11r, nc11i, nc12r, nc12i, nc13r, nc13i, nc14r, nc14i, 
                            nc21r, nc21i, nc22r, nc22i, nc23r, nc23i, nc24r, nc24i, 
                            nc31r, nc31i, nc32r, nc32i, nc33r, nc33i, nc34r, nc34i, 
                            nc41r, nc41i, nc42r, nc42i, nc43r, nc43i, nc44r, nc44i
                       FROM est
                      WHERE ID in (%s)''' % ','.join(map(lambda(x) : str(x), est_ids)))
    
      raw = np.array(cur.fetchall(), dtype=float)

      # Metadata. 
      (self.id, 
       self.site_id, 
       self.dep_id) = (np.array(raw[:,i], dtype=int) for i in range(0,3))
      self.timestamp = raw[:,3]
      raw = raw[:,4:]

      # Signal power. 
      self.edsp = raw[:,0]
      raw = raw[:,1:]

      # Signal vector, N x 1.
      self.ed = raw[:,0:8:2] + np.complex(0,-1) * raw[:,1:8:2]
      raw = raw[:,8:]

      # Noise covariance matrix, N x N. 
      self.nc = raw[:,0::2] + np.complex(0,-1) * raw[:,1::2]
      self.nc = self.nc.reshape(raw.shape[0], self.N, self.N)

      self.signal_ct = self.id.shape[0]

  def __len__(self): 
    return self.signal_ct

  def activity_per_site(self, index_list):
    ''' Return activity metric per site. 

       The activity metric we use is the standard deviation the signal
       power (edsp). 
    
     :returns: Mapping of siteID to a float.
     :rtype: dict
    '''
    activity = {}
    for index in index_list:
      if not activity.get(self.site_id[index]):
        activity[self.site_id[index]] = [self.edsp[index]]
      else: 
        activity[self.site_id[index]].append(self.edsp[index])

    for (site_id, x) in activity.iteritems():
      activity[site_id] = np.std(x) / np.mean(x)
    
    return activity



class Position:
  
  def __init__(self, db_con=None, pos_ids=[]): 
    self.table = []
    if len(pos_ids) > 0:
      cur = db_con.cursor()
      cur.execute('''SELECT ID, deploymentID, timestamp, easting, northing, 
                            utm_zone_number, utm_zone_letter, likelihood,
                            activity
                       FROM position
                      WHERE ID in (%s)
                      ORDER BY timestamp ASC''' % ','.join(map(lambda(x) : str(x), pos_ids)))
      for row in cur.fetchall():
        self.table.append(row)

  def __len__(self):
    return len(self.table)

  def __getitem__(self, i):
    return self.table[i]

  def insert_db(self, db_con):
    cur = db_con.cursor()
    for (id, dep_id, timestamp, easting, northing, 
         utm_zone_number, utm_zone_letter, likelihood, 
         activity, pos_deps) in self.table: 
      cur.execute(query_insert_pos, (dep_id, 
                                     timestamp, 
                                     easting,  # pos.imag
                                     northing, # pos.real
                                     utm_zone_number,
                                     utm_zone_letter,
                                     likelihood, 
                                     activity))
      pos_id = cur.lastrowid                               
      handle_provenance_insertion(cur, pos_deps, {'position':(pos_id,)})

  def export_kml(self, name, dep_id):

    fd = open('%s_pos.kml' % name, 'w')
    fd.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    fd.write('<kml xmlns="http://www.opengis.net/kml/2.2"\n')
    fd.write(' xmlns:gx="http://www.google.com/kml/ext/2.2">\n')
    fd.write('<Folder>\n')
    fd.write('  <Placemark>\n')
    fd.write('  <MultiGeometry>\n')
    fd.write('    <name>%s (deploymentID=%d) position cloud</name>\n' % (name, dep_id))
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



class Bearing: 
  
  def __init__(self, db_con=None, bearing_ids=[]):
    self.table = []
    if len(bearing_ids) > 0:
      cur = db_con.cursor()
      cur.execute('''SELECT ID, deploymentID, siteID, timestamp, bearing,
                            likelihood, activity
                       FROM bearing
                      WHERE ID in (%s)
                      ORDER BY timestamp ASC''' % ','.join(map(lambda(x) : str(x), bearing_ids)))
      for row in cur.fetchall():
        self.table.append(row)

  def __len__(self):
    return len(self.table)

  def __getitem__(self, i):
    return self.table[i]

  def insert_db(self, db_con):
    cur = db_con.cursor()
    for (id, dep_id, site_id, timestamp, bearing, 
         likelihood, activity) in self.table: 
      cur.execute(query_insert_bearing, (dep_id,
                                         site_id, 
                                         timestamp, 
                                         bearing, 
                                         likelihood, 
                                         activity))
    
  def export_kml(self, name, dep_id, site_id):
    pass # TODO 




class position_estimator: 
  ''' Calculate and store bearing likelihood distributions for a signal window.

    The likelihoods calculated for the bearings are based on Bartlet's estimator. 

    :param sv: Steering vectors per site. 
    :type sv: qraat.position.steering_vectors
    :param sig: A set of signals for a given transmitter and time window.  
    :type qraat.position.signal: 
  ''' 

  def __init__(self, sv, sig): 
  
    self.sites   = sv.sites
    self.id      = sig.id
    self.site_id = sig.site_id
    self.time    = sig.timestamp

    record_provenance_from_site_data = False

    (self.utm_zone_letter, self.utm_zone_number) = sv.get_utm_zone()

    likelihoods = np.zeros((len(sig), 360))
    for i in range(len(sig)):
      try:
        G      = sv.steering_vectors[self.site_id[i]]
        G_deps = sv.sv_deps_by_site[self.site_id[i]]
      except KeyError:
        print >>sys.stderr, "position: error: no steering vectors for site ID=%d" % self.site_id[i]
        sys.exit(1)

      V     = sig.ed[i, np.newaxis,:]
      V_dep = sig.id[i]

      # Bartlet's estimator. 
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
  
  def get_utm_zone(self):
    ''' Get UTM zone letter and number. '''
    return (self.utm_zone_letter, self.utm_zone_number)

  def __len__(self): 
    return self.likelihoods.shape[0]


  def likelihood_per_site(self, index_list):
    ''' Return summed likelihood distributions per site over time interval. 
    
     :returns: Mapping of siteID to bearing bearing distribution. 
     :rtype: dict
    ''' 
    ll_per_site = {}
    for e in index_list: 
      if ll_per_site.get(self.site_id[e]) == None:
        ll_per_site[self.site_id[e]] = self.likelihoods[e,]
      else: 
        ll_per_site[self.site_id[e]] += self.likelihoods[e,]
    return ll_per_site

  
  def bearing_estimator(self, ll_per_site):
    ''' Estimate bearing of a transmitter from a each site. 
    
     :return: Mapping of siteID to (bearing, likelihood) tuple.
     :rtype: dict
    ''' 
    bearing = {}
    for (site_id, ll) in ll_per_site.iteritems():
      theta = np.argmax(ll)
      bearing[site_id] = (theta, ll[theta])
    return bearing


  def position_estimator(self, ll_per_site, center, scale, half_span=15):
    ''' Estimate the position of a transmitter over time interval.

      Generate a set of candidate points centered around ``center``.
      Calculate the bearing to the receiver sites from each of this points.
      The log likelihood of a candidate corresponding to the actual location
      of the target transmitter over the time window is equal to the sum of
      the likelihoods of each of these bearings given the signals in the 
      window. Return an estimate of the maximal point along with its 
      likelihood.
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
      site_bearings[site.ID] = np.angle(grid - site.pos) * 180 / np.pi

    #: Based on bearing self.likelihoods for EST's in time range, calculate
    #: the log likelihood of each candidate point.
    pos_likelihood = np.zeros(site_bearings[self.sites[0].ID].shape[0:2])
    for (site_id, ll) in ll_per_site.iteritems():
      pos_likelihood += np.interp(site_bearings[site_id], 
                                  range(-360, 360),
                                  np.hstack((ll, ll)) )
    
    max_index = np.argmax(pos_likelihood)
    return (grid.flat[max_index], round(pos_likelihood.flat[max_index], 6))


  def jitter_estimator(self, ll_per_site, center, scale, half_span=15):
    ''' Position estimator with a little jitter around the center. 
    
      Vary the northing and easting of the center uniformly plus 
      or minus the scaling factor. 
    ''' 

    (j_neg, j_pos) = (scale / -2, scale / 2)
    j_center = center + np.complex(round(random.uniform(j_neg, j_pos), 2), 
                                   round(random.uniform(j_neg, j_pos), 2))
    
    return self.position_estimator(ll_per_site, j_center, scale, half_span) 



class mle_position_estimator (position_estimator): 
  ''' Calculate bearing distribution with the minimum likelihood estimator. ''' 

  def __init__(self, sv, sig): 
    self.sites   = sv.sites
    self.id      = sig.id
    self.site_id = sig.site_id
    self.time    = sig.timestamp

    record_provenance_from_site_data = False

    self.likelihoods = np.zeros((len(sig), 360)) # TODO 
    self.likelihood_deps = []                    # TODO 



def calc_windows(bl, t_window, t_delta):
  ''' Divide est data into uniform time windows. 

    Return a tuple with the timestamp of the start of the window 
    and a list of indices corresponding to the est's wihtin the 
    window. 

    :param bl: Bearing likelihoods for time range. 
    :type bl: qraat.position.bearing
    :param t_window: Number of seconds for each time window. 
    :type t_window: int
    :param t_delta: Interval of time between each position calculation.
    :type t_delta: int
  '''

  start_step = np.ceil(bl.time[0] / t_delta)
  while start_step*t_delta - (t_window / 2.0) < bl.time[0]:
    start_step += 1
  start_step -= 1

  end_step = np.floor(bl.time[-1] / t_delta)
  while end_step*t_delta + (t_window / 2.0) > bl.time[-1]:
    end_step -= 1
  end_step += 1
  
  for time_step in range(int(start_step),int(end_step)):

    # Find the indexes corresponding to the time window.
    est_index_list = np.where(
      np.abs(bl.time - time_step*t_delta - t_window / 2.0) 
        <= t_window / 2.0)[0]

    if len(est_index_list) > 0:
      yield (time_step * t_delta, est_index_list)



def calc_positions(signal, bl, center, utm_zone_letter, utm_zone_number, t_window, t_delta, dep_id, verbose=False):
  ''' Calculate positions of a transmitter over a time interval. 
  
  '''
  pos_est = [] 

  if verbose:
    print "%15s %-19s %-19s %-19s" % ('time window',
              '100 meters', '10 meters', '1 meter')

  position = Position()
  bearing = Bearing()

  for (t, index_list) in calc_windows(bl, t_window, t_delta): 
   
    pos = ll = pos_deps = pos_activity = None

    # Calculate activiy. (siteID -> activity.) 
    activity = signal.activity_per_site(index_list)

    # Calculate most likely bearings. (siteID -> (theta, ll[theta]).)
    ll_per_site = bl.likelihood_per_site(index_list)
    theta = bl.bearing_estimator(ll_per_site)

    # Zip together bearing and activity
    # TODO make sure activity[site_id] = None if it couldn't be done. 
    # TODO break up this data structure since it's not necesssary 
    #      anymore. 
    for site_id in theta.keys(): 
      theta[site_id] = theta[site_id] + (activity[site_id],)
    
    # Calculate position if data is available. 
    if (len(set(bl.site_id[index_list])) > 1): 

      # Activity for a position is given as the arithmetic mean of 
      # of the standard deviations of signal power per site.
      pos_activity = np.mean([activity for (_, _, activity) in theta.values()])

      if verbose: 
        print "Time window {0} - {1}".format(
          t - t_window / 2.0, t + t_window)

      # Calculate position 
      scale = 100
      pos = center
      while scale >= 1: # 100, 10, 1 meters ...
        (pos, ll) = bl.jitter_estimator(ll_per_site, pos, scale)
        if verbose:
          print "%8dn,%de" % (pos.real, pos.imag),
        scale /= 10

      # Determine components of est that contribute to the computed position.
      pos_deps = []
      for est_index in index_list:
        pos_deps.append(bl.id[est_index])
      pos_deps = {'est': tuple(pos_deps)}

      if verbose: print
   
    if pos: # TODO utm
      position.table.append((None, dep_id, t, pos.imag, pos.real, utm_zone_number,
                                             utm_zone_letter, ll, pos_activity, pos_deps))
    
    for (site_id, (theta, ll, activity)) in theta.iteritems():
      bearing.table.append((None, dep_id, site_id, t, theta, ll, activity))

  return (bearing, position)








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
  plane_t = qraat.util.enum('GT', 'LT', 'GE', 'LE')
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
    Ti = cls(p, theta_i)
    Tj = cls(p, theta_j) 
    if Ti.pos:
      Ti.plane = cls.plane_t.GT
      if not Tj.pos:
        Tj.plane = cls.plane_t.GT 
      else: Tj.plane = cls.plane_t.LT
    else:
      Ti.plane = cls.plane_t.LT
      if Tj.pos:
        Tj.plane = cls.plane_t.LT
      else: Tj.plane = cls.plane_t.GT
    return (Ti, Tj)    

  
