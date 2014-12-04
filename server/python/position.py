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
import utm
#from scipy.interpolate import interp1d #spline interpolation
import scipy.interpolate

num_ch = 4

def get_center(db_con):
  cur = db_con.cursor()
  cur.execute('''SELECT northing, easting, utm_zone_number, utm_zone_letter 
                   FROM qraat.location
                  WHERE name = 'center' ''')
  (n, e, utm_zone_number, utm_zone_letter) = cur.fetchone()
  return np.complex(n, e), utm_zone_number, utm_zone_letter

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

    # Get site locations.
    self.sites = qraat.csv.csv(db_con=db_con, db_table='site')

    # Get steering vector data.
    self.steering_vectors = {} # site.ID -> sv
    self.bearings = {}         # site.ID -> bearing
    self.svID = {}
    self.calID = {}
    to_be_removed = []
    cur = db_con.cursor()
    for site in self.sites:
      cur.execute('''SELECT ID, Bearing,
                            sv1r, sv1i, sv2r, sv2i,
                            sv3r, sv3i, sv4r, sv4i
                       FROM steering_vectors
                      WHERE SiteID=%s and Cal_InfoID=%s
                   ORDER BY Bearing''', (site.ID, cal_id))
      raw_data = cur.fetchall()
      sv_data = np.array(raw_data,dtype=float)
      if sv_data.shape[0] > 0:
        self.steering_vectors[site.ID] = np.array(sv_data[:,2::2] + np.complex(0,1) * sv_data[:,3::2])
        self.bearings[site.ID] = np.array(sv_data[:,1])
        self.svID[site.ID] = np.array(sv_data[:,0], dtype=int)
        self.calID[site.ID] = cal_id
      else:
        to_be_removed.append(site)
    while len(to_be_removed) > 0:
      self.sites.table.remove(to_be_removed.pop())

    # Format site locations as np.complex's.
    for site in self.sites:
      setattr(site, 'pos', np.complex(site.northing, site.easting))

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


class per_site_data:

  def __init__(self):
    self.num_est = 0
    self.num_bearing = 0
    self.estID = np.zeros((self.num_est,),dtype = int)
    self.timestamp = np.zeros((self.num_est,),dtype = float)
    self.power = np.zeros((self.num_est,),dtype = float)
    self.signal_vector = np.zeros((self.num_est,num_ch),dtype = int)
    self.site_position = np.complex(0,0)
    self.bearing = np.zeros((self.num_bearing,),dtype = float)
    self.bearing_likelihood = np.zeros((self.num_est, self.num_bearing), dtype=float)
    self.bearing_likelihood_function = lambda : None
    self.bearingID = 0
    self.calID = 0

  def time_filter(self, t_start, t_stop):
    mask = (self.timestamp < t_stop) * (self.timestamp > t_start)
    new_data = per_site_data()
    new_data.num_est = np.sum(mask)
    new_data.num_bearing = self.num_bearing
    new_data.site_position = self.site_position
    new_data.bearing = self.bearing
    new_data.estID = self.estID[mask]
    new_data.timestamp = self.timestamp[mask]
    new_data.signal_vector = self.signal_vector[mask, :]
    new_data.power = self.power[mask]
    new_data.bearing_likelihood = self.bearing_likelihood[mask,:]
    return new_data

  def formulate_bearing_llh(self):
    if self.num_est > 0:
      sum_bearing_likelihoods = np.sum(self.bearing_likelihood,0) #normalize?
      upper_half = np.where(self.bearing < 180)#returns tuple with len()=dimensionality
      last_index = upper_half[0][-1] + 1
      lower_half = np.where(self.bearing >= 180)
      first_index = lower_half[0][0] - 1
      bearing_domain = np.hstack((self.bearing[[first_index]]-360,
                                  self.bearing[lower_half]-360,
                                  self.bearing[upper_half],
                                  self.bearing[[last_index]]))
      likelihood_range = np.hstack((sum_bearing_likelihoods[[first_index]],
                                    sum_bearing_likelihoods[lower_half],
                                    sum_bearing_likelihoods[upper_half],
                                    sum_bearing_likelihoods[[last_index]]))
      self.bearing_likelihood_function = scipy.interpolate.InterpolatedUnivariateSpline(bearing_domain,likelihood_range)

  def get_activity(self):
    a = None
    if self.num_est > 0:
      a = np.std(self.power) / np.mean(self.power)
    return a

  def bearing_estimate(self):
    bearing_likelihood = np.sum(self.bearing_likelihood, 0)
    max_index = np.argmax(bearing_likelihood)
    theta_hat = self.bearing[max_index]
    norm_max_likelihood = bearing_likelihood[max_index] / float(self.num_est)
    return theta_hat, norm_max_likelihood

class estimator:

  def __init__(self, deploymentID, t_start, t_stop, t_window, t_delta):

    self.deploymentID = deploymentID
    self.t_start = t_start
    self.t_stop = t_stop
    self.t_window = t_window
    self.t_delta = t_delta
    self.num_est = 0
    self.per_site = dict()
    self.max_estID = 0


  def get_est_data(self, db_con, score_threshold):
    cur = db_con.cursor()
    self.num_est = cur.execute('''SELECT ID, siteID, timestamp, edsp, 
                            ed1r,  ed1i,  ed2r,  ed2i,  ed3r,  ed3i,  ed4r,  ed4i 
                   FROM est
                   JOIN estscore ON est.ID = estscore.estID
                  WHERE deploymentID={0:d}
                    AND timestamp >= {1:f} 
                    AND timestamp <= {2:f}
                    AND (score / theoretical_score) > {3:f}'''.format(
                         self.deploymentID, self.t_start-self.t_window,
                         self.t_stop+self.t_window, score_threshold))
    if self.num_est:
      raw_db = cur.fetchall()
      raw_data = np.array(raw_db, dtype=float)
      estID = raw_data[:,0]
      self.max_estID = np.max(estID)
      siteID = raw_data[:,1]
      timestamp = raw_data[:,2]
      power = raw_data[:,3]
      signal_vector = np.zeros((raw_data.shape[0],num_ch),dtype=np.complex)
      for j in range(num_ch):
        signal_vector[:,j] = raw_data[:,2*j+4] + np.complex(0,-1)*raw_data[:,2*j+5]
      for site in set(siteID):
        temp_data = per_site_data()
        temp_data.estID = estID[siteID == site]
        temp_data.timestamp = timestamp[siteID == site]
        temp_data.power = power[siteID == site]
        temp_data.signal_vector = signal_vector[siteID == site]
        temp_data.num_est = np.sum(siteID == site)
        self.per_site[site] = temp_data
        
    return self.num_est


  def get_bearing_likelihood(self, sv):

    for site, data in self.per_site.iteritems():
      # Bartlet's estimator.
      V = data.signal_vector #records X channels
      try:
        G = sv.steering_vectors[site] #bearings X channels
        data.bearing = sv.bearings[site]
        data.calID = sv.calID[site]
      except KeyError:
        #no steering vectors or bearings for site
        data.num_bearing = 0
        data.bearing = np.zeros((0,),dtype=float)
        data.bearing_likelihood = np.zeros((V.shape[0], 0), dtype = float)
        continue
      left_half = np.dot(V, np.conj(np.transpose(G))) #records X bearings
      data.bearing_likelihood = np.real(left_half * np.conj(left_half)) #records X bearings
      data.num_bearing = data.bearing.shape[0]
      data.site_position = sv.sites.get(ID=site).pos
      
  def time_filter(self, t_start, t_stop):
    filtered_dict = dict()
    total_est = 0
    if t_stop > self.t_start and t_start < self.t_stop:
      for site, data in self.per_site.iteritems():
        new_data = data.time_filter(t_start, t_stop)
        if new_data.num_est > 0:
          total_est += new_data.num_est        
          filtered_dict[site] = new_data
    new_estimator = estimator(self.deploymentID, t_start, t_stop, 0, 0)
    new_estimator.num_est = total_est
    new_estimator.per_site = filtered_dict
    return new_estimator

  def windowed(self):
    half_window = self.t_window / 2.0
    time_center = np.ceil((self.t_start - half_window) / float(self.t_delta)) * self.t_delta
    while self.t_stop > (time_center - half_window): 
      yield self.time_filter(time_center - half_window,
                             time_center + half_window)
      time_center += self.t_delta


  def insert_bearings(self, db_con, dep_id=None):
    if dep_id is None: 
      dep_id = self.deploymentID
    timestamp = (self.t_start + self.t_stop) / 2.0
    cur = db_con.cursor()
    for site, data in self.per_site.iteritems():
      if data.num_bearing > 0 and data.num_est > 0:
        theta_hat, norm_max_likelihood = data.bearing_estimate()
        activity = data.get_activity()
        cur.execute('''INSERT INTO bearing 
                   (deploymentID, siteID, timestamp, bearing, likelihood, activity)
                   VALUES (%s, %s, %s, %s, %s, %s)''',
                   (dep_id, site, timestamp,
                    theta_hat, norm_max_likelihood, activity))
        data.bearingID = cur.lastrowid
        handle_provenance_insertion(cur, {'est':tuple(data.estID), 'calibration_information':(data.calID,)}, {'bearing':(data.bearingID,)})
    
                    
  def get_position_likelihood(self, positions):
    likelihoods = np.zeros(positions.shape, dtype=float)
    for site, data in self.per_site.iteritems():
      bearing_to_positions = np.angle(positions - data.site_position) * 180 / np.pi
      #likelihoods += data.bearing_likelihood_function(bearing_to_positions)
      likelihoods += data.bearing_likelihood_function(bearing_to_positions.flat).reshape(bearing_to_positions.shape)
    return likelihoods

  def get_canidate_positions(self, center, scale, half_span=15):
    grid = np.zeros((half_span*2+1, half_span*2+1),np.complex)
    for e in range(-half_span,half_span+1):
      for n in range(-half_span,half_span+1):
        grid[e + half_span, n + half_span] = center + np.complex(n * scale, e * scale)
    return grid

  def position_estimate(self, center_position):
    for data in self.per_site.itervalues():
      data.formulate_bearing_llh()
    scale = 100
    p_hat = center_position
    while scale >= 1:
      positions = self.get_canidate_positions(p_hat, scale)
      likelihoods = self.get_position_likelihood(positions)
      max_index = np.argmax(likelihoods)
      p_hat = positions.flat[max_index]
      max_likelihood = likelihoods.flat[max_index]
      scale /= 10
    return p_hat, max_likelihood

  def get_activity(self):
    return np.mean([ s.get_activity() for s in self.per_site.itervalues() ])

  def insert_positions(self, db_con, center=None, dep_id=None):
    if len(self.per_site) > 1:
      if center is None:
        (center_position, utm_number, utm_letter) = get_center(db_con)
      else:
        (center_position, utm_number, utm_letter) = center
      if dep_id is None: dep_id = self.deploymentID
      timestamp = (self.t_start + self.t_stop) / 2.0
      position_hat, likelihood = self.position_estimate(center_position)
      activity = self.get_activity()
      lat, lon = utm.to_latlon(position_hat.imag, position_hat.real, utm_number, utm_letter)
      cur = db_con.cursor()
      cur.execute('''INSERT INTO position
                         (deploymentID, timestamp, easting, northing, 
                          utm_zone_number, utm_zone_letter, likelihood, 
                          activity, latitude, longitude)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                     (dep_id, timestamp, position_hat.imag, position_hat.real,
                      utm_number, utm_letter, likelihood,
                      activity, round(lat,6), round(lon,6)))
      self.positionID = cur.lastrowid
      bearingID = [ data.bearingID for data in self.per_site.itervalues() ]
      handle_provenance_insertion(cur, {'bearing':bearingID}, {'position':(self.positionID,)})


def handle_provenance_insertion(cur, depends_on, obj):
  ''' Insert provenance data into database ''' 
  query = 'insert into provenance (obj_table, obj_id, dep_table, dep_id) values (%s, %s, %s, %s);'
  prov_args = []
  for dep_k in depends_on.keys():
    for dep_v in depends_on[dep_k]:
      for obj_k in obj.keys():
        for obj_v in obj[obj_k]:
          args = (obj_k, obj_v, dep_k, dep_v)
          prov_args.append(args)
  cur.executemany(query, prov_args) 


##############################################
# below this line is depricated, I think -Todd
##############################################













import random

# Get est's from the database, applying a filter. Return a set of
# estID's which are fed to the class signal. 

def get_est_ids_timefilter(db_con, dep_id, t_start, t_end, thresh):
  cur = db_con.cursor()
  cur.execute('''SELECT ID, siteID, deploymentID, timestamp, edsp, 
                            ed1r,  ed1i,  ed2r,  ed2i,  ed3r,  ed3i,  ed4r,  ed4i, 
                   FROM est
                   JOIN estscore ON est.ID = estscore.estID
                  WHERE deploymentID=%d
                    AND timestamp >= %f 
                    AND timestamp <= %f
                    AND (score / theoretical_score) > %f''' % (
                                      dep_id, t_start, t_end, thresh))
  raw_db = cur.fetchall()
  estID = [ int(row[0]) for row in raw_db ]
  signal_dict = get_signal_dict(raw_db, dep_id) 
  return estID, signal_dict

def get_est_ids_bandfilter(db_con, dep_id, t_start, t_end, band3 = 150, band10 = 900):
  cur = db_con.cursor()
  cur.execute('''SELECT ID, siteID, timestamp, edsp, 
                            ed1r,  ed1i,  ed2r,  ed2i,  ed3r,  ed3i,  ed4r,  ed4i, 
                   FROM est
                  WHERE deploymentID=%d
                    AND timestamp >= %f 
                    AND timestamp <= %f 
                    AND band3 < %f 
                    AND band10 < %f''' % (dep_id, t_start, t_end, band3, band10))
  raw_db = cur.fetchall()
  estID = [ int(row[0]) for row in raw_db ]
  signal_dict = get_signal_dict(raw_db, dep_id) 
  return estID, signal_dict

def get_est_ids(db_con, dep_id, t_start, t_end):
  cur = db_con.cursor()
  cur.execute('''SELECT ID, siteID, timestamp, edsp, 
                            ed1r,  ed1i,  ed2r,  ed2i,  ed3r,  ed3i,  ed4r,  ed4i, 
                   FROM est
                  WHERE deploymentID=%d
                    AND timestamp >= %f 
                    AND timestamp <= %f''' % (dep_id, t_start, t_end))
  raw_db = cur.fetchall()
  estID = [ int(row[0]) for row in raw_db ]
  signal_dict = get_signal_dict(raw_db, dep_id) 
  return estID, signal_dict










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
         activity, pos_dependancies) in self.table: 
      cur.execute(query_insert_pos, (dep_id, 
                                     timestamp, 
                                     easting,  # pos.imag
                                     northing, # pos.real
                                     utm_zone_number,
                                     utm_zone_letter,
                                     likelihood, 
                                     activity))
      pos_id = cur.lastrowid                               
      handle_provenance_insertion(cur, pos_dependancies, {'position':(pos_id,)})

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
        G_dependancies = sv.sv_dependancies_by_site[self.site_id[i]]
      except KeyError:
        print >>sys.stderr, "position: error: no steering vectors for site ID=%d" % self.site_id[i]
        sys.exit(1)

      V     = sig.ed[i, np.newaxis,:]
      V_dep = sig.id[i]

      # Bartlet's estimator. 
      left_half = np.dot(V, np.conj(np.transpose(G)))
      bearing_likelihood = (left_half * np.conj(left_half)).real

      bearing_likelihood_dependancies = [('Steering_Vectors', x) for x in G_dependancies]
      bearing_likelihood_dependancies.append(('est', V_dep))

      likelihood_dependancies = {}
      for j, theta in enumerate(sv.bearings[self.site_id[i]]):
        likelihoods[i, theta] = bearing_likelihood[0, j]
        likelihood_dependancies[i, theta] = bearing_likelihood_dependancies

    self.likelihoods = likelihoods
    if record_provenance_from_site_data:
      self.likelihood_dependancies = likelihood_dependancies
    else:
      self.likelihood_dependancies = [] 
  
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

    #: Bearings from receiver sites to each candidate point.
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
   
    pos = ll = pos_dependancies = pos_activity = None

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
      pos_dependancies = []
      for est_index in index_list:
        pos_dependancies.append(bl.id[est_index])
      pos_dependancies = {'est': tuple(pos_dependancies)}

      if verbose: print
   
    if pos: # TODO utm
      position.table.append((None, dep_id, t, pos.imag, pos.real, utm_zone_number,
                                             utm_zone_letter, ll, pos_activity, pos_dependancies))
    
    for (site_id, (theta, ll, activity)) in theta.iteritems():
      bearing.table.append((None, dep_id, site_id, t, theta, ll, activity))

  return (bearing, position)


