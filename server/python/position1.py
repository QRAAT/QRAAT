# position1.py -- Working on clean, succinct positiion estimator code. 
#
# PositionEstimator, WindowedPositionEstimator -- high level calls for
#   position estimation and aggregated site data. 
# 
# InsertPositions -- insert positoins into the datbaase.  
#
# class Position -- represent computed positions. 
#
# Copyright (C) 2015 Todd, Borrowman, Chris Patton
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

import util, signal1

import sys, time
import numpy as np
import matplotlib.pyplot as pp
from matplotlib.patches import Ellipse
from scipy.interpolate import InterpolatedUnivariateSpline as spline1d
import numdifftools as nd
import utm

HALF_SPAN = 15
ELLIPSE_PLOT_SCALE = 4



### Position estimation. ######################################################

def PositionEstimator(dep_id, sites, center, signal, sv, method=signal1.Signal.Bartlet):
  ''' Estimate the source of a signal. 
  
    Inputs: 
      
      sites -- a set of site locations represented in UTM easting/northing 
               as an `np.complex`. The imaginary component is easting and 
               the real part is northing.

      center -- initial guess of position, represented in UTM as an `np.complex`. 
                A good value would be the centroid of the sites.  

      signal -- instance of `class signal1.Signal`, signal data. 

      sv -- instance of `class signal1.SteeringVectors`, calibration data. 

      method -- Specify method for computing bearing likelihood distribution.

    Returns UTM position estimate as a complex number. 
  ''' 
  if method == signal1.Signal.Bartlet: obj = np.argmax
  elif method == signal1.Signal.MLE:   obj = np.argmin
  else: obj = np.argmax
  
  P = {} # Compute bearing likelihood distributions.  
  for site_id in signal.get_site_ids():
    P[site_id] = method(signal[site_id], sv)

  return Position.calc(dep_id, P, signal, obj, sites, center,
                                    signal.t_start, signal.t_end)


def WindowedPositionEstimator(dep_id, sites, center, signal, sv, t_step, t_win, 
                              method=signal1.Signal.Bartlet):
  ''' Estimate the source of a signal, aggregate site data. 
  
    Inputs: 
    
      sites, center, signal, sv
      
      t_step, t_win -- time step and window respectively. A position 
                       is computed for each timestep. 

    Returns a sequence of UTM positions. 
  ''' 
  if method == signal1.Signal.Bartlet: obj = np.argmax
  elif method == signal1.Signal.MLE:   obj = np.argmin
  else: obj = np.argmax
  
  positions = []

  P = {} # Compute bearing likelihood distributions. 
  for site_id in signal.get_site_ids():
    P[site_id] = method(signal[site_id], sv)
  
  for (t_start, t_end) in util.compute_time_windows(
                      signal.t_start, signal.t_end, t_step, t_win):
  
    positions.append(Position.calc(dep_id, P, signal, obj, 
                                    sites, center, t_start, t_end))
  
  return positions


def InsertPositions(db_con, positions, zone):
  ''' Insert positions into database. ''' 
  cur = db_con.cursor()
  number, letter = zone
  max_id = 0
  for pos in positions:
    if pos.p is None: 
      continue
    lat, lon = utm.to_latlon(pos.p.imag, pos.p.real, number, letter)
    cur.execute('''INSERT INTO position
                     (deploymentID, timestamp, latitude, longitude, easting, northing, 
                      utm_zone_number, utm_zone_letter, likelihood, 
                      activity, number_est_used)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                     (pos.dep_id, pos.t, round(lat,6), round(lon,6),
                      pos.p.imag, pos.p.real, number, letter, 
                      pos.get_likelihood(), pos.get_activity(),
                      pos.num_est))
    max_id = max(cur.lastrowid, max_id)

  return max_id





### class Position. ###########################################################

class Position:
  
  def __init__(self, dep_id, p, t, likelihood, num_est, bearing, activity, splines):
    
    assert len(bearing) == len(activity) and len(bearing) == len(splines)
    self.dep_id = dep_id
    self.num_sites = len(bearing)
    self.num_est = num_est
    self.p = p
    self.t = t
    self.likelihood = likelihood
    self.bearing = bearing
    self.activity = activity
    self.splines = splines

  @classmethod
  def calc(cls, dep_id, P, signal, obj, sites, center, t_start, t_end):
    ''' Compute a position given bearing likelihood data. ''' 
    
    # Aggregate site data. 
    (splines, bearing, activity, num_est) = aggregate_window(
                                  P, signal, obj, t_start, t_end)
    
    if len(splines) > 1: # Need at least two site bearings. 
      p_hat, likelihood = compute_position(sites, splines, center, obj, half_span=HALF_SPAN)
    else: p_hat, likelihood = None, None
     
    # Return a position object. 
    num_sites = len(bearing)
    t = (t_end + t_start) / 2
    return cls(dep_id,      # deployment ID
               p_hat,       # pos. estimate
               t,           # middle of time window 
               likelihood,  # likelihood of pos. esstimate
               num_est,     # total pulses used in calculation
               bearing,     # siteID -> (theta, likelihood)
               activity,    # siteID -> activity
               splines)     # siteID -> bearing likelihood spline

  def get_likelihood(self):
    ''' Return normalized position likelihood. ''' 
    if self.likelihood and self.num_sites > 0:
      return self.likelihood / self.num_sites
    else: return None
  
  def get_activity(self): 
    ''' Return activity measurement. ''' 
    if self.num_sites > 0:
      return np.mean(self.activity.values())
    else: return None

  def plot(self, fn, sites, center, scale, half_span):
    ''' Plot search space. '''

    if self.num_sites == 0:
      return 

    (positions, likelihoods) = compute_likelihood(
                         sites, self.splines, center, scale, half_span)

    fig = pp.gcf()
    
    # Transform to plot's coordinate system.
    e = lambda(x) : ((x - center.imag) / scale) + half_span
    n = lambda(y) : ((y - center.real) / scale) + half_span 
    f = lambda(p) : [e(p.imag), n(p.real)]
    
    x_left =  center.imag - (half_span * scale)
    x_right = center.imag + (half_span * scale)
    
    # Search space
    p = pp.imshow(likelihoods.transpose(), 
        origin='lower',
        extent=(0, half_span * 2, 0, half_span * 2),
        cmap='YlGnBu',
        aspect='auto', interpolation='nearest')

    # Sites
    pp.scatter(
      [e(float(s.imag)) for s in sites.values()],
      [n(float(s.real)) for s in sites.values()],
       s=HALF_SPAN, facecolor='0.5', label='sites', zorder=10)
    
    # Pos. estimate with confidence ellipse
    if self.p is not None: 
      ax = fig.add_subplot(111)
      (x, alpha) = compute_conf(compute_covariance(self.p, sites, self.splines))
      if x is not None: 
        ellipse = Ellipse(xy=f(self.p), width=x[0]*2*ELLIPSE_PLOT_SCALE, 
                        height=x[1]*2*ELLIPSE_PLOT_SCALE, angle=alpha)
        ax.add_artist(ellipse)
        ellipse.set_clip_box(ax.bbox)
        ellipse.set_alpha(0.2)
        ellipse.set_facecolor([1.0,1.0,1.0])
      else: print "Skipping non-positive definite cov. matrix"
      pp.plot(e(self.p.imag), n(self.p.real), 
            'w.', markersize=2.0,  label='position', zorder=11)

    pp.clim()   # clamp the color limits
    pp.legend()
    pp.axis([0, half_span * 2, 0, half_span * 2])
    
    t = time.localtime(self.t)
    pp.title('%04d-%02d-%02d %02d%02d:%02d depID=%d' % (
         t.tm_year, t.tm_mon, t.tm_mday,
         t.tm_hour, t.tm_min, t.tm_sec,
         self.dep_id))
    
    pp.savefig(fn)
    pp.clf()



### Low level calls. ##########################################################

def aggregate_window(P, signal, obj, t_start, t_end):
  ''' Aggregate site data, compute splines for pos. estimation. 
  
    Site data includes the most likely bearing to each site, 
    measurement of activity at each site, and a spline 
    interpolation of bearing distribution at each site. 
  '''

  num_est = 0
  splines = {}  
  activity = {}
  bearing = {}
  for (id, L) in P.iteritems():
    mask = (t_start <= signal[id].t) & (signal[id].t < t_end)
    edsp = signal[id].edsp[mask]
    if edsp.shape[0] > 0:
      l = aggregate_bearing(L[mask])
      splines[id] = compute_bearing_spline(l)
      activity[id] = (np.sum((edsp - np.mean(edsp))**2)**0.5)/np.sum(edsp)
      theta = obj(l); bearing[id] = (theta, l[theta])
      num_est += edsp.shape[0]
  
  return (splines, bearing, activity, num_est)


def aggregate_bearing(p):
  ''' Sum a set of bearing likelihoods. '''
  # Average the likelihoods of the pulses for each bearing. TODO The idea here 
  # is that multiplie data may bias the result of the DOA or position estimator. 
  # Is there anything wrong with this? 
  return np.sum(p, 0) / p.shape[0]


def compute_bearing_spline(l): 
  ''' Interpolate a spline on a bearing likelihood distribuiton. 
    
    Input an aggregated bearing distribution, e.g. the output of 
    `aggregate_bearing(p)` where p is the output of `_per_site_data.mle()` 
    or `_per_site_data.bartlet()`.
  '''
  bearing_domain = np.arange(-360,360)         
  likelihood_range = np.hstack((l, l)) 
  return spline1d(bearing_domain, likelihood_range)


def compute_likelihood(sites, splines, center, scale, half_span):
  ''' Compute a grid of candidate points and their likelihoods. '''
    
  # Generate a grid of positions with center at the center. 
  positions = np.zeros((half_span*2+1, half_span*2+1),np.complex)
  for e in range(-half_span,half_span+1):
    for n in range(-half_span,half_span+1):
      positions[e + half_span, n + half_span] = center + np.complex(n * scale, e * scale)

  # Compute the likelihood of each position as the sum of the likelihoods 
  # of bearing to each site. 
  likelihoods = np.zeros(positions.shape, dtype=float)
  for id in splines.keys():
    bearing_to_positions = np.angle(positions - sites[id]) * 180 / np.pi
    likelihoods += splines[id](bearing_to_positions.flat).reshape(bearing_to_positions.shape)
  
  return (positions, likelihoods)


def compute_position(sites, splines, center, obj, half_span=HALF_SPAN): 
  ''' Maximize (resp. minimize) over position space. 

    A simple, speedy algorithm for finding the most likely source of a 
    transmitter signal in Euclidean space, given a bearing distribution from a 
    set of receiver sites. 

    Inputs: 
      
      sites, center - UTM positions of receiver sites and center, the initial 
                      guess of the transmitter's position. 
      
      splines -- a set of splines corresponding to the bearing likelihood
                 distributions for each site.

      half_span -- scaling factor for generating a grid of candidate positions. 
                   This is half the length of a side of the square bounding the
                   grid.

      obj -- np.argmin or np.argmax
    
      Returns UTM position estimate as a complex number. 
  '''
  scale = 100
  p_hat = center
  while scale >= 1:
  
    (positions, likelihoods) = compute_likelihood(
                           sites, splines, p_hat, scale, half_span)
    
    index = obj(likelihoods)
    p_hat = positions.flat[index]
    likelihood = likelihoods.flat[index]
    scale /= 10

  return p_hat, likelihood


def compute_covariance(p, sites, splines, half_span=150, scale=1):

  e = lambda(x0) : int((x0 - p.imag) / scale) + half_span
  n = lambda(y1) : int((y1 - p.real) / scale) + half_span
  f = lambda(p) : [e(p.imag), n(p.real)]
    
  (positions, likelihoods) = compute_likelihood(
                           sites, splines, p, scale, half_span)
    
  J = lambda (x) : likelihoods[x[0], x[1]]
  H = nd.Hessian(J)
  Del = nd.Gradient(J)
  
  a = Del(f(p))
  b = np.linalg.inv(H(f(p)))
  C = np.dot(b, np.dot(a, np.dot(np.transpose(a), b)))
  return C # TODO double check!


def compute_conf(C, sig=0.95, scale=1):
  
  chi_squared = {0.95 : 5.991} 
  assert sig in chi_squared.keys()

  w, v = np.linalg.eig(C)
  if w[0] > 0 and w[1] > 0: # Positive definite 

    i = np.argmax(w) # Major w[i], v[:,i]
    j = np.argmin(w) # Minor w[i], v[:,j]

    a = np.arctan2(v[:,i][1], v[:,i][0]) * 180 / np.pi
    x = np.array([2 * np.sqrt(chi_squared[sig] * w[i]), 
                  2 * np.sqrt(chi_squared[sig] * w[j])])
    return (x * scale, a) # TODO double check!

  else: return (None, None)

  





### Testing, testing ... ######################################################


def test1(): 
  
  cal_id = 3
  dep_id = 105
  t_start = 1407452400 
  t_end = 1407455985 #- (50 * 60)

  db_con = util.get_db('writer')
  sv = signal1.SteeringVectors(db_con, cal_id)
  signal = signal1.Signal(db_con, dep_id, t_start, t_end)

  sites = util.get_sites(db_con)
  (center, zone) = util.get_center(db_con)
  assert zone == util.get_utm_zone(db_con)
  
  positions = WindowedPositionEstimator(dep_id, sites, center, signal, sv, 60, 120,
                                         method=signal1.Signal.Bartlet)

  #InsertPositions(db_con, positions, zone)
  for i, pos in enumerate(positions):
    pos.plot('pos%d.png' % (i+1), sites, center, 10, 150) 


  #pos = PositionEstimator(dep_id, sites, center, signal, sv)
  #C = compute_covariance(pos.p, sites, pos.splines)
  #print C
  #print compute_conf(C)
  #pos.plot('fella.png', sites, center, 10, 150)

if __name__ == '__main__':
  

  #test_exp()
  #test_bearing()
  #test_mle()
  test1()
