# position1.py -- Working on clean, succinct positiion estimator code. 
#
# PositionEstimator, WindowedPositionEstimator -- high level calls for
#   position estimation and aggregated site data. 
# 
# InsertPositions -- insert positoins into the datbaase.  
#
# class Position -- represent computed positions. 
#
# References
#
#  [ZB11] Handbook of Position Location: Theory, Practice, and 
#         Advances. Edited by Seyad A. Zekevat, R. Michael 
#         Beuhrer.
#
# TODO Does aggregating the bearing spectra for the same site 
#      and computing a spline over the sum *bad*? 
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
from scipy.interpolate import InterpolatedUnivariateSpline as spline1d
import scipy, scipy.stats
import numdifftools as nd
import utm
import itertools, random

HALF_SPAN = 15         
SCALE = 10             # Meters
ELLIPSE_PLOT_SCALE = 5 # Scaling factor


class PosDefError (Exception): pass

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
  P = {} # Compute bearing likelihood distributions.  
  for site_id in signal.get_site_ids():
    (P[site_id], obj) = method(signal[site_id], sv)

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
  positions = []

  P = {} # Compute bearing likelihood distributions. 
  for site_id in signal.get_site_ids():
    (P[site_id], obj) = method(signal[site_id], sv)
  
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
  
  def __init__(self, dep_id, p, t, likelihood, num_est, bearing, activity, splines, fella):
    
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
    self.fella = fella

  @classmethod
  def calc(cls, dep_id, P, signal, obj, sites, center, t_start, t_end):
    ''' Compute a position given bearing likelihood data. ''' 
    
    # Aggregate site data. 
    (splines, fella, bearing, activity, num_est) = aggregate_window(
                                  P, signal, obj, t_start, t_end)
    
    if len(splines) > 1: # Need at least two site bearings. 
      p_hat, likelihood = compute_position(sites, splines, center, obj)
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
               splines,     # siteID -> bearing likelihood spline
               fella)       # TODO 

  def get_likelihood(self):
    ''' Return normalized position likelihood. ''' 
    if self.likelihood and self.num_sites > 0:
      # NOTE if aggregate bearings are normalised, 
      # divide by self.num_sites; otherwise, divide
      # by self.num_est. See aggregate_spectrum().
      return self.likelihood / self.num_est
    else: return None
  
  def get_activity(self): 
    ''' Return activity measurement. ''' 
    if self.num_sites > 0:
      return np.mean(self.activity.values())
    else: return None

  def plot(self, fn, sites, center, scale, half_span, p_known=None):
    ''' Plot search space. '''

    if self.num_sites == 0:
      print 'yes'
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
       s=HALF_SPAN, facecolor='0.5', label='sites', zorder=10)
   
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
         self.dep_id))
    
    pp.savefig(fn)
    pp.clf()



### class ConfidenceRegion. ###################################################

class ConfidenceRegion0: 

  def __init__(self, pos, sites, significance_level=0.90, half_span=HALF_SPAN*10, scale=1, p_known=None):
    self.p_hat = pos.p
    self.level = significance_level
    self.half_span = half_span
    self.scale = scale
  
    if p_known: 
      x = transform_coord(p_known, self.p_hat, half_span, scale)
    else: 
      x = transform_coord(self.p_hat, self.p_hat, half_span, scale)
  
    (positions, likelihoods) = compute_likelihood(
                             sites, pos.splines, self.p_hat, scale, half_span)
    
    # Obj function, Hessian matrix, and gradient vector. 
    J = lambda (x) : likelihoods[x[0], x[1]]
    H = nd.Hessian(J)
    Del = nd.Gradient(J)
   
    # Covariance.  
    a = Del(x)
    b = np.linalg.inv(H(x))
    C = np.dot(b, np.dot(np.dot(a, np.transpose(a)), b))
  
    # Confidence interval. 
    self.e = compute_conf(self.p_hat, C, significance_level, 
                          half_span, scale, k=1) 
  
  def display(self, p_known=None):
    X, Y = self.e.cartesian()
    X = map(lambda x: int(x), X)
    Y = map(lambda y: int(y), Y)
    self.contour = set(zip(list(X), list(Y)))
    if p_known is not None:
      x_known = transform_coord(p_known, self.p_hat, self.half_span, self.scale)
    else:
      x_known = None
    fella = 20
    for i in range(-fella, fella+1):
      for j in range(-fella, fella+1):
        x = self.e.x + np.array([i,j])
        if x_known is not None and x[0] == x_known[0] and x[1] == x_known[1]: print 'C', 
        elif x[0] == self.e.x[0] and x[1] == self.e.x[1]: print 'P', 
        elif tuple(x) in self.contour: print '.',
        else: print ' ',
      print 

  def plot(self, fn, p_known=None):
    fig = pp.gcf()
    x_hat = self.e.x
  
    #(x_fit, y_fit) = fit_contour(x, y, N=10000)
    (x_fit, y_fit) = self.e.cartesian()  
    pp.plot(x_fit, y_fit, color='k', alpha=0.5)

    # x_hat
    pp.plot(x_hat[0], x_hat[1], color='k', marker='o')
    pp.text(x_hat[0]+0.25, x_hat[1]-0.25, '$\hat{\mathbf{x}}$', fontsize=24)
      
    # x_known
    if p_known:
      x_known = transform_coord(p_known, self.p_hat, self.half_span, self.scale)
      pp.plot([x_known[0]], [x_known[1]],  
              marker='o', color='k', fillstyle='none')
      pp.text(x_known[0]+0.25, x_known[1]-0.25, '$\mathbf{x}^*$', fontsize=24)
    
    pp.savefig(fn)
    pp.clf()

  
  def __contains__(self, p):
    return p in self.e



class ConfidenceRegion1 (ConfidenceRegion0): 

  def __init__(self, pos, sites, significance_level=0.90, half_span=HALF_SPAN*10, scale=1, p_known=None):
    ''' Compute covariance matrix of position estimater w.r.t true location `p`. 

      Assuming the estimate follows a bivariate normal distribution. 
      This follows [ZB11] equation 2.169. 

      Return a tuple (x, alpha), where x[0] gives the magnitude of the major 
      axis, x[1]s give the magnitude of the minor axis, and alpha gives the 
      angular orientation (relative to the x-axis) of the ellipse in degrees. 
      If C is not positive definite, then the distribution has no density: 
      return (None, None). 

      Based on the blog post: http://www.visiondummy.com/2014/04/draw-error-
      ellipse-representing-covariance-matrix/ by Vincent Spruyt. Note that
      this only applies to *known* covariance, e.g. estimated from multiple
      position estimates. 

    '''
    self.p_hat = pos.p
    self.level = significance_level
    self.half_span = half_span
    self.scale = scale
  
    if p_known: 
      x = transform_coord(p_known, self.p_hat, half_span, scale)
    else: 
      x = transform_coord(self.p_hat, self.p_hat, half_span, scale)
  
    (positions, likelihoods) = compute_likelihood(
                             sites, pos.splines, self.p_hat, scale, half_span)
    
    # Obj function, Hessian matrix, and gradient vector. 
    J = lambda (x) : likelihoods[x[0], x[1]]
    H = nd.Hessian(J)
    Del = nd.Gradient(J)
  
    A = []; B = []
    for i in range(len(pos.fella.values()[0])): # FIXME Not all lists will be the sam elength
      splines = {}
      for id in pos.fella.keys():
        splines[id] = pos.fella[id][i]
      (p, _) = compute_position(sites, splines, self.p_hat, np.argmax, HALF_SPAN, 3, 0, SCALE) # FIXME obj=np.argmax
      x = transform_coord(p, self.p_hat, half_span, scale)
   
      # Covariance of p_hat.  
      a = Del(x); A.append(np.dot(a, np.transpose(a)))
      b = H(x);   B.append(b)
      
    
    A = np.mean(A, 0)
    B = np.linalg.inv(np.mean(B, 0))
    C = np.dot(B, np.dot(A, B))

    # Confidence interval. 
    self.e = compute_conf(self.p_hat, C, significance_level, 
                          half_span, scale, k=1) 


class BootstrapConfidenceRegion (ConfidenceRegion0): 

  def __init__(self, pos, sites, conf_level=0.90, half_span=HALF_SPAN, scale=1):
    self.p_hat = pos.p
    self.level = conf_level
    self.half_span = half_span
    self.scale = scale
    
    P = []; k = len(pos.splines)
    for subsample in itertools.combinations(pos.splines.keys(), 3):
      splines = {}
      for id in subsample:
        splines[id] = pos.splines[id]
      (p, _) = compute_position(sites, splines, self.p_hat, np.argmax, HALF_SPAN, 3, 0, SCALE) # FIXME obj=np.argmax
      P.append(transform_coord(p, self.p_hat, half_span, scale))
    
    random.shuffle(P) # Estimates of sub samples. 
    A = np.array(P[len(P)/2:])
    B = np.array(P[:len(P)/2])
    C = np.cov(A[:,0], A[:,1])
    D = np.linalg.inv(C)
    x_bar = np.array([np.mean(B[:,0]), np.mean(B[:,1])])
    x_hat = transform_coord(self.p_hat, self.p_hat, half_span, scale)
    
    w = []
    for x in iter(B): 
      y = x - x_bar
      w.append(np.dot(np.transpose(y), np.dot(D, y)))
    Q = sorted(w)[int(len(w) * (1-conf_level))-1] 
    f = lambda(x) : np.dot(np.transpose(x_hat - x), np.dot(D, np.transpose(x_hat - x)))
    (level_set, contour) = compute_contour(x_hat, f, Q)
    #self.contour = contour
    X = np.array(map(lambda x : x[0], contour))
    Y = np.array(map(lambda x : x[1], contour))
    (x_center, angle, axes) = fit_ellipse(X, Y)
    p_center = transform_coord_inv(x_center, self.p_hat, half_span, scale)
    self.e = Ellipse(self.p_hat, angle, axes, half_span, scale)
  
  def display(self, p_known=None):
    X, Y = self.e.cartesian()
    X = map(lambda x: int(x), X)
    Y = map(lambda y: int(y), Y)
    contour = set(zip(list(X), list(Y)))
    if p_known is not None:
      x_known = transform_coord(p_known, self.p_hat, self.half_span, self.scale)
    else:
      x_known = None
    fella = 20
    x_hat = np.array([self.half_span, self.half_span])
    for i in range(-fella, fella+1):
      for j in range(-fella, fella+1):
        x = x_hat + np.array([i,j])
        x = np.array([int(x[0]), int(x[1])])
        if x_known is not None and x[0] == x_known[0] and x[1] == x_known[1]: print 'C', 
        elif x[0] == x_hat[0] and x[1] == x_hat[1]: print 'P', 
        elif tuple(x) in contour: print '.',
        else: print ' ',
      print 

class Ellipse:

  def __init__(self, p_hat, angle, axes, half_span, scale, x=None): 
    self.p_hat = p_hat
    self.angle = angle
    self.axes = axes
    self.half_span = half_span
    self.scale = scale
    self.x = np.array([half_span, half_span])

  def area(self):
    return np.pi * self.axes[0] * self.axes[1]

  def cartesian(self): 
    theta = np.linspace(0,2*np.pi)
    X = self.x[0] + self.axes[0]*np.cos(theta)*np.cos(self.angle) - \
                    self.axes[1]*np.sin(theta)*np.sin(self.angle)
    Y = self.x[1] + self.axes[0]*np.cos(theta)*np.sin(self.angle) + \
                    self.axes[1]*np.sin(theta)*np.cos(self.angle)
    return (X, Y)

  def __contains__(self, p):
    x = transform_coord(p, self.p_hat, self.half_span, self.scale) - self.x
    return ((x[0] / self.axes[0])**2 + (x[1] / self.axes[1])**2) <= 1 
    



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
  fella = {}
  for (id, L) in P.iteritems():
    mask = (t_start <= signal[id].t) & (signal[id].t < t_end)
    edsp = signal[id].edsp[mask]
    if edsp.shape[0] > 0:
      l = L[mask]
      p = aggregate_spectrum(l)
      splines[id] = compute_bearing_spline(p)
      fella[id] = []
      for i in range(len(l)): 
        fella[id].append(compute_bearing_spline(l[i]))
      activity[id] = (np.sum((edsp - np.mean(edsp))**2)**0.5)/np.sum(edsp)
      theta = obj(p); bearing[id] = (theta, p[theta])
      num_est += edsp.shape[0]
  
  return (splines, fella, bearing, activity, num_est)


def aggregate_spectrum(p):
  ''' Sum a set of bearing likelihoods. '''
  # NOTE normalising by the number of pulses effectively
  # reduces the sample size. 
  return np.sum(p, 0) #/ p.shape[0]


def compute_bearing_spline(l): 
  ''' Interpolate a spline on a bearing likelihood distribuiton. 
    
    Input an aggregated bearing distribution, e.g. the output of 
    `aggregate_spectrum(p)` where p is the output of `_per_site_data.mle()` 
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


def compute_position(sites, splines, center, obj, s=HALF_SPAN, m=3, n=-1, delta=SCALE):
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
  p_hat = center
  for i in reversed(range(n, m)):
    scale = pow(delta, i)
    (positions, likelihoods) = compute_likelihood(
                           sites, splines, p_hat, scale, s)
    
    index = obj(likelihoods)
    p_hat = positions.flat[index]
    likelihood = likelihoods.flat[index]

  return p_hat, likelihood


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
  
def compute_cov(x, H, Del):
  ''' Compute covariance matrix of estimate, given x the true position. ''' 
  a = Del(x)
  b = np.linalg.inv(H(x))
  C = np.dot(b, np.dot(np.dot(a, np.transpose(a)), b))
  return C


def compute_conf(p_hat, C, conf_level, half_span=0, scale=1, k=1):
  Qt = scipy.stats.chi2.ppf(conf_level, 2)

  # k - the number of samples (sites)
  w, v = np.linalg.eig(C / k)
  if w[0] > 0 and w[1] > 0: # Positive definite. 

    i = np.argmax(w) # Major w[i], v[:,i]
    j = np.argmin(w) # Minor w[i], v[:,j]

    angle = np.arctan2(v[:,i][1], v[:,i][0]) 
    x = np.array([2 * np.sqrt(Qt * w[i]), 
                  2 * np.sqrt(Qt * w[j])])

    axes = x * scale

  else: raise PosDefError
  
  return Ellipse(p_hat, angle, axes, half_span, scale)




def compute_contour(x_hat, f, Q):
  ''' Find the points that fall within confidence region of the estimate. ''' 
  S = set(); S.add((x_hat[0], x_hat[1]))
  level_set = S.copy()
  contour = set()
  max_size = float("+inf") # FIXME Computational stop gap. 

  while len(S) > 0 and len(S) < max_size and len(level_set) < max_size: 
    R = set()
    for x in S:
      if f(x) < Q: 
        level_set.add(x)
        R.add((x[0]+1, x[1]-1)); R.add((x[0]+1, x[1])); R.add((x[0]+1, x[1]+1))
        R.add((x[0],   x[1]-1));                        R.add((x[0] ,  x[1]+1))
        R.add((x[0]-1, x[1]-1)); R.add((x[0]-1, x[1])); R.add((x[0]-1, x[1]+1)) 
      else: 
        contour.add(x)
    S = R.difference(level_set)

  if len(S) == max_size or len(level_set) == max_size: 
    return None # Unbounded confidence region
  return (level_set, contour)


def fit_contour(x, y, N):
  ''' Fit closed countour to a set of points in R^2. 
  
    Convert the Cartesian coordinates (x, y) to polar coordinates (theta, r)
    and fit a spline. Sample uniform angles from this spline and compute the
    Fourier transform of their distancxe to the centroid of the contour. 
    `N` is the number of samples. 
  
    http://stackoverflow.com/questions/13604611/how-to-fit-a-closed-contour
  '''
  x0, y0 = np.mean(x), np.mean(y)
  C = (x - x0) + 1j * (y - y0)
  angles = np.angle(C)
  distances = np.abs(C)
  sort_index = np.argsort(angles)
  angles = angles[sort_index]
  distances = distances[sort_index]
  angles = np.hstack(([ angles[-1] - 2*np.pi ], angles, [ angles[0] + 2*np.pi ]))
  distances = np.hstack(([distances[-1]], distances, [distances[0]]))

  f = spline1d(angles, distances)
  theta = scipy.linspace(-np.pi, np.pi, num=N, endpoint=False) 
  distances_uniform = f(theta)

  fft_coeffs = np.fft.rfft(distances_uniform)
  fft_coeffs[5:] = 0 
  r = np.fft.irfft(fft_coeffs)
 
  x_fit = x0 + r * np.cos(theta)
  y_fit = y0 + r * np.sin(theta)

  return (x_fit, y_fit)


def fit_noisy_ellipse(x, y):
  ''' Fit ellipse to a set of points in R^2.

    http://nicky.vanforeest.com/misc/fitEllipse/fitEllipse.html
  '''
  x = x[:,np.newaxis]
  y = y[:,np.newaxis]
  D =  np.hstack((x*x, x*y, y*y, x, y, np.ones_like(x)))
  S = np.dot(D.T,D)
  C = np.zeros([6,6])
  C[0,2] = C[2,0] = 2; C[1,1] = -1
  E, V =  np.linalg.eig(np.dot(np.linalg.inv(S), C))
  n = np.argmax(np.abs(E))
  A = V[:,n]
     
  # Center of ellipse
  b,c,d,f,g,a = A[1]/2, A[2], A[3]/2, A[4]/2, A[5], A[0]
  num = b*b-a*c
  x0=(c*d-b*f)/num
  y0=(a*f-b*d)/num
  x = np.array([x0,y0])

  # Angle of rotation
  angle = 0.5*np.arctan(2*b/(a-c))

  # Length of Axes
  up = 2*(a*f*f+c*d*d+g*b*b-2*b*d*f-a*c*g)
  down1=(b*b-a*c)*( (c-a)*np.sqrt(1+4*b*b/((a-c)*(a-c)))-(c+a))
  down2=(b*b-a*c)*( (a-c)*np.sqrt(1+4*b*b/((a-c)*(a-c)))-(c+a))
  res1=np.sqrt(up/down1)
  res2=np.sqrt(up/down2)
  axes = np.array([res1, res2])

  return (x, angle, axes)


def fit_ellipse(x, y): 
  
  x_lim = np.array([np.min(x), np.max(x)])
  y_lim = np.array([np.min(y), np.max(y)])
  
  x_center = np.array([np.mean(x_lim), np.mean(y_lim)])
 
  X = np.vstack((x,y))
  D = (lambda d: np.sqrt(
          (d[0] - x_center[0])**2 + (d[1] - x_center[1])**2))(X)
  x_major = x_center - X[:,np.argmax(D)] 
  angle = np.arctan2(x_major[1], x_major[0])
  axes = np.array([np.max(D), np.min(D)])
  return (x_center, angle, axes)


  


  

 



### Testing, testing ... ######################################################


def test1(): 

  import time
  
  cal_id = 3
  dep_id = 105
  t_start = 1407452400 
  t_end = 1407455985 - (59 * 60) 

  db_con = util.get_db('reader')
  sv = signal1.SteeringVectors(db_con, cal_id)
  signal = signal1.Signal(db_con, dep_id, t_start, t_end)

  sites = util.get_sites(db_con)
  (center, zone) = util.get_center(db_con)
  assert zone == util.get_utm_zone(db_con)
  
  start = time.time()
  pos = PositionEstimator(dep_id, sites, center, signal, sv, 
    method=signal1.Signal.MLE)
  print "Finished in {0:.2f} seconds.".format(time.time() - start)
 
  print compute_conf(pos.p, pos.num_sites, sites, pos.splines)
  
  pos.plot('fella.png', sites, center, 10, 150)


if __name__ == '__main__':
  

  #test_exp()
  #test_bearing()
  #test_mle()
  test1()
