# position1.py -- Working on clean, succinct positiion estimator code. 
#
# PositionEstimator, WindowedPositionEstimator -- high level calls for
#   position estimation and aggregated site data. 
# 
# InsertPositions -- insert positoins into the datbaase.  
#
# class Position -- represent computed positions.
# class ConfidenceRegion
# class BoostrapConfidenceRegion (ConfidenceRegion)
# class Ellipse
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

class PositionError (Exception): 
  value = 0; msg = ''
  def __str__(self): return '%s (%d)' % (self.msg, self.value)
  
class PosDefError (PositionError): 
  value = 1
  msg = 'covariance matrix is positive definite.'

class BootstrapError (PositionError): 
  value = 2
  msg = 'not enough samples to perform boostrap.'

class UnboundedContourError (PositionError): 
  value = 3
  msg = 'exceeded maximum size of level set.'


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
  
  def __init__(self, dep_id, p, t, likelihood, num_est, bearing, activity, splines, sub_splines, all_splines, obj):
    
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
    self.sub_splines = sub_splines
    self.all_splines = all_splines
    self.obj = obj

  @classmethod
  def calc(cls, dep_id, P, signal, obj, sites, center, t_start, t_end):
    ''' Compute a position given bearing likelihood data. ''' 
    
    # Aggregate site data. 
    (splines, sub_splines, all_splines, bearing, activity, num_est) = aggregate_window(
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
               splines,     # siteID -> aggregated bearing likelihood spline
               sub_splines, # siteID -> spline of sub samples for bootstrapping
               all_splines,  
               obj)         # Objective function

  def get_likelihood(self):
    ''' Return normalized position likelihood. ''' 
    if self.likelihood and self.num_sites > 0:
      # NOTE if aggregate bearings are normalised, 
      # divide by self.num_sites; otherwise, divide
      # by self.num_est. See aggregate_spectrum().
      return self.likelihood / self.num_sites
    else: return None
  
  def get_activity(self): 
    ''' Return activity measurement. ''' 
    if self.num_sites > 0:
      return np.mean(self.activity.values())
    else: return None

  def plot(self, fn, sites, center, p_known=None, half_span=150, scale=10):
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




### class Ellipse. ###################################################

class Ellipse:

  def __init__(self, p_hat, angle, axes, half_span=0, scale=1, x=None):
    ''' Ellipse data structure. ''' 
    self.p_hat = p_hat
    self.angle = angle
    self.axes = axes
    self.half_span = half_span
    self.scale = scale
    self.x = np.array([half_span, half_span])

  def area(self):
    return np.pi * self.axes[0] * self.axes[1]

  def cartesian(self): 
    theta = np.linspace(0,2*np.pi, 360)
    X = self.x[0] + self.axes[0]*np.cos(theta)*np.cos(self.angle) - \
                    self.axes[1]*np.sin(theta)*np.sin(self.angle)
    Y = self.x[1] + self.axes[0]*np.cos(theta)*np.sin(self.angle) + \
                    self.axes[1]*np.sin(theta)*np.cos(self.angle)
    return (X, Y)

  def __contains__(self, p):
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
    pp.title("95\%-confidence region")
    pp.legend(title="Axis length")
    pp.savefig(fn)
    pp.clf()



### Covariance. ###############################################################

class Covariance:

  def __init__(self, pos, sites, p_known=None, half_span=75, scale=0.5):
    ''' Confidence region from asymptotic covariance. ''' 
    self.p_hat = pos.p
    self.half_span = half_span
    self.scale = scale
  
    if p_known:
      p = p_known
    else: 
      p = pos.p
    x = np.array([half_span, half_span])

    (positions, likelihoods) = compute_likelihood(
                             sites, pos.splines, p, scale, half_span)
    
    # Obj function, Hessian matrix, and gradient vector. 
    J = lambda (x) : likelihoods[x[0], x[1]]
    H = nd.Hessian(J)
    Del = nd.Gradient(J)
   
    # Covariance.  
    b = Del(x)  
    A = np.linalg.inv(H(x))
    self.C = np.dot(A, np.dot(np.dot(b, b.T), A)) 

  def conf(self, level): 
    ''' Emit confidence interval at the (1-conf_level) significance level. ''' 
    Qt = scipy.stats.chi2.ppf(level, 2) * self.scale
    (angle, axes) = compute_conf(self.C, Qt, 1) 
    return Ellipse(self.p_hat, angle, axes, 0, 1)


class Covariance2 (Covariance):
  
  def __init__(self, pos, sites, p_known=None, half_span=75, scale=0.5):
    ''' Confidence region from asymptotic covariance. ''' 
    self.p_hat = pos.p
    self.half_span = half_span
    self.scale = scale
    n = sum(map(lambda l : len(l), pos.sub_splines.values())) 
    m = n / pos.num_sites
  
    if p_known:
      p = p_known
    else: 
      p = pos.p
    x = np.array([half_span, half_span])
    
    C = np.zeros((2,2), dtype=np.float64)
    for i in range(m):
      splines = { id : p[i] for (id, p) in pos.all_splines.iteritems() }
      (positions, likelihoods) = compute_likelihood(
                               sites, splines, p, scale, half_span)
      J = lambda (x) : likelihoods[x[0], x[1]]
      b = np.array([nd.Gradient(J)(x)])

      A = np.linalg.inv(nd.Hessian(J)(x))
      d = np.dot(b, A)
      C += np.dot(d.T, d)
      
    self.C = C / n


class Covariance3 (Covariance):
  
  def __init__(self, pos, sites, p_known=None, half_span=75, scale=0.5):
    ''' Confidence region from asymptotic covariance. ''' 
    self.p_hat = pos.p
    self.half_span = half_span
    self.scale = scale
    n = sum(map(lambda l : len(l), pos.sub_splines.values())) 
    m = n / pos.num_sites
  
    if p_known:
      p = p_known
    else: 
      p = pos.p
    x = np.array([half_span, half_span])
    
    A = np.zeros((2,2), dtype=np.float64)
    b = np.zeros((2,), dtype=np.float64)
    for i in range(m):
      splines = { id : p[i] for (id, p) in pos.all_splines.iteritems() }
      (positions, likelihoods) = compute_likelihood(
                               sites, splines, p, scale, half_span)
      J = lambda (x) : likelihoods[x[0], x[1]]
      b += nd.Gradient(J)(x)
      A += nd.Hessian(J)(x)
      
    Ainv = np.linalg.inv(A / n)
    b = np.array([b / n]).T
    self.C = np.dot(Ainv, np.dot(b, b.T), Ainv)


class BootstrapCovariance:

  def __init__(self, pos, sites, max_resamples=500):
    ''' Bootstrap method for estimationg covariance of a position estimate. 

      Generate at most `max_resamples` position estimates by resampling the signals used
      in computing `pos`. 
    '''
    self.p_hat = pos.p
    n = sum(map(lambda l : len(l), pos.sub_splines.values())) 
    self.m = n / pos.num_sites

    # Generate sub samples. 
    P = bootstrap_resample(pos, sites, max_resamples, pos.obj)
    A = np.array(P[len(P)/2:])
    B = np.array(P[:len(P)/2])
    
    # Estimate covariance. 
    self.C = np.cov(A[:,0], A[:,1]) 
    
    # Mahalanobis distance of remaining estimates. 
    W = []
    D = np.linalg.inv(self.C)
    x_bar = np.array([np.mean(B[:,0]), np.mean(B[:,1])])
    x_hat = np.array([pos.p.imag, pos.p.real])
    for x in iter(B): 
      y = x - x_bar
      w = np.dot(np.transpose(y), np.dot(self.m * D, y))
      W.append(w)
    self.W = np.array(sorted(W))

  def conf(self, level): 
    ''' Emit confidence interval at the (1-conf_level) significance level. ''' 
    Qt = self.W[int(len(self.W) * level)] 
    (angle, axes) = compute_conf(self.C, Qt, 1) 
    return Ellipse(self.p_hat, angle, axes, 0, 1)



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
  sub_splines = {}
  all_splines = {}
  for (id, L) in P.iteritems():
    mask = (t_start <= signal[id].t) & (signal[id].t < t_end)
    edsp = signal[id].edsp[mask]
    if edsp.shape[0] > 0:
      l = L[mask]
      
      # Aggregated bearing spectrum spline per site.
      p = aggregate_spectrum(l)
      splines[id] = compute_bearing_spline(p) 
      
      # Sub sample splines. 
      sub_splines[id] = []
      if len(l) == 1: 
        sub_splines[id].append(compute_bearing_spline(l[0]))
      elif len(l) == 2:
        sub_splines[id].append(compute_bearing_spline(l[0]))
        sub_splines[id].append(compute_bearing_spline(l[1]))
      else:
        for index in itertools.combinations(range(len(l)), len(l)-1):
          p = aggregate_spectrum(l[np.array(index)])
          sub_splines[id].append(compute_bearing_spline(p)) 
      
      # All splines.
      all_splines[id] = []
      for i in range(len(l)):
        all_splines[id].append(compute_bearing_spline(l[i]))

      # Aggregated activity measurement per site. 
      activity[id] = (np.sum((edsp - np.mean(edsp))**2)**0.5)/np.sum(edsp)
      theta = obj(p); bearing[id] = (theta, p[theta])
      num_est += edsp.shape[0]
  
  return (splines, sub_splines, all_splines, bearing, activity, num_est)


def aggregate_spectrum(p):
  ''' Sum a set of bearing likelihoods. '''
  return np.sum(p, 0) / p.shape[0]

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


def compute_position(sites, splines, center, obj, s=HALF_SPAN, m=3, n=-2, delta=SCALE):
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


def bootstrap_resample(pos, sites, max_samples, obj):
  ''' Generate positionn estimates by sub sampling signal data. 

    Construct an objective function from a subset of the pulses (one pulse per site)
    and optimize over the search space. Repeat this at most `max_samples` times.
  '''
  N = reduce(int.__mul__, map(lambda S : len(S), pos.sub_splines.values()))
  if N < 2: # Number of pulse combinations
    raise BootstrapError  
  
  P = []
  for i in range(max_samples):
    splines = {}
    for id in pos.sub_splines.keys():
      j = random.randint(0, len(pos.sub_splines[id])-1)
      splines[id] = pos.sub_splines[id][j]
    (p, _) = compute_position(sites, splines, pos.p, obj) 
    P.append(transform_coord(p, pos.p, 0, 1))
    
  return P

def bootstrap_resample_site(pos, sites, max_samples, obj):
  ''' Random subsamples of sites. '''
  # TODO This method is probably more appropriate than bootstrap_resample()
  # for really small samples (<2 per site)
  P = []
  for site_ids in itertools.combinations(pos.splines.keys(), 2):
    splines = { id : pos.splines[id] for id in site_ids }
    (p, _) = compute_position(sites, splines, pos.p, obj) 
    P.append(transform_coord(p, pos.p, 0, 1))
  random.shuffle(P)
  return P

def compute_conf(C, Qt, scale=1):
  ''' Compute confidence region from covariance matrix.
    
    `Qt` is typically the cumulative probability of `t` from the chi-square 
    distribution with two degrees of freedom. 

    Method due to http://www.visiondummy.com/2014/04/
      draw-error-ellipse-representing-covariance-matrix/. 
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



def compute_contour(x_hat, f, Q):
  ''' Find the points that fall within confidence region of the estimate. 
  
    Given a point x_hat known to be contained by a contour defined by
    f(x) < Q, compute the contour.  
  ''' 
  S = set(); S.add((x_hat[0], x_hat[1]))
  level_set = S.copy()
  contour = set()
  max_size = 10000 # FIXME Computational stop gap. 

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

  if len(S) >= max_size or len(level_set) >= max_size: 
    return (None, None) # Unbounded confidence region
  return (level_set, contour)

def fit_ellipse(x, y): 
  ''' Fit ellipse parameters to a set of points in R^2. 
  
    The points should correspond a perfect ellipse. 
  ''' 
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

def fit_noisy_ellipse(x, y):
  ''' Least squares fit of an ellipse to a set of points in R^2. 

    The points are allowed to be noisy. Method due to  
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
  


if __name__ == '__main__':
  

  #test_exp()
  #test_bearing()
  #test_mle()
  test1()
