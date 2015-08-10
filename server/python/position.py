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
      (bearing_spectrum[site_id], obj) = method(signal[site_id], sv)

    return Position(bearing_spectrum, signal, obj, sites, center,
                                signal.t_start, signal.t_end, s, m, n, delta)

  else:
    return None


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
    obj = None 

    for site_id in signal.get_site_ids().intersection(sv.get_site_ids()): 
      (bearing_spectrum[site_id], obj) = method(signal[site_id], sv)
    
    for (t_start, t_end) in util.compute_time_windows(
                        signal.t_start, signal.t_end, t_step, t_win):
    
      pos.append(Position(bearing_spectrum, signal, obj, 
                  sites, center, t_start, t_end, s, m, n, delta))
    
  return pos


def WindowedCovarianceEstimator(pos, sites, max_resamples=BOOT_MAX_RESAMPLES):  
  ''' Compute covariance of each position in `pos`. 

    Inputs:
      
      pos -- list of `class position.Position` instances. 

      sites -- mapping of siteIDs to receiver locations. 

      max_resamples -- a paramter of the bootstrap covariance estimate, the 
                       number of times to resample from the data. 

    Returns a list of `position.BootstrapCovariance` instances. 
  ''' 
  cov = []
  for P in pos:
    if ENABLE_BOOTSTRAP:
      C = BootstrapCovariance(P, sites, max_resamples)
      cov.append(C)
    if ENABLE_BOOTSTRAP2:
      C = BootstrapCovariance2(P, sites, max_resamples)
      cov.append(C)
    if ENABLE_BOOTSTRAP3:
      C = BootstrapCovariance3(P, sites, max_resamples)
      cov.append(C)
  return cov


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
        (bearing_spectrum[site_id], obj) = self.method(sig[site_id], self.sv)
      
      for (t_start, t_end) in util.compute_time_windows(
                          sig.t_start, sig.t_end, t_step, t_win):
      
        self.jobs.put((self.job, (bearing_spectrum, sig, t_start, t_end, obj)))

  def dequeue(self):
    ''' Dequeue a position and covariance estimate in chronological order. 
    
      Returns a tuple (P, C) where P is an instance of `position.Position`
      and C is an instance of `position.BootstrapCovariance`. 
    ''' 
    return self.output.get()

  def empty(self):
    return self.output.empty()

  def job(self, bearing_spectrum, sig, t_start, t_end, obj):
    ''' Estimate position and covariance and put objects in output queue. ''' 
    P = Position(bearing_spectrum, sig, obj, 
                  self.sites, self.center, t_start, t_end, *self.pos_params)
    C = BootstrapCovariance(P, self.sites, *self.cov_params)
    self.output.put((P, C))

  def join(self):
    self.jobs.join()

   


def InsertPositions(db_con, dep_id, cal_id, zone, pos):
  ''' Insert positions and bearings into database. 

    Inputs: 
      
      db_con -- MySQL database connector. 

      dep_id -- deploymentID of positions

      cal_id -- Cal_InfoID of steering vectors used to compute 
                beaaring spectra. 

      zone -- UTM zone for computation, represented as a tuple 
              (zone number, zone letter). 
  
      pos -- list of `class position.Position` estimates. 
  ''' 
  max_id = 0
  for P in pos:
    # Insert bearings
    bearing_ids = []
    for (site_id, B) in P.bearings.iteritems():
      bearing_id = B.insert_db(db_con, cal_id, dep_id, site_id, P.t)
      bearing_ids.append(bearing_id)
    
    # Insert position
    pos_id = P.insert_db(db_con, dep_id, bearing_ids, zone)
    if pos_id:
      max_id = max(pos_id, max_id)
  return max_id


def InsertPositionsCovariances(db_con, dep_id, cal_id, zone, pos, cov):
  ''' Insert positions, bearings, and covariances into database. 
  
    Inputs:

      db_con, dep_id, cal_id, zone

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
    if pos_id:
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


def ReadCovariances(db_con, dep_id, t_start, t_end):
  ''' Read covariances from the database. 
  
    Return a list of `class position.Covariance` instances. 
  ''' 
  cur = db_con.cursor()
  cur.execute('''SELECT status, method, 
                        cov11, cov12, cov21, cov22,
                        w99, w95, w90, w80, w68,
                        easting, northing
                   FROM covariance
                   JOIN position as p ON p.ID = positionID
                  WHERE deploymentID = %s
                    AND timestamp >= %s
                    AND timestamp <= %s
                  ORDER BY timestamp ASC''', (dep_id, t_start, t_end))
  cov = []
  for row in cur.fetchall():
    if row[1] == 'boot':
      C = BootstrapCovariance()
    elif row[2] == 'boot2': 
      C = BootstrapCovariance2()
    if row[0] == 'ok':
      C.C = np.array([[row[2], row[3]], 
                      [row[4], row[5]]])
      C.W[0.997] = row[6]
      C.W[0.95] = row[7]
      C.W[0.90] = row[8]
      C.W[0.80] = row[9]
      C.W[0.68] = row[10]
    C.p_hat = np.complex(row[12], row[11])
    C.status = row[0]
    cov.append(C)
  return cov
  

def ReadConfidenceRegions(db_con, dep_id, t_start, t_end, conf_level): 
  ''' Read confidence regions from the database. 
    
    Input: 
      
      conf_level -- a number in [0 .. 1] (see `position.BOOT_CONF_LEVELS` for 
                    valid choices) giving the desired confidence level. 
                    
    Returns a list of `class position.Ellipse` instances. If the covariance 
    is singular or not positive definite, `None` is given instead.   
  '''
  cur = db_con.cursor()
  cur.execute('''SELECT status, method, 
                        alpha, lambda1, lambda2, w{0},
                        easting, northing
                   FROM covariance
                   JOIN position as p ON p.ID = positionID
                  WHERE deploymentID = %s
                    AND timestamp >= %s
                    AND timestamp <= %s'''.format(int(100*conf_level)), 
                      (dep_id, t_start, t_end))
  conf = []
  for row in cur.fetchall():
    if row[0] == 'ok': 
      alpha = row[2]
      lambda1 = row[3]
      lambda2 = row[4] 
      Qt = row[5]
      p_hat = np.complex(row[7], row[6])
      axes = np.array([np.sqrt(Qt * lambda1), 
                       np.sqrt(Qt * lambda2)])
      E = Ellipse(p_hat, alpha, axes)
      conf.append(E)
    else: conf.append(None)
  return conf


### class Position. ###########################################################

class Position:
  
  def __init__(self, *args):
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
    self.obj = None
    
    self.pos_id = None
    self.zone = None
    self.latitude = None
    self.longitude = None
  
    if len(args) == 11: 
      self.calc(*args)

  def calc(self, bearing_spectrum, signal, obj, sites, center, t_start, t_end, s, m, n, delta):
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
         
        obj -- objective function for bearing spectrum (either `np.argmin` or `np.argmax`). 

        sites -- mapping from siteIDs to receiver locations. 

        center -- initial guess for position estimation. 

        t_start, t_end -- slice of `signal` data to use for estimate. 

        s, m, n, delta -- paramters of position estimation algorithm. 
    ''' 
    # Aggregate site data. 
    (splines, sub_splines, all_splines, bearings, num_est) = aggregate_window(
                                  bearing_spectrum, signal, obj, t_start, t_end)
   
    if len(splines) > 1: # Need at least two site bearings. 
      p_hat, likelihood = compute_position(sites, splines, center, obj, s, m, n, delta)
    else: p_hat, likelihood = None, None
    
    # Return a position object. 
    num_sites = len(bearings)
    t = (t_end + t_start) / 2
    
    self.p = p_hat
    self.t = t
    
    if likelihood and num_sites > 0:
      if NORMALIZE_SPECTRUM:
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
    self.obj = obj                 # objective function used in pos. est.
 
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
  
  def __init__(self, *args): 
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

  def calc(self, edsp, bearing_spectrum, num_est, obj, est_ids):
    ''' Compute bearing from `bearing_spectrum` and activity from `edsp`.

      Inputs: 

        bearing_spectrum -- two dimensional array of signals versus 
                            bearing likelihoods. 

        edsp -- a list of real numbers indicating the signal power 
                of each signal. 

        num_est -- number of signals 

        obj -- objective function for bearing likelihood (either `np.argmin`
               or `np.argmax`).

        est_ids -- estIDs (serial identifiers in database) of the signals. 
    '''
    self.est_ids = est_ids
    self.num_est = num_est
    self.bearing = obj(bearing_spectrum)

    # Normalized likelihood. 
    self.likelihood = bearing_spectrum[self.bearing]
    if not NORMALIZE_SPECTRUM: 
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



### class Ellipse. ###################################################

class Ellipse:

  def __init__(self, p_hat, angle, axes, half_span=0, scale=1):
    ''' Representation of an ellipse. 
    
      A confidence region for normally distributed data. 
      
      Input: 
      
        p_hat -- UTM position estimate represented as a complex number. This is the
                 center of the ellipse. 

        angle -- orientation of the ellipse, represented as the angle (in radians, 
                 where 0 indicates east) between the x-axis and the major axis.

        axes -- vector of length 2: `axes[0]` is half the length of the major axis 
                and `axes[1]` is half the length of the minor axis. 

        half_span, scale -- if the ellipse is to be scaled in a weird way.
      ''' 
    self.p_hat = p_hat
    self.angle = angle
    self.axes = axes
    self.half_span = half_span
    self.scale = scale
    self.x = np.array([half_span, half_span])

  def area(self):
    ''' Return the area of the ellipse. ''' 
    return np.pi * self.axes[0] * self.axes[1] 

  def eccentricity(self):
    ''' Return the eccentricity of the ellipse. ''' 
    return np.sqrt(1 - ((self.axes[1]/2)**2) / ((self.axes[0]/2)**2))

  def cartesian(self): 
    ''' Convert the ellipse to (x,y) coordinates. ''' 
    theta = np.linspace(0,2*np.pi, 360)
    X = self.x[0] + self.axes[0]*np.cos(theta)*np.cos(self.angle) - \
                    self.axes[1]*np.sin(theta)*np.sin(self.angle)
    Y = self.x[1] + self.axes[0]*np.cos(theta)*np.sin(self.angle) + \
                    self.axes[1]*np.sin(theta)*np.cos(self.angle)
    return (X, Y)

  def __contains__(self, p):
    ''' Return `True` if the ellipse contains the point. 

      Input: p -- UTM position represented as a complex number.
    '''
    x = transform_coord(p, self.p_hat, self.half_span, self.scale)
    R = np.array([[ np.cos(self.angle), np.sin(self.angle) ],
                  [-np.sin(self.angle), np.cos(self.angle) ]])   
    y = np.dot(R, x - self.x)
    return ((y[0] / self.axes[0])**2 + (y[1] / self.axes[1])**2) <= 1 

  def display(self, p_known=None):
    ''' Ugly console renderring of confidence region. ''' 
    X, Y = self.cartesian()
    X = map(lambda x: int(x), X)
    Y = map(lambda y: int(y), Y)
    self.contour = set(zip(list(X), list(Y)))
    if p_known is not None:
      x_known = transform_coord(p_known, self.p_hat, self.half_span, self.scale)
    else:
      x_known = None
    dim = 20
    for i in range(-dim, dim+1):
      for j in range(-dim, dim+1):
        x = self.x + np.array([i,j])
        if x_known is not None and x[0] == x_known[0] and x[1] == x_known[1]: print 'C', 
        elif x[0] == self.x[0] and x[1] == self.x[1]: print 'P', 
        elif tuple(x) in self.contour: print '.',
        else: print ' ',
      print 

  def plot(self, fn, p_known=None):
    ''' A pretty plot of confidence region. ''' 
    pp.rc('text', usetex=True)
    pp.rc('font', family='serif')
    
    fig = pp.gcf()
    x_hat = self.x
 
    ax = fig.add_subplot(111)
    ax.axis('equal')

    #(x_fit, y_fit) = fit_contour(x, y, N=10000)
    X = np.vstack(self.cartesian())
    pp.plot(X[0,:], X[1,:], color='k')

    # Major, minor axes
    D = (lambda d: np.sqrt(
          (d[0] - x_hat[0])**2 + (d[1] - x_hat[1])**2))(X)
    x_major = X[:,np.argmax(D)]
    x_minor = X[:,np.argmin(D)]
    pp.plot([x_hat[0], x_major[0]], [x_hat[1], x_major[1]], '-', label='major $\sqrt{\lambda_1 Q_\gamma}$')
    pp.plot([x_hat[0], x_minor[0]], [x_hat[1], x_minor[1]], '-', label='minor $\sqrt{\lambda_2 Q_\gamma}$')

    #x_hat
    pp.plot(x_hat[0], x_hat[1], color='k', marker='o')
    pp.text(x_hat[0]-1.25, x_hat[1]-0.5, '$\hat{\mathbf{x}}$', fontsize=18)
      
    # x_known
    offset = 0.5
    if p_known:
      x_known = transform_coord(p_known, self.p_hat, self.half_span, self.scale)
      pp.plot([x_known[0]], [x_known[1]],  
              marker='o', color='k', fillstyle='none')
      pp.text(x_known[0]+offset, x_known[1]-offset, '$\mathbf{x}^*$', fontsize=18)
    
    ax.set_xlabel('easting (m)')
    ax.set_ylabel('northing (m)')
    pp.legend(title="Axis length")
    pp.savefig(fn, dpi=150, bbox_inches='tight')
    pp.clf()



### Covariance. ###############################################################

class likelihood_function:
  def __init__(self, sites, splines):
    self.sites = sites
    self.splines = splines

  def evaluate(self, x):
    ''' Compute the likelihood of position `x`. ''' 
    likelihood = 0
    for siteID in self.splines.keys():
      bearing = np.angle(x - self.sites[siteID]) * 180 / np.pi
      likelihood += self.splines[siteID](bearing)
    return likelihood



class Covariance:
  
  def __init__(self, *args, **kwargs):
    ''' Asymptotic covariance of position estimate. 

      If arguments are provided, then `position.Covariance.calc()` is called. 
    '''
    self.method = 'asym'
    self.p_hat = None
    self.half_span = None
    self.scale = None
    self.m = None
    self.C = None

    if len(args) >= 2: 
      self.calc(*args, **kwargs)
  
  def calc(self, pos, sites, p_known=None, half_span=75, scale=0.5):
    ''' Confidence region from asymptotic covariance. 
    
      Note that this expression only works if the `NORMALIZE_SPECTRUM` flag at the
      top of this program is set to `True`. 
    ''' 
    assert NORMALIZE_SPECTRUM
    assert ENABLE_ASYMPTOTIC
  
    self.p_hat = pos.p
    self.half_span = half_span
    self.scale = scale
    n = sum(map(lambda l : len(l), pos.sub_splines.values())) 
    self.m = n / pos.num_sites
  
    if p_known:
      p = p_known
    else: 
      p = pos.p
    x = np.array([half_span, half_span])
   
    likelihood = likelihood_function(sites, pos.splines)

    # Hessian
    #(positions, likelihoods) = compute_likelihood_grid(
    #                         sites, pos.splines, p, scale, half_span)
    #J = lambda (x) : likelihoods[x[0], x[1]]
    H = nd.Hessian(likelihood.evaluate)(p)
    A = np.linalg.inv(H)

    # Gradient TODO TAB
    B = np.zeros((2,2), dtype=np.float64)
    for i in range(self.m):
      splines = { id : p[i] for (id, p) in pos.all_splines.iteritems() }
      likelihood = likelihood_function(sites, splines)
      #(positions, likelihoods) = compute_likelihood_grid(
      #                         sites, splines, p, scale, half_span)
      #J = lambda (x) : likelihoods[x[0], x[1]]
      b = np.array([nd.Gradient(likelihood.evaluate)(x)]).T
      B += np.dot(b, b.T)
    B = B / self.m
    
    self.C = np.dot(A, np.dot(B, A))

  def __getitem__(self, index):
    ''' Return an element of the covariance matrix. ''' 
    return self.C[index]

  def conf(self, level): 
    ''' Emit confidence interval at the (1-conf_level) significance level. ''' 
    Qt = scipy.stats.chi2.ppf(level, 2) 
    (angle, axes) = compute_conf(self.C, 2 * Qt / self.m, 1) 
    return Ellipse(self.p_hat, angle, axes, 0, 1)


class BootstrapCovariance (Covariance):

  def __init__(self, *args, **kwargs):
    ''' Bootstrap method for estimating covariance of a position estimate. 

      If arguments are provided, then `position.BootstrapCovariance.calc()` is 
      called.
    '''
    self.method = 'boot'
    self.C = None
    self.W = {}
    self.p_hat = None
    if len(args) >= 2: 
      self.calc(*args, **kwargs)
 

  def calc(self, pos, sites, max_resamples=BOOT_MAX_RESAMPLES):
    '''  Bootstrap estimation of covariance. 

      Generate at most `max_resamples` position estimates by resampling the signals used
      in computing `pos`.

      Inputs:
          
        pos -- instance of `class position.Position`. 

        sites -- mapping of siteIDs to positions of receivers. 

        max_resamples -- number of times to resample the data.
    '''
    assert ENABLE_BOOTSTRAP
    self.p_hat = pos.p

    # Generate sub samples.
    P = np.array(bootstrap_resample_sites(pos, sites, 
                                  max_resamples, pos.obj, pos.splines.keys()))
    if len(P) > 0:  
      A = np.array(P[len(P)/2:])
      B = np.array(P[:len(P)/2])
     
      # Estimate covariance. 
      self.C = np.cov(np.imag(A), np.real(A))
      n = sum(map(lambda l : len(l), pos.sub_splines.values())) 
      self.m = float(n) / pos.num_sites
      
      # Mahalanobis distance of remaining estimates. 
      try: 
        W = []
        D = np.linalg.inv(self.C)
        p_bar = np.mean(B)
        x_bar = np.array([p_bar.imag, p_bar.real])
        x_hat = np.array([pos.p.imag, pos.p.real])
        for x in map(lambda p: np.array([p.imag, p.real]), iter(B)): 
          y = x - x_bar
          w = np.dot(np.transpose(y), np.dot(self.m * D, y)) 
          W.append(w)
       
        # Store just a few distances. 
        W = np.array(sorted(W))
        self.W = {}
        for level in BOOT_CONF_LEVELS:
          self.W[level] = W[int(len(W) * level)] * 2
        self.status = 'ok'
      
      except np.linalg.linalg.LinAlgError: # Singular 
        self.status = 'singular'

    else: # not enough samples
      self.status = 'undefined'

  def insert_db(self, db_con, pos_id): 
    ''' Insert covariance into the database. 
    
      Input: 

        pos_id -- positionID, serial identifier of position estimate in 
                  the database. 
    '''
    if self.status == 'ok':
      
      cov11, cov12, cov21, cov22 = self.C[0,0], self.C[0,1], self.C[1,0], self.C[1,1]
      w99, w95, w90, w80, w68 = (
             self.W[0.997], self.W[0.95], self.W[0.90], self.W[0.80], self.W[0.68])
    
      w, v = np.linalg.eig(self.C)
      if w[0] > 0 and w[1] > 0: # Positive definite. 

        i = np.argmax(w) # Major w[i], v[:,i]
        j = np.argmin(w) # Minor w[i], v[:,j]

        alpha = np.arctan2(v[:,i][1], v[:,i][0]) 
        lambda1 = w[i]
        lambda2 = w[j]
        self.status = 'ok'

      else: 
        alpha = lambda1 = lambda2 = None
        self.status = 'nonposdef'

    else: 
      cov11, cov12, cov21, cov22 = None, None, None, None
      w99, w95, w90, w80, w68 = None, None, None, None, None
      alpha = lambda1 = lambda2 = None
  
    cur = db_con.cursor()
    cur.execute('''INSERT INTO covariance
                   (positionID, status, method, 
                    cov11, cov12, cov21, cov22,
                    lambda1, lambda2, alpha, 
                    w99, w95, w90, w80, w68)
                 VALUES (%s, %s, %s, 
                         %s, %s, %s, %s, 
                         %s, %s, %s, 
                         %s, %s, %s, %s, %s)''', 
            (pos_id, self.status, self.method,
             cov11, cov12, cov21, cov22,
             lambda1, lambda2, alpha, 
             w99, w95, w90, w80, w68))
    return cur.lastrowid
      
  def conf(self, level): 
    ''' Emit confidence interval at the (1-conf_level) significance level. ''' 
    if self.status == 'ok':
      Qt = self.W[level] 
      (angle, axes) = compute_conf(self.C, Qt, 1) 
      return Ellipse(self.p_hat, angle, axes, 0, 1)
    elif self.status == 'singular':
      raise SingularError
    elif self.status == 'undefined':
      raise BootstrapError


class BootstrapCovariance2 (BootstrapCovariance):

  def __init__(self, *args, **kwargs):
    ''' Bootstrap method originally proposed by the stats group.

      Resample by using pairs of sites to compute estimates. 
    '''
    self.method = 'boot2'
    self.C = None
    self.W = {}
    self.p_hat = None
    if len(args) >= 2: 
      self.calc(*args, **kwargs)

  def calc(self, pos, sites, max_resamples=BOOT_MAX_RESAMPLES):
    assert ENABLE_BOOTSTRAP2
    self.p_hat = pos.p

    # Generate sub samples.
    P = np.array(bootstrap_resample(pos, sites, max_resamples, pos.obj))
    
    if len(P) > 0: 
      A = np.array(P[len(P)/2:])
      B = np.array(P[:len(P)/2])
      
      # Estimate covariance. 
      self.C = np.cov(np.imag(A), np.real(A)) 
      n = sum(map(lambda l : len(l), pos.sub_splines.values())) 
      self.m = float(n) / pos.num_sites
      
      # Mahalanobis distance of remaining estimates. 
      try:
        W = []
        D = np.linalg.inv(self.C)
        p_bar = np.mean(B)
        x_bar = np.array([p_bar.imag, p_bar.real])
        x_hat = np.array([pos.p.imag, pos.p.real])
        for x in map(lambda p: np.array([p.imag, p.real]), iter(B)): 
          y = x - x_bar
          w = np.dot(np.transpose(y), np.dot(D, y)) 
          W.append(w)
       
        # Store just a few distances. 
        W = np.array(sorted(W))
        self.W = {}
        for level in BOOT_CONF_LEVELS:
          self.W[level] = W[int(len(W) * level)]
        self.status = 'ok'
        
      except np.linalg.linalg.LinAlgError: # Singular 
        self.status = "singular"
    
    else: # not enough samples
      self.status = 'undefined'

class BootstrapCovariance3 (BootstrapCovariance):

  def __init__(self, *args, **kwargs):
    ''' Bootstrap method from Todd.

      Resample with replacement such that resample has same size as original. 
    '''
    self.method = 'boot3'
    self.C = None
    self.W = {}
    self.p_hat = None
    if len(args) >= 2: 
      self.calc(*args, **kwargs)

  def calc(self, pos, sites, max_resamples=BOOT_MAX_RESAMPLES):
    assert ENABLE_BOOTSTRAP3
    self.p_hat = pos.p

    # Generate sub samples.
    resampled_positions = np.array(bootstrap_case_resample(pos, sites, max_resamples, pos.obj))
    num_resampled_positions = len(resampled_positions)
    if num_resampled_positions > 1:
      if num_resampled_positions > 100:
        A = np.array(resampled_positions[num_resampled_positions/2:])
        B = np.array(resampled_positions[:num_resampled_positions/2])
      else:
        A = np.array(resampled_positions)
        B = np.array(resampled_positions)
      
      # Estimate covariance. 
      self.C = np.cov(np.imag(A), np.real(A)) 
      #n = sum(map(lambda l : len(l), pos.sub_splines.values())) 
      #self.m = float(n) / pos.num_sites
      
      # Mahalanobis distance of remaining estimates. 
      distances = []
      try:
        inv_C = np.linalg.inv(self.C)
      except np.linalg.linalg.LinAlgError: # Singular 
        self.status = "singular"
      else:
        p_bar = np.mean(B)
        x_bar = np.array([p_bar.imag, p_bar.real])
        for x in map(lambda p: np.array([p.imag, p.real]), iter(B)): 
          y = x - x_bar
          w = np.dot(np.transpose(y), np.dot(inv_C, y)) 
          distances.append(w)
       
        # Store just a few distances. 
        sorted_distances = np.array(sorted(distances))
        self.W = {}
        for level in BOOT_CONF_LEVELS:
          self.W[level] = sorted_distances[int(len(sorted_distances) * level)]
        self.status = 'ok'
        
          
    else: # not enough samples
      self.status = 'undefined'


### Low level calls. ##########################################################

def aggregate_window(bearing_spectrum_per_site_dict, signal_per_site_dict, obj, t_start, t_end):
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
      p = aggregate_spectrum(likelihoods)
      splines[siteID] = compute_bearing_spline(p) 
      
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

      # Aggregated data per site. 
      bearings[siteID] = Bearing(edsp, p, len(edsp), obj, est_ids)

      num_est += edsp.shape[0]
  
  return (splines, sub_splines, all_splines, bearings, num_est)


def aggregate_spectrum(p):
  ''' Sum a set of bearing likelihoods. '''
  if NORMALIZE_SPECTRUM:
    return np.sum(p, 0) / p.shape[0]
  else: 
    return np.sum(p, 0)


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


def compute_position(sites, splines, center, obj, s, m, n, delta):
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

      obj -- np.argmin or np.argmax

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
      index = obj(likelihoods)
      p_hat = positions.flat[index]
      likelihood = likelihoods.flat[index]
      a = index / span; b = index % span
      ct += 1
  return p_hat, likelihood


def bootstrap_resample(pos, sites, max_resamples, obj):
  ''' Generate positionn estimates by sub sampling signal data. 

    Construct an objective function from a subset of the pulses (one pulse per site)
    and optimize over the search space. Repeat this at most `max_resamples / samples` 
    for each pair of sites where `samples` is the number of such pairs. 
  '''
  resamples = max(1, max_resamples / (pos.num_sites * (pos.num_sites - 1) / 2))
  P = []
  for site_ids in itertools.combinations(pos.splines.keys(), 2):
    P += bootstrap_resample_sites(pos, sites, resamples, obj, site_ids)
  random.shuffle(P)
  return P

def bootstrap_resample_sites(pos, sites, resamples, obj, site_ids):
  ''' Resample from a specific set of sites. ''' 
  N = reduce(int.__mul__, [1] + map(lambda S : len(S), pos.sub_splines.values()))
  if N < 2 or pos.p is None: # Number of pulse combinations
    return []

#  a = 1 if obj == np.argmin else -1
#  x0 = np.array([pos.p.imag, pos.p.real])
  P = []
  for i in range(resamples):
    splines = {}
    for id in site_ids:
      j = random.randint(0, len(pos.sub_splines[id])-1)
      splines[id] = pos.sub_splines[id][j]
#    f = lambda(x) : a * compute_likelihood(sites, splines, np.complex(x[1], x[0]))    
#    res = scipy.optimize.minimize(f, x0)
#    p = np.complex(res.x[1], res.x[0])
    (p, _) = compute_position(sites, splines, pos.p, obj,
              s=POS_EST_S, m=POS_EST_M-1, n=POS_EST_N, delta=POS_EST_DELTA) 
    P.append(p)
  return P

def bootstrap_case_resample(pos, sites, max_resamples, obj):
  ''' Bootstrap case resampling:
        https://en.wikipedia.org/wiki/Bootstrapping_(statistics)#Case_resampling '''


  #N = reduce(int.__mul__, [1] + map(lambda S : len(S), pos.all_splines.values()))
  if pos.p is None or pos.num_sites < 2: # Number of pulse combinations
    return []

  bootstrap_resampled_positions = []
  site_list = pos.all_splines.keys()  
  number_of_ests_dict = {}

  #number of exhaustive combinations
  N=1
  for siteid in site_list:
    number_of_ests_dict[siteid] = len(pos.all_splines[siteid])
    N *= np.math.factorial(2*number_of_ests_dict[siteid]-1)/np.math.factorial(number_of_ests_dict[siteid])/np.math.factorial(number_of_ests_dict[siteid]-1)



  if (N < max_resamples): #exhaustive search
    #combinator generator
    combinator_iter_list = []
    for siteid in site_list:
      combinator_iter_list.append(
          itertools.combinations_with_replacement(
            [ (siteid, j) for j in range(number_of_ests_dict[siteid]) ], number_of_ests_dict[siteid]
              )
                )
    combinator_generator = itertools.product(*combinator_iter_list)

    for site_spline_tuple_list in combinator_generator:
      spline_dict = {}
      for siteid in site_list:
        spline_dict[siteid] = []
      for site_spline_tuples in site_spline_tuple_list:
        for site, est_index in site_spline_tuples:
          spline_dict[site].append(pos.all_splines[site][est_index])
      (p, _) = compute_position(sites, spline_dict, pos.p, obj,
              s=POS_EST_S, m=POS_EST_M-1, n=POS_EST_N, delta=POS_EST_DELTA)
      bootstrap_resampled_positions.append(p)

    
  else: #monte carlo
    #combo_pool = tuple(combinator_generator)
    number_of_combos = N#len(combo_pool)
    
    uniqueness_dict = {}
    for j in range(max_resamples):
      spline_dict = {}
      for site in site_list:
        spline_dict[site] = []

      unique = False
      while not unique:
        #pick random sample
        current_combo = []
        for site in site_list:
          current_est_choices = []
          for k in range(number_of_ests_dict[site]):
            current_est_choices.append(random.randrange(number_of_ests_dict[site]))
          current_est_choices.sort()
          current_combo.append(tuple(current_est_choices))
        #test if chosen before
        if not tuple(current_combo) in uniqueness_dict:
          uniqueness_dict[tuple(current_combo)]=1
          unique = True
          

      #build splines
      for k, site in enumerate(site_list):
        est_choices = current_combo[k]
        for m in est_choices:
          spline_dict[site].append(pos.all_splines[site][m])
      #for site_spline_tuples in current_combo:#combo_pool[index]:
        #for site, est_index in site_spline_tuples:
        #  spline_dict[site].append(pos.all_splines[site][est_index])
      #compute position
      (p, _) = compute_position(sites, spline_dict, pos.p, obj,
              s=POS_EST_S, m=POS_EST_M-1, n=POS_EST_N, delta=POS_EST_DELTA)
      bootstrap_resampled_positions.append(p)






    #indices = sorted(random.sample(xrange(number_of_combos), max_resamples))
    #count = 0
    #current_combo = combinator_generator.next()
    #for index in indices:
    #  while count < index:
    #    count +=1
    #    current_combo = combinator_generator.next()
      
  return bootstrap_resampled_positions

def compute_conf(C, Qt, scale=1):
  ''' Compute confidence region from covariance matrix.
    
    Method due to http://www.visiondummy.com/2014/04/
      draw-error-ellipse-representing-covariance-matrix/. 
    
    C -- covariance matrix.

    Qt -- is typically the cumulative probability of `t` from the chi-square 
          distribution with two degrees of freedom. This is also the Mahalanobis
          distance in the case of the bootstrap.

    scale -- In case weird scaling was used. 
  '''
  w, v = np.linalg.eig(C)
  if w[0] > 0 and w[1] > 0: # Positive definite. 

    i = np.argmax(w) # Major w[i], v[:,i]
    j = np.argmin(w) # Minor w[i], v[:,j]

    angle = np.arctan2(v[:,i][1], v[:,i][0]) 
    x = np.array([np.sqrt(Qt * w[i]), 
                  np.sqrt(Qt * w[j])])

    axes = x * scale

  else: raise PosDefError
  
  return (angle, axes)


def transform_coord(p, center, half_span, scale):
  ''' Transform position as a complex number to some coordinate system. ''' 
  x = [int((p.imag - center.imag) / scale) + half_span,
       int((p.real - center.real) / scale) + half_span]
  return np.array(x)

def transform_coord_inv(x, center, half_span, scale):
  ''' Transform position as a complex number to some coordinate system (inverse) ''' 
  p = np.complex( (((x[1] - half_span) * scale) + center.real), 
                  (((x[0] - half_span) * scale) + center.imag) )
  return p

  
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
