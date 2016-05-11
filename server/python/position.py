# position.py -- Bearing, position, and covariance estimation of signals.  
#
# High level calls, database interaction: 
#  - PositionEstimator
#  - WindowedPositionEstimator
#  - WindowedCovarianceEstimator
#  - InsertPositions
#  - InsertPositionsCovariances
#  - ReadPositions
#  - ReadBearings
#  - ReadAllBearings
#  - ReadCovariances
#  - ReadConfidenceRegions
#
# Objects defined here: 
#  - class Position
#  - class Bearing
#  - class Covariance
#  - class BootstrapCovariance (Covariance)
#  - class BootstrapCovariance2 (BootstrapCovariance)
#  - class Ellipse
#
# Copyright (C) 2015 Chris Patton, Todd Borrowman, Sean Riddle
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

from . import util, signal

import sys, time
import numpy as np
import matplotlib.pyplot as pp
from scipy.interpolate import InterpolatedUnivariateSpline as spline1d
import scipy, scipy.stats
import numdifftools as nd
import utm
import itertools, random

import Queue, threading

# Paramters for position estimation. 
POS_EST_M = 3
POS_EST_N = -1
POS_EST_DELTA = 5
POS_EST_S = 10

# Enable bootstrap covariance estimation (compute Position.sub_splines). 
# The subsplines are computed in `aggregate_window()`. Disabling this 
# will improve performance of position estimation when the covariance is 
# not needed. 
ENABLE_BOOTSTRAP = False
ENABLE_BOOTSTRAP2 = False
ENABLE_BOOTSTRAP3 = False

# Enable asymptotic covariance (compute Position.all_splines). 
ENABLE_ASYMPTOTIC = False

# Normalize bearing spectrum. 
NORMALIZE_SPECTRUM = False

# Paramters for bootstrap covariance estimation. 
BOOT_MAX_RESAMPLES = 200
BOOT_CONF_LEVELS = [0.68, 0.80, 0.90, 0.95, 0.997]



### class PositionEstimator. ##################################################

class PositionError (Exception): 
  value = 0; msg = ''
  def __str__(self): return '%s (%d)' % (self.msg, self.value)

class SingularError (PositionError):
  value = 2
  msg = 'covariance matrix is singular.'

class PosDefError (PositionError): 
  value = 3
  msg = 'covariance matrix is positive definite.'

class BootstrapError (PositionError): 
  value = 4
  msg = 'not enough samples to perform boostrap.'



### High level function calls. ################################################

def PositionEstimator(signal, sites, center, sv, method=signal.Signal.Bartlet,
                        s=POS_EST_S, m=POS_EST_M, n=POS_EST_N, delta=POS_EST_DELTA):
  ''' Estimate the source of a signal. 
  
    Inputs: 
      
      signal -- instance of `class signal.Signal`, signal data. 
      
      sites -- a map from siteIDs to site positions represented as UTM 
               easting/northing as a complex number. The imaginary component 
               is easting and the real part is northing.

      center -- initial guess of position, represented in UTM as a complex 
                number. 

      sv -- instance of `class signal.SteeringVectors`, calibration data. 

      method -- Specify method for computing bearing likelihood distribution.

      s, m, n, delta -- Parameters for position estimation algorithm. 

    Returns an instance of `class position.Position`. 
  ''' 
  if len(signal) > 0: 
    bearing_spectrum = {} # Compute bearing likelihood distributions.  
    for site_id in signal.get_site_ids().intersection(sv.get_site_ids()): 
      (bearing_spectrum[site_id], objective_function) = method(signal[site_id], sv)

    return Position(bearing_spectrum, signal, objective_function, sites, center,
                                signal.t_start, signal.t_end, s, m, n, delta)

  else:
    return None

#TAB Start Here
def WindowedPositionEstimator(signal, sites, center, sv, t_step, t_win, method=signal.Signal.Bartlet, 
                               s=POS_EST_S, m=POS_EST_M, n=POS_EST_N, delta=POS_EST_DELTA):
  ''' Estimate the source of a signal for windows of data over ``signal``. 
  
    Inputs: 
    
      signal, sites, center, sv
      
      t_step, t_win -- time step and window respectively. A position 
                       is computed for each timestep. 

      s, m, n, delta

    Returns a list of `class position.Position` instances. 
  ''' 
  pos = []

  if len(signal) > 0: 
    bearing_spectrum = {} # Compute bearing likelihood distributions. 
    objective_function = None 

    for site_id in signal.get_site_ids().intersection(sv.get_site_ids()): 
      (bearing_spectrum[site_id], objective_function) = method(signal[site_id], sv)
    
    for (t_start, t_end) in util.compute_time_windows(
                        signal.t_start, signal.t_end, t_step, t_win):
    
      pos.append(Position(bearing_spectrum, signal, objective_function, 
                  sites, center, t_start, t_end, s, m, n, delta))#TAB A
    
  return pos


#Multithreaded estimation
class EstimatorPool:

  class Worker (threading.Thread):

    def __init__(self, jobs):
      threading.Thread.__init__(self)
      self.jobs = jobs
      self.daemon = True
      self.start()

    def run(self):
      while True:
        func, args = self.jobs.get()
        try: func(*args)
        except Exception, e: print e
        self.jobs.task_done()

  def __init__(self, num_jobs, sites, center, sv,
               method=signal.Signal.Bartlet,
               s=POS_EST_S, m=POS_EST_M, n=POS_EST_N, delta=POS_EST_DELTA,
               max_resamples=BOOT_MAX_RESAMPLES):
    ''' Pool of worker threads for multihtreaded position and covariance estimation. 

      Input: jobs -- number of workers to spawn. 
    '''
    # Parameters
    self.sites = sites
    self.center = center
    self.sv = sv
    self.method = method
    self.pos_params = (s, m, n, delta)
    self.cov_params = (max_resamples,)
  
    # Worker threads
    self.jobs = Queue.Queue(num_jobs)
    for _ in range(num_jobs):
      self.Worker(self.jobs)
    
    # Output queue
    self.output = Queue.PriorityQueue()

  def enqueue(self, sig, t_step, t_win): 
    ''' Enqueue a chunk of sig data. 

      The bearing spectra for the sigs are computed, then a bunch of jobs
      are added to the queue. A job consists of a reference the bearing spectrum 
      data, the sig data, and a window of data to use for the position and 
      covariance estimation. 
    '''
    if len(sig) > 0: 
      bearing_spectrum = {} # Compute bearing likelihood distributions. 
      for site_id in sig.get_site_ids().intersection(self.sv.get_site_ids()): 
        (bearing_spectrum[site_id], objective_function) = self.method(sig[site_id], self.sv)
      
      for (t_start, t_end) in util.compute_time_windows(
                          sig.t_start, sig.t_end, t_step, t_win):
      
        self.jobs.put((self.job, (bearing_spectrum, sig, t_start, t_end, objective_function)))

  def dequeue(self):
    ''' Dequeue a position and covariance estimate in chronological order. 
    
      Returns a tuple (P, C) where P is an instance of `position.Position`
      and C is an instance of `position.BootstrapCovariance`. 
    ''' 
    return self.output.get()

  def empty(self):
    return self.output.empty()

  def job(self, bearing_spectrum, sig, t_start, t_end, objective_function):
    ''' Estimate position and covariance and put objects in output queue. ''' 
    P = Position(bearing_spectrum, sig, objective_function, 
                  self.sites, self.center, t_start, t_end, *self.pos_params)
    C = BootstrapCovariance(P, self.sites, *self.cov_params)
    self.output.put((P, C))

  def join(self):
    self.jobs.join()

   

def InsertPositions(db_con, dep_id, cal_id, zone, pos, cov=None):
  ''' Insert positions, bearings, and covariances into database. 
  
    Inputs:

      db_con -- MySQL database connector. 

      dep_id -- deploymentID of positions

      cal_id -- Cal_InfoID of steering vectors used to compute 
                beaaring spectra. 

      zone -- UTM zone for computation, represented as a tuple 
              (zone number, zone letter). 

      pos -- list of `class position.Position` instances

      cov -- list of `class position.BootstrapCovariance` instances 
             corresponding to the positions in `pos`. 
  
  ''' 
  max_id = 0
  for (P, C) in zip(pos, cov):
    # Insert bearings
    bearing_ids = []
    for (site_id, B) in P.bearings.iteritems():
      bearing_id = B.insert_db(db_con, cal_id, dep_id, site_id, P.t)
      bearing_ids.append(bearing_id)
    
    # Insert position
    pos_id = P.insert_db(db_con, dep_id, bearing_ids, zone)
    if pos_id and not (cov is None):
      max_id = max(pos_id, max_id)
      
      # Insert covariance
      cov_id = C.insert_db(db_con, pos_id)
  return max_id


def ReadBearings(db_con, dep_id, site_id, t_start, t_end):
  ''' Read bearings from the database for a particular site and transmitter.  

    Inputs:

      db_con, dep_id, db_con

      t_start, t_end -- Unix timestamps (in GMT) indicating the
                        time range of the query.

    Returns a list of `class position.Bearing` instances. 
  '''
  cur = db_con.cursor()
  cur.execute('''SELECT ID, siteID, timestamp, bearing, 
                        likelihood, activity, number_est_used 
                   FROM bearing
                  WHERE deploymentID = %s
                    AND siteID = %s
                    AND timestamp >= %s
                    AND timestamp <= %s
                  ORDER BY timestamp ASC ''', (dep_id, site_id, t_start, t_end))
  bearings = []
  for row in cur.fetchall():
    B = Bearing()
    B.bearing_id = row[0]
    B.t = row[2]
    B.bearing = row[3]
    B.likelihood = row[4]
    B.activity = row[5]
    B.num_est = row[6]
    bearings.append(B)
  return bearings


def ReadAllBearings(db_con, dep_id, t_start, t_end):
  ''' Read bearings from database for all available sites. 
    
    Returns a mapping from siteIDs to lists of `class position.Bearing` 
    instances. 
  '''
  cur = db_con.cursor()
  cur.execute('''SELECT ID, siteID, timestamp, bearing, 
                        likelihood, activity, number_est_used 
                   FROM bearing
                  WHERE deploymentID = %s
                    AND timestamp >= %s
                    AND timestamp <= %s
                  ORDER BY timestamp ASC''', (dep_id, t_start, t_end))
  bearings = {}
  for row in cur.fetchall():
    B = Bearing()
    B.bearing_id = row[0]
    B.t = row[2]
    B.bearing = row[3]
    B.likelihood = row[4]
    B.activity = row[5]
    B.num_est = row[6]
    site_id = int(row[1])
    if not bearings.get(site_id): 
      bearings[site_id] = [B]
    else: 
      bearings[site_id].append(B)
  return bearings


def ReadPositions(db_con, dep_id, t_start, t_end):
  ''' Read positions from database. 

    Returns a list of `class position.Position` instances.
  '''
  cur = db_con.cursor()
  cur.execute('''SELECT ID, timestamp, latitude, longitude, easting, northing, 
                        utm_zone_number, utm_zone_letter, likelihood, 
                        activity, number_est_used
                   FROM position
                  WHERE deploymentID = %s
                    AND timestamp >= %s
                    AND timestamp <= %s
                  ORDER BY timestamp ASC''', (dep_id, t_start, t_end))
  pos = []
  for row in cur.fetchall():
    P = Position()
    P.pos_id = row[0]
    P.t = row[1]
    P.latitude = row[2]
    P.longitude = row[3]
    P.p = np.complex(row[5], row[4]) 
    P.zone = (row[6], row[7])
    P.likelihood = row[8]
    P.activity = row[9]
    P.num_est = row[1]
    pos.append(P)
  return pos 



### class Position. ###########################################################

class Position:
  
  def __init__(self, *args):#TAB A
    ''' Representation of position estimtes. 
    
      The default constructor sets all attributes to `None`. If arguments are provided, 
      then the method `position.Position.calc()` is called, which estimates the 
      transmitter's location from signal data. 
    ''' 
    self.num_sites = None
    self.num_est = None
    self.p = None
    self.t = None
    self.likelihood = None
    self.activity = None
    self.bearings = None
    
    self.splines = None
    self.sub_splines = None
    self.all_splines = None
    self.objective_function = None
    
    self.pos_id = None
    self.zone = None
    self.latitude = None
    self.longitude = None
  
    if len(args) == 11: 
      self.calc(*args)#TAB B

  def calc(self, bearing_spectrum, signal, objective_function, sites, center, t_start, t_end, s, m, n, delta):#TAB B
    ''' Compute a position from signal data.

      In addition, compute the bearing data. If there is only data from one site, then 
      no estimate is produced (`p_hat = None`). 

      Inputs: 

        bearing_spectrum -- mapping from siteIDs to a two-dimensional arrays representing the
                            raw bearing spectra of the signals. The rows correspond to signals
                            and the columns to bearings. There are 360 columns corresponding 
                            to whole degree bearings. The cells are likelihoods of observing
                            the signal given that the bearing is the true bearing from the 
                            receiver to the transmitter. This is generated from either 
                            `class signal.Signal.MLE` or `class signal.Signal.Bartlet`. 
        
        signal -- an instance of `class signal.Signal` encapsulating the raw signal data. 
         
        objective_function -- objective function for bearing spectrum (either `np.argmin` or `np.argmax`). 

        sites -- mapping from siteIDs to receiver locations. 

        center -- initial guess for position estimation. 

        t_start, t_end -- slice of `signal` data to use for estimate. 

        s, m, n, delta -- paramters of position estimation algorithm. 
    ''' 
    # Aggregate site data. 
    (splines, sub_splines, all_splines, bearings, num_est) = aggregate_window(
                                  bearing_spectrum, signal, objective_function, t_start, t_end)#TAB C
   
    if len(splines) > 1: # Need at least two site bearings. 
      p_hat, likelihood = compute_position(sites, splines, center, objective_function, s, m, n, delta) #TAB G
    else: p_hat, likelihood = None, None
    
    # Return a position object. 
    num_sites = len(bearings)
    t = (t_end + t_start) / 2
    
    self.p = p_hat
    self.t = t
    
    if likelihood and num_sites > 0:
      if NORMALIZE_SPECTRUM:#TAB HUH?
        self.likelihood = likelihood / num_sites
      else: 
        self.likelihood = likelihood / num_est
    
    if num_sites > 0:
      self.activity = np.mean([ B.activity for B in bearings.values() ]) 
    
    self.bearings = bearings
    self.num_est = num_est
    self.num_sites = num_sites

    self.splines = splines         # siteID -> aggregated bearing likelihood spline
    self.sub_splines = sub_splines # siteID -> spline of sub samples for bootstrapping
    self.all_splines = all_splines # siteID -> spline for each pulse
    self.objective_function = objective_function                 # objective function used in pos. est.
 
  def insert_db(self, db_con, dep_id, bearing_ids, zone):
    ''' Insert position and bearings into the database. 
    
      Inputs: 
        
        db_con, dep_id, zone

        bearing_ids -- bearingIDs (serial identifiers in the database) of the bearings
                       corresponding to bearing data. These are used for provenance 
                       in the database. 
    ''' 
    if self.p is None: 
      return None
    number, letter = zone
    lat, lon = utm.to_latlon(self.p.imag, self.p.real, number, letter)
    cur = db_con.cursor()
    cur.execute('''INSERT INTO position
                     (deploymentID, timestamp, latitude, longitude, easting, northing, 
                      utm_zone_number, utm_zone_letter, likelihood, 
                      activity, number_est_used)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                     (dep_id, self.t, round(lat,6), round(lon,6),
                      self.p.imag, self.p.real, number, letter, 
                      self.likelihood, self.activity,
                      self.num_est))
    pos_id = cur.lastrowid
    handle_provenance_insertion(cur, {'bearing': tuple(bearing_ids)}, 
                                     {'position' : (pos_id,)})
    return pos_id

  def plot(self, fn, dep_id, sites, center, p_known=None, half_span=150, scale=10):
    ''' Plot search space of position estimate. 
    
      Note that this can only be called if `splines` is not `None`, that is, 
      the position was computed from signal data. 
    '''
    assert self.splines != None 

    if self.num_sites == 0:
      print 'yes'
      return 

    (positions, likelihoods) = compute_likelihood_grid(
                         sites, self.splines, center, scale, half_span)

    fig = pp.gcf()
    
    # Transform to plot's coordinate system.
    e = lambda(x) : ((x - center.imag) / scale) + half_span
    n = lambda(y) : ((y - center.real) / scale) + half_span 
    f = lambda(p) : [e(p.imag), n(p.real)]
    
    x_left =  center.imag - (half_span * scale)
    x_right = center.imag + (half_span * scale)
    
    # Search space
    P = pp.imshow(likelihoods.transpose(), 
        origin='lower',
        extent=(0, half_span * 2, 0, half_span * 2),
        cmap='YlGnBu',
        aspect='auto', interpolation='nearest')

    cbar = fig.colorbar(P, ticks=[np.min(likelihoods), np.max(likelihoods)])
    cbar.ax.set_yticklabels(['low', 'high'])# vertically oriented colorbar
    
    # Sites
    pp.scatter(
      [e(float(s.imag)) for s in sites.values()],
      [n(float(s.real)) for s in sites.values()],
       s=half_span / scale, facecolor='0.5', label='sites', zorder=10)
   
    # True position (if known).
    if p_known: 
      pp.scatter([e(p_known.imag)], [n(p_known.real)], 
              facecolor='0.0', label='position', zorder=11)

    # Pos. estimate with confidence ellipse
    if self.p is not None: 
      pp.scatter([e(self.p.imag)], [n(self.p.real)], 
            facecolor='1.0', label='pos. est', zorder=11)

    pp.clim()   # clamp the color limits
    #pp.legend()
    pp.axis([0, half_span * 2, 0, half_span * 2])
    
    t = time.localtime(self.t)
    pp.title('%04d-%02d-%02d %02d%02d:%02d depID=%d' % (
         t.tm_year, t.tm_mon, t.tm_mday,
         t.tm_hour, t.tm_min, t.tm_sec,
         dep_id))
    
    pp.savefig(fn)
    pp.clf()

def __lt__(self): 
  assert self.t is not None
  return self.t


### class Bearing. ############################################################

class Bearing:
  
  def __init__(self, *args): #TAB F
    ''' Representation of bearing estimates. 

      This class also encapsulates the "activity" of the transmitter, as 
      measured from the data received from the site. If arguments are provided, 
      then `position.Bearing.calc()` is called.  
    '''
    self.bearing_id = None
    self.t = None

    self.est_ids = None
    self.bearing = None
    self.likelihood = None
    self.activity = None
    self.num_est = None

    if len(args) == 5:
      self.calc(*args)

  def calc(self, edsp, bearing_spectrum, num_est, objective_function, est_ids):
    ''' Compute bearing from `bearing_spectrum` and activity from `edsp`.

      Inputs: 

        bearing_spectrum -- two dimensional array of signals versus 
                            bearing likelihoods. 

        edsp -- a list of real numbers indicating the signal power 
                of each signal. 

        num_est -- number of signals 

        objective_function -- objective function for bearing likelihood (either `np.argmin`
               or `np.argmax`).

        est_ids -- estIDs (serial identifiers in database) of the signals. 
    '''
    self.est_ids = est_ids
    self.num_est = num_est
    self.bearing = objective_function(bearing_spectrum)

    # Normalized likelihood. 
    self.likelihood = bearing_spectrum[self.bearing]
    if not NORMALIZE_SPECTRUM: #TAB HUH? See other NORMALIZE
      self.likelihood /= num_est
    
    # Activity.
    self.activity = (np.sum((edsp - np.mean(edsp))**2)**0.5)/np.sum(edsp)

  def insert_db(self, db_con, cal_id, dep_id, site_id, t):
    ''' Insert bearing into database. 
    
      Inputs: 
          
        t -- Unix timestamp in GMT. 
    ''' 
    cur = db_con.cursor()
    cur.execute('''INSERT INTO bearing 
                          (deploymentID, siteID, timestamp, 
                           bearing, likelihood, activity, number_est_used)
                  VALUES (%s, %s, %s, %s, %s, %s, %s)''', 
                 (dep_id, site_id, t, 
                  self.bearing, self.likelihood, self.activity, self.num_est))
    bearing_id = cur.lastrowid
    handle_provenance_insertion(cur, {'est' : tuple(self.est_ids), 
                                       'calibration_information' : (cal_id,)}, 
                                      {'bearing' : (bearing_id,)})
    return bearing_id




### Low level calls. ##########################################################
#TAB C
def aggregate_window(bearing_spectrum_per_site_dict, signal_per_site_dict, objective_function, t_start, t_end):
  ''' Aggregate site data, compute splines for pos. estimation. 
  
    Site data includes the most likely bearing to each site, 
    measurement of activity at each site, and a spline 
    interpolation of bearing distribution at each site. 
  '''

  num_est = 0
  splines = {}  
  bearings = {}
  sub_splines = {}

  if ENABLE_BOOTSTRAP3 or ENABLE_ASYMPTOTIC: 
    all_splines = {}
  else: all_splines = None

  if ENABLE_BOOTSTRAP or ENABLE_BOOTSTRAP2:
    sub_splines = {}
  else: sub_splines = None

  for (siteID, bearing_spectrum) in bearing_spectrum_per_site_dict.iteritems():
    mask = (t_start <= signal_per_site_dict[siteID].t) & (signal_per_site_dict[siteID].t < t_end)
    est_ids = signal_per_site_dict[siteID].est_ids[mask]
    edsp = signal_per_site_dict[siteID].edsp[mask]
    if edsp.shape[0] > 0:
      likelihoods = bearing_spectrum[mask]
      # Aggregated bearing spectrum spline per site.
      p = aggregate_spectrum(likelihoods)#TAB D
      splines[siteID] = compute_bearing_spline(p) #TAB E
      
      # Sub sample splines.
      if ENABLE_BOOTSTRAP or ENABLE_BOOTSTRAP2:
        sub_splines[siteID] = []
        if len(likelihoods) == 1: 
          sub_splines[siteID].append(compute_bearing_spline(likelihoods[0]))
        elif len(likelihoods) == 2:
          sub_splines[siteID].append(compute_bearing_spline(likelihoods[0]))
          sub_splines[siteID].append(compute_bearing_spline(likelihoods[1]))
        else:
          #HUH? TAB 2015-07-27
          #For N records build all N-1 sized spectra? 
          for index in itertools.combinations(range(len(likelihoods)), len(likelihoods)-1):
            p = aggregate_spectrum(likelihoods[np.array(index)])
            sub_splines[siteID].append(compute_bearing_spline(p)) 
      
      # All splines.
      if ENABLE_BOOTSTRAP3 or ENABLE_ASYMPTOTIC: 
        all_splines[siteID] = []
        for i in range(len(likelihoods)):
          all_splines[siteID].append(compute_bearing_spline(likelihoods[i]))

      # Aggregated data per site. #TAB F
      bearings[siteID] = Bearing(edsp, p, len(edsp), objective_function, est_ids)

      num_est += edsp.shape[0]
  
  return (splines, sub_splines, all_splines, bearings, num_est)

#TAB D
def aggregate_spectrum(p):
  ''' Sum a set of bearing likelihoods. '''
  if NORMALIZE_SPECTRUM:
    return np.sum(p, 0) / p.shape[0]#TAB HUH? SEE position.calc
  else: 
    return np.sum(p, 0)

#TAB E
def compute_bearing_spline(l): 
  ''' Interpolate a spline on a bearing likelihood distribuiton. 
    
    Input an aggregated bearing distribution, e.g. the output of 
    `aggregate_spectrum(p)` where p is the output of `_per_site_data.mle()` 
    or `_per_site_data.bartlet()`.
  '''
  bearing_domain = np.arange(-360,360)       
  likelihood_range = np.hstack((l, l))
  return spline1d(bearing_domain, likelihood_range)


def compute_likelihood_grid(sites, splines, center, scale, half_span):
  ''' Compute a grid of candidate points and their likelihoods. '''
  # Generate a grid of positions with center at the center. 
  positions = np.zeros((half_span*2+1, half_span*2+1),np.complex)
  for e in range(-half_span,half_span+1):
    for n in range(-half_span,half_span+1):
      positions[e + half_span, n + half_span] = center + np.complex(n * scale, e * scale)
  # Compute the likelihood of each position as the sum of the likelihoods 
  # of bearing to each site. 
  likelihoods = np.zeros(positions.shape, dtype=float)
  for siteID in splines.keys():
    bearing_to_positions = np.angle(positions - sites[siteID]) * 180 / np.pi
    try:
      spline_iter = iter(splines[siteID])
    except TypeError:
      likelihoods += splines[siteID](bearing_to_positions.flat).reshape(bearing_to_positions.shape)
    else:
      for s in spline_iter:
        likelihoods += s(bearing_to_positions.flat).reshape(bearing_to_positions.shape)
  return (positions, likelihoods)

#not called TAB 2015-07-27
def compute_likelihood(sites, splines, p):
  ''' Compute the likelihood of position `p`. ''' 
  likelihood = 0
  for siteID in splines.keys():
    bearing = np.angle(p - sites[siteID]) * 180 / np.pi
    likelihood += splines[siteID](bearing)
  return likelihood

#TAB G
def compute_position(sites, splines, center, objective_function, s, m, n, delta):
  ''' Maximize (resp. minimize) over position space. 

    Grid search algorithm for position estimation (optimizing over the 
    search space). If the most likely position is at the edge of the grid,
    then rerun at the same scale with the most likely position as the 
    new center. This is done up to 3 times.  

    Inputs: 
      
      sites, center - UTM positions of receiver sites and center, the initial 
                      guess of the transmitter's position. 
      
      splines -- a set of splines corresponding to the bearing likelihood
                 distributions for each site.

      objective_function -- np.argmin or np.argmax

      s -- Half span of search grid. (The dimensions of the grid are 2*s+1 
           by 2*s+1.) 

      m -- Initial scale. The grid points are initially spaced delta**m 
           meters apart. 

      n -- Final scale. The grid points are spaced delta**n meters apart 
           in the final iteration. 

      delta -- Scaling factor.  
    
      Returns UTM position estimate as a complex number and the likelihood
      of the position
  '''
  assert m >= n
  p_hat = center
  span = s * 2 + 1
  for i in reversed(range(n, m+1)):
    scale = delta ** i
    a = b = ct = 0
    while ct < 3 and (a == 0 or a == span-1 or b == 0 or b == span-1): 
      (positions, likelihoods) = compute_likelihood_grid(
                             sites, splines, p_hat, scale, s)
      index = objective_function(likelihoods)
      p_hat = positions.flat[index]
      likelihood = likelihoods.flat[index]
      a = index / span; b = index % span
      ct += 1
  return p_hat, likelihood




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
