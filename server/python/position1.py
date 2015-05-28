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
# Copyright (C) 2015 Chris Patton, Todd Borrowman
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

# Paramters for position estimation. 
POS_EST_M = 3
POS_EST_N = -1
POS_EST_DELTA = 5
POS_EST_S = 10

# Normalize bearing spectrum. 
NORMALIZE_SPECTRUM = False

# Enable asymptotic covariance (compute Position.all_splines)
ENABLE_ASYMPTOTIC = False

# Paramters for bootstrap covariance estimation. 
BOOT_MAX_RESAMPLES = 200
BOOT_CONF_LEVELS = [0.68, 0.80, 0.90, 0.95, 0.997]

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

class UnboundedContourError (PositionError): 
  value = 5
  msg = 'exceeded maximum size of level set.'


### Position estimation. ######################################################

def PositionEstimator(dep_id, sites, center, signal, sv, method=signal.Signal.Bartlet,
                        s=POS_EST_S, m=POS_EST_M, n=POS_EST_N, delta=POS_EST_DELTA):
  ''' Estimate the source of a signal. 
  
    Inputs: 
      
      sites -- a set of site locations represented in UTM easting/northing 
               as an `np.complex`. The imaginary component is easting and 
               the real part is northing.

      center -- initial guess of position, represented in UTM as an `np.complex`. 
                A good value would be the centroid of the sites.  

      signal -- instance of `class signal.Signal`, signal data. 

      sv -- instance of `class signal.SteeringVectors`, calibration data. 

      method -- Specify method for computing bearing likelihood distribution.

    Returns UTM position estimate as a complex number. 
  ''' 
  B = {} # Compute bearing likelihood distributions.  
  for site_id in signal.get_site_ids():
    (B[site_id], obj) = method(signal[site_id], sv)

  return Position(dep_id, B, signal, obj, sites, center,
                                    signal.t_start, signal.t_end, s, m, n, delta)


def WindowedPositionEstimator(dep_id, sites, center, signal, sv, t_step, t_win, 
                              method=signal.Signal.Bartlet, 
                              s=POS_EST_S, m=POS_EST_M, n=POS_EST_N, delta=POS_EST_DELTA):
  ''' Estimate the source of a signal, aggregate site data. 
  
    Inputs: 
    
      sites, center, signal, sv
      
      t_step, t_win -- time step and window respectively. A position 
                       is computed for each timestep. 

    Returns a sequence of UTM positions. 
  ''' 
  pos = []

  B = {} # Compute bearing likelihood distributions. 
  for site_id in signal.get_site_ids():
    (B[site_id], obj) = method(signal[site_id], sv)
  
  for (t_start, t_end) in util.compute_time_windows(
                      signal.t_start, signal.t_end, t_step, t_win):
  
    pos.append(Position(dep_id, B, signal, obj, 
                              sites, center, t_start, t_end, s, m, n, delta))
  
  return pos

def WindowedCovarianceEstimator(sites, pos, max_resamples=BOOT_MAX_RESAMPLES):  
  ''' Compute covariance of each pos. estimate in ``pos``.  ''' 
  cov = []
  for P in pos: 
    C = BootstrapCovariance(P, sites, max_resamples)
    cov.append(C)
  return cov

def InsertBearings(db_con, pos):
  ''' Insert bearings into database ''' 
  cur = db_con.cursor()
  max_id = 0
  for P in pos:
    for site_id in P.bearing.keys(): 
      bearing, likelihood, activity, num_est = P.bearing[site_id]
      cur.execute('''INSERT INTO bearing 
                          (deploymentID, siteID, timestamp, 
                           bearing, likelihood, activity, number_est_used)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)''', 
                 (P.dep_id, site_id, P.t, 
                  bearing, likelihood, activity, num_est))
      max_id = max(max_id, cur.lastrowid)
  return max_id


def InsertPositions(db_con, zone, pos):
  ''' Insert positions into database. ''' 
  max_id = 0
  for i in range(len(pos)):
    pos_id = pos[i].insert_db(db_con, zone)
    if pos_id:
      max_id = max(pos_id, max_id)
  return max_id

def InsertPositionsCovariances(db_con, zone, pos, cov):
  ''' Insert positions and covariances into database. ''' 
  max_id = 0
  for i in range(len(pos)):
    pos_id = pos[i].insert_db(db_con, zone)
    if pos_id:
      max_id = max(pos_id, max_id)
      cov_id = cov[i].insert_db(db_con, pos_id)
  return max_id

def ReadPositions(db_con, dep_id, t_start, t_end): 
  cur = db_con.cursor()
  cur.execute('''SELECT ID, timestamp, latitude, longitude, easting, northing, 
                        utm_zone_number, utm_zone_letter, likelihood, 
                        activity, number_est_used
                   FROM position
                  WHERE deploymentID = %s
                    AND timestamp >= %s
                    AND timestamp <= %s''', (dep_id, t_start, t_end))
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
  cur = db_con.cursor()
  cur.execute('''SELECT status, method, 
                        cov11, cov12, cov21, cov22,
                        w99, w95, w90, w80, w68,
                        easting, northing
                   FROM covariance
                   JOIN position as p ON p.ID = positionID
                  WHERE deploymentID = %s
                    AND timestamp >= %s
                    AND timestamp <= %s''', (dep_id, t_start, t_end))
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
    
    self.dep_id = None
    self.num_sites = None
    self.num_est = None
    self.p = None
    self.t = None
    self.likelihood = None
    self.activity = None
    self.bearing = None
    
    self.splines = None
    self.sub_splines = None
    self.all_splines = None
    self.obj = None
    
    self.pos_id = None
    self.zone = None
    self.latitude = None
    self.longitude = None
  
    if len(args) == 12: 
      self.calc(*args)

  def calc(self, dep_id, B, signal, obj, sites, center, t_start, t_end, s, m, n, delta):
    ''' Compute a position given bearing likelihood data. ''' 
    
    # Aggregate site data. 
    (splines, sub_splines, all_splines, bearing, activity, num_est) = aggregate_window(
                                  B, signal, obj, t_start, t_end)
    
    if len(splines) > 1: # Need at least two site bearings. 
      p_hat, likelihood = compute_position(sites, splines, center, obj, s, m, n, delta)
    else: p_hat, likelihood = None, None
    
    # Return a position object. 
    num_sites = len(bearing)
    t = (t_end + t_start) / 2
    
    self.dep_id = dep_id
    self.p = p_hat
    self.t = t
    
    if likelihood and num_sites > 0:
      if NORMALIZE_SPECTRUM:
        self.likelihood = likelihood / num_sites
      else: 
        self.likelihood = likelihood / num_est
    
    if num_sites > 0:
      self.activity = np.mean(activity.values())
    
    self.bearing = {}
    for (site_id, (bearing, likelihood, num_est)) in bearing.iteritems():
      self.bearing[site_id] = (bearing, likelihood, activity[site_id], num_est)

    self.num_est = num_est
    self.num_sites = num_sites

    self.splines = splines         # siteID -> aggregated bearing likelihood spline
    self.sub_splines = sub_splines # siteID -> spline of sub samples for bootstrapping
    self.all_splines = all_splines # siteID -> spline for each pulse
    self.obj = obj                 # objective function used in pos. est.
 
  def insert_db(self, db_con, zone):
    ''' Insert position into DB. ''' 
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
                     (self.dep_id, self.t, round(lat,6), round(lon,6),
                      self.p.imag, self.p.real, number, letter, 
                      self.likelihood, self.activity,
                      self.num_est))
    return cur.lastrowid

  def plot(self, fn, sites, center, p_known=None, half_span=150, scale=10):
    ''' Plot search space. '''
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
         self.dep_id))
    
    pp.savefig(fn)
    pp.clf()




### class Ellipse. ###################################################

class Ellipse:

  def __init__(self, p_hat, angle, axes, half_span=0, scale=1):
    ''' Ellipse data structure. ''' 
    self.p_hat = p_hat
    self.angle = angle
    self.axes = axes
    self.half_span = half_span
    self.scale = scale
    self.x = np.array([half_span, half_span])

  def area(self):
    return np.pi * self.axes[0] * self.axes[1] 

  def eccentricity(self):
    return np.sqrt(1 - ((self.axes[1]/2)**2) / ((self.axes[0]/2)**2))

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
    pp.legend(title="Axis length")
    pp.savefig(fn, dpi=150, bbox_inches='tight')
    pp.clf()



### Covariance. ###############################################################

class Covariance:
  
  def __init__(self, *args, **kwargs):
    self.method = 'asym'
    self.p_hat = None
    self.half_span = None
    self.scale = None
    self.m = None
    self.C = None

    if len(args) == 2: 
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
   
    # Hessian
    (positions, likelihoods) = compute_likelihood_grid(
                             sites, pos.splines, p, scale, half_span)
    J = lambda (x) : likelihoods[x[0], x[1]]
    H = nd.Hessian(J)(x)
    A = np.linalg.inv(H)

    # Gradient
    B = np.zeros((2,2), dtype=np.float64)
    for i in range(self.m):
      splines = { id : p[i] for (id, p) in pos.all_splines.iteritems() }
      (positions, likelihoods) = compute_likelihood_grid(
                               sites, splines, p, scale, half_span)
      J = lambda (x) : likelihoods[x[0], x[1]]
      b = np.array([nd.Gradient(J)(x)]).T
      B += np.dot(b, b.T)
    B = B / self.m
    
    self.C = np.dot(A, np.dot(B, A))

  def __getitem__(self, index):
    return self.C[index]

  def conf(self, level): 
    ''' Emit confidence interval at the (1-conf_level) significance level. ''' 
    Qt = scipy.stats.chi2.ppf(level, 2) 
    (angle, axes) = compute_conf(self.C, 2 * Qt / self.m, 1) 
    return Ellipse(self.p_hat, angle, axes, 0, 1)


class BootstrapCovariance (Covariance):

  def __init__(self, *args, **kwargs):
    ''' Bootstrap method for estimationg covariance of a position estimate. 

      Generate at most `max_resamples` position estimates by resampling the signals used
      in computing `pos`. 
    '''
    self.method = 'boot'
    self.C = None
    self.W = {}
    self.p_hat = None
    if len(args) >= 2: 
      self.calc(*args, **kwargs)
 

  def calc(self, pos, sites, max_resamples=200):
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
    ''' Insert into DB. '''
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

  def calc(self, pos, sites, max_resamples=200):
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

  if ENABLE_ASYMPTOTIC: 
    all_splines = {}
  else: all_splines = None

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
      if ENABLE_ASYMPTOTIC: 
        all_splines[id] = []
        for i in range(len(l)):
          all_splines[id].append(compute_bearing_spline(l[i]))

      # Aggregated activity measurement per site. 
      activity[id] = (np.sum((edsp - np.mean(edsp))**2)**0.5)/np.sum(edsp)
      theta = obj(p)
      bearing[id] = (theta, p[theta] / signal[id].count, signal[id].count)
      num_est += edsp.shape[0]
  
  return (splines, sub_splines, all_splines, bearing, activity, num_est)


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
  for id in splines.keys():
    bearing_to_positions = np.angle(positions - sites[id]) * 180 / np.pi
    likelihoods += splines[id](bearing_to_positions.flat).reshape(bearing_to_positions.shape)
  
  return (positions, likelihoods)


def compute_likelihood(sites, splines, p): 
  likelihood = 0
  for id in splines.keys():
    bearing = np.angle(p - sites[id]) * 180 / np.pi
    likelihood += splines[id](bearing)
  return likelihood


def compute_position(sites, splines, center, obj, s, m, n, delta):
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
  assert m >= n
  p_hat = center
  span = s * 2 + 1
  for i in reversed(range(n, m+1)):
    scale = delta ** i
    a = b = ct = 0
    while ct < 10 and (a == 0 or a == span-1 or b == 0 or b == span-1): 
      # Deal with boundary cases. If p_hat falls along the 
      # edge of the grid, recompute with p_hat as center. FIXME
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
  if N < 2: # Number of pulse combinations
    return []

  P = []
  for i in range(resamples):
    splines = {}
    for id in site_ids:
      j = random.randint(0, len(pos.sub_splines[id])-1)
      splines[id] = pos.sub_splines[id][j]
    (p, _) = compute_position(sites, splines, pos.p, obj,
              s=POS_EST_S, m=POS_EST_M-1, n=POS_EST_N, delta=POS_EST_DELTA) 
    P.append(p)
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

