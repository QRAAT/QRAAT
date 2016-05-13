# position.py -- Bearing, position, and covariance estimation of signals.  
#
# High level calls, database interaction: 
#  - PositionEstimator
#  - WindowedPositionEstimator
#  - InsertPositions
#  - ReadPositions
#  - ReadBearings
#  - ReadAllBearings
#
# Objects defined here: 
#  - class Position
#  - class Bearing
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

import numpy as np
from scipy.interpolate import InterpolatedUnivariateSpline as spline1d
import utm
import itertools

# Paramters for position estimation. 
EASTING_MIN = 573000
EASTING_MAX = 576000
NORTHING_MIN = 4259000
NORTHING_MAX = 4263000
STEPSIZE = 5

# Normalize bearing spectrum. 
NORMALIZE_SPECTRUM = False



### High level function calls. ################################################

def PositionEstimator(signal, sites, sv, method=signal.Signal.Bartlet,
                        stepsize = STEPSIZE, emin = EASTING_MIN, emax=EASTING_MAX,
                        nmin = NORTHING_MIN, nmax = NORTHING_MAX):
  ''' Estimate the source of a signal. 
  
    Inputs: 
      
      signal -- instance of `class signal.Signal`, signal data. 
      
      sites -- a map from siteIDs to site positions represented as UTM 
               easting/northing as a complex number. The imaginary component 
               is easting and the real part is northing.

      sv -- instance of `class signal.SteeringVectors`, calibration data. 

      method -- Specify method for computing bearing likelihood distribution.

      stepsize, emin, emax, nmin, nmax -- Parameters for position estimation algorithm. 

    Returns an instance of `class position.Position`. 
  ''' 
  if len(signal) > 0: 
    bearing_spectrum = {} # Compute bearing likelihood distributions.  
    for site_id in signal.get_site_ids().intersection(sv.get_site_ids()): 
      bearing_spectrum[site_id] = method(signal[site_id], sv)

    return Position(bearing_spectrum, signal, sites, signal.t_start, signal.t_end,
                    stepsize, emin, emax, nmin, nmax)

  else:
    return None


def WindowedPositionEstimator(signal, sites, sv, t_step, t_win, 
                               method=signal.Signal.Bartlet, 
                               stepsize = STEPSIZE, emin = EASTING_MIN, emax=EASTING_MAX,
                               nmin = NORTHING_MIN, nmax = NORTHING_MAX,
                               prepare_for_cov=False):
  ''' Estimate the source of a signal for windows of data over ``signal``. 
  
    Inputs: 
    
      signal -- instance of `class signal.Signal`, signal data. 
      
      sites -- a map from siteIDs to site positions represented as UTM 
               easting/northing as a complex number. The imaginary component 
               is easting and the real part is northing.

      sv -- instance of `class signal.SteeringVectors`, calibration data. 

      method -- Specify method for computing bearing likelihood distribution.
      
      t_step, t_win -- time step and window respectively. A position 
                       is computed for each timestep. 

      stepsize, emin, emax, nmin, nmax -- Parameters for position estimation algorithm. 

    Returns a list of `class position.Position` instances. 
  ''' 
  pos = []

  if len(signal) > 0: 
    bearing_spectrum = {} # Compute bearing likelihood distributions. 

    for site_id in signal.get_site_ids().intersection(sv.get_site_ids()): 
      bearing_spectrum[site_id] = method(signal[site_id], sv)
    
    for (t_start, t_end) in util.compute_time_windows(
                        signal.t_start, signal.t_end, t_step, t_win):
    
      pos.append(Position(bearing_spectrum, signal, 
                  sites, t_start, t_end, stepsize, emin, emax, nmin, nmax,
                  prepare_for_cov))
    
  return pos


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
    self.all_splines = None
    
    self.pos_id = None
    self.zone = None
    self.latitude = None
    self.longitude = None
  
    if len(args) == 11: 
      self.calc(*args)

  def calc(self, bearing_spectrum, signal, sites, t_start, t_end, stepsize, emin, emax, nmin, nmax, prepare_for_cov):
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
         
        sites -- mapping from siteIDs to receiver locations. 

        t_start, t_end -- slice of `signal` data to use for estimate. 

        stepsize, emin, emax, nmin, nmax -- Parameters for position estimation algorithm. 
    ''' 
    # Aggregate site data. 
    (splines, all_splines, bearings, num_est) = aggregate_window(
                                  bearing_spectrum, signal, t_start, t_end,
                                  prepare_for_cov)
   
    if len(splines) > 1: # Need at least two site bearings. 
      p_hat, likelihood = compute_position(sites, splines, stepsize, emin, emax, nmin, nmax)
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
    self.all_splines = all_splines # siteID -> spline for each pulse

 
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
    import time
    import matplotlib.pyplot as pp

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

    if len(args) == 3:
      self.calc(*args)

  def calc(self, edsp, bearing_spectrum, est_ids):
    ''' Compute bearing from `bearing_spectrum` and activity from `edsp`.

      Inputs: 

        bearing_spectrum -- two dimensional array of signals versus 
                            bearing likelihoods. 

        edsp -- a list of real numbers indicating the signal power 
                of each signal. 

        est_ids -- estIDs (serial identifiers in database) of the signals. 
    '''
    self.est_ids = est_ids
    self.num_est = len(est_ids)
    self.bearing = np.argmax(bearing_spectrum)

    # Normalized likelihood. 
    self.likelihood = bearing_spectrum[self.bearing]
    if not NORMALIZE_SPECTRUM: #TAB HUH? See other NORMALIZE
      self.likelihood /= self.num_est
    
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
def aggregate_window(bearing_spectrum_per_site_dict, signal_per_site_dict, t_start, t_end,
                     calc_all_splines=False):
  ''' Aggregate site data, compute splines for pos. estimation. 
  
    Site data includes the most likely bearing to each site, 
    measurement of activity at each site, and a spline 
    interpolation of bearing distribution at each site. 
  '''

  num_est = 0
  splines = {}  
  bearings = {}

  if calc_all_splines: 
    all_splines = {}
  else: all_splines = None

  for (siteID, bearing_spectrum) in bearing_spectrum_per_site_dict.iteritems():
    mask = (t_start <= signal_per_site_dict[siteID].t) & (signal_per_site_dict[siteID].t < t_end)
    est_ids = signal_per_site_dict[siteID].est_ids[mask]
    edsp = signal_per_site_dict[siteID].edsp[mask]
    if edsp.shape[0] > 0:
      likelihoods = bearing_spectrum[mask]
      # Aggregated bearing spectrum spline per site.
      spectrum = aggregate_spectrum(likelihoods)
      splines[siteID] = compute_bearing_spline(spectrum)
      
      # All splines.
      if calc_all_splines: 
        all_splines[siteID] = []
        for i in range(len(likelihoods)):
          all_splines[siteID].append(compute_bearing_spline(likelihoods[i]))

      # Aggregated data per site.
      bearings[siteID] = Bearing(edsp, spectrum, est_ids)

      num_est += edsp.shape[0]
  
  return (splines, all_splines, bearings, num_est)


def aggregate_spectrum(p):
  ''' Sum a set of bearing likelihoods. '''
  if NORMALIZE_SPECTRUM:
    return np.sum(p, 0) / p.shape[0]#TAB HUH? SEE position.calc
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


def compute_likelihood_grid(sites, splines, stepsize, emin, emax, nmin, nmax):
  ''' Compute a grid of candidate points and their likelihoods. '''
  # Generate a grid of positions with center at the center. 
  e_range = np.arange(emin,emax+stepsize,stepsize)
  n_range = np.arange(nmin,nmax+stepsize,stepsize)
  positions = np.zeros((len(e_range), len(n_range)),np.complex)
  for j,e in enumerate(e_range):
    for k,n in enumerate(n_range):
      positions[j, k] = np.complex(n, e)
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

def compute_position(sites, splines, stepsize, emin, emax, nmin, nmax):
  ''' Maximize over position space. 

    Grid search algorithm for position estimation.  First pass is stepsize grid
    within boundry.  Second pass is 1 meter grid bounding the likelihoods > 90% max
    of first pass.

    Inputs: 
      
      sites - UTM positions of receiver sites. 
      
      splines -- a set of splines corresponding to the bearing likelihood
                 distributions for each site.

      stepsize -- initial stepsize for grid search

      emin, emax, nmin, nmax -- initial grid boundary for search
    
      Returns UTM position estimate as a complex number and the likelihood
      of the position
  '''
  
  (positions, likelihoods) = compute_likelihood_grid(
                             sites, splines, stepsize, emin, emax, nmin, nmax)
  max_llh = np.max(likelihoods)
  select_positions = positions[likelihoods > 0.9*max_llh]
  emin = np.min(select_positions.imag)
  emax = np.max(select_positions.imag)
  nmin = np.min(select_positions.real)
  nmax = np.max(select_positions.real)
  stepsize = 1
  (positions, likelihoods) = compute_likelihood_grid(
                             sites, splines, stepsize, emin, emax, nmin, nmax)
  max_llh = np.max(likelihoods)
  p_hat = positions.flat[np.argmax(likelihoods)]
  return p_hat, max_llh




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
