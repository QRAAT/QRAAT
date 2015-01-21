# position1.py -- Working on clean, succinct positiion estimator code. 
#
# class SteeringVectors -- represent steering vectors in the database.
#
# class Signal -- represent signal data in the database. 
#
# class GeneralizedVonMises -- represents a bimodal von Mises distribution. You
# can completely ignore this. The method and the maximum ikelihood estimator in 
# particular are due to [GJ06]. 
#
# class Bearing -- represent bearings in the database. 
#
#  [GJ06] Riccardo Gatto, Sreenivasa Rao Jammalamadaka. "The generalized 
#         von Mises distribution." In Statistical Methodology, 2006. 
#
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

import qraat
import util

import sys
import numpy as np
import matplotlib.pyplot as pp
from scipy.special import iv as I # Modified Bessel of the first kind.
from scipy.optimize import fmin   # Downhill simplex minimization algorithm. 
from scipy.interpolate import InterpolatedUnivariateSpline as spline1d
import utm

num_ch = 4
two_pi = 2 * np.pi
pi_n = np.pi ** num_ch


### class SteeringVectors. ####################################################

class SteeringVectors:
  
  def __init__(self, db_con, cal_id):

    ''' Represent steering vectors ($G_i(\theta)$).
      
      The bearings and their corresponding steering vectors are stored in 
      dictionaries indexed by site ID. This class also stores provenance 
      information for direction-of-arrival and position estimation. Note 
      that it is implicitly assumed in the code that there are steering 
      vectors for exactly 360 distinct bearings for each site. 

      Inputs:
          
        db_con -- Interface to the database. 

        cal_id -- Calibration ID, identifies the set of steering vectors to 
                  use for direction-of-arrival and position estimation. 
    ''' 

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



### class Signal. #############################################################

class Signal:

  def __init__(self, db_con, dep_id, t_start, t_end, score_threshold=0):
   
    ''' Represent signals in the `qraat.est` table ($V$, $\Sigma$, $sigma$).
    
      Store data in a dictionary mapping sites to time-indexed signal data. 
      The relevant data are the eigenvalue decomposition of the signal (ed1r, 
      ed1i, ... ed4r, ed4i), the noise covariance matrix (nc11r, nc11i, ... 
      nc44r, nc44i), and the signal power (edsp). Each pulse is assigned
      an ID (est_id). Time is represented in seconds as a floating point 
      number (timestamp). 

      Inputs: 

        db_con -- an interface to the database. 

        dep_id -- deployment ID, identifies a target/transmitter. 

        t_start, t_end -- time range of query set. 

        score_threshold -- Signals are given scores based on how likely we 
                           think they are real signals and not just noise. 
    '''

    self.table = {}
    cur = db_con.cursor()
    ct = cur.execute('''SELECT ID, siteID, timestamp, edsp, 
                               ed1r,  ed1i,  ed2r,  ed2i,  
                               ed3r,  ed3i,  ed4r,  ed4i, tnp,
                               nc11r, nc11i, nc12r, nc12i, nc13r, nc13i, nc14r, nc14i, 
                               nc21r, nc21i, nc22r, nc22i, nc23r, nc23i, nc24r, nc24i, 
                               nc31r, nc31i, nc32r, nc32i, nc33r, nc33i, nc34r, nc34i, 
                               nc41r, nc41i, nc42r, nc42i, nc43r, nc43i, nc44r, nc44i 
                          FROM est
                          JOIN estscore ON est.ID = estscore.estID
                         WHERE deploymentID= %s
                           AND timestamp >= %s 
                           AND timestamp <= %s
                           AND (score / theoretical_score) >= %s
                         ORDER BY timestamp''', 
              (dep_id, t_start, t_end, score_threshold))
 
    if ct:
      raw_data = np.array(cur.fetchall(), dtype=float)
      est_ids = np.array(raw_data[:,0], dtype=int)
      self.max_est_id = np.max(est_ids)
      site_ids = np.array(raw_data[:,1], dtype=int)
      timestamps = raw_data[:,2]
      edsp = raw_data[:,3]
      signal_vector = np.zeros((raw_data.shape[0], num_ch),dtype=np.complex)
      for j in range(num_ch):
        signal_vector[:,j] = raw_data[:,2*j+4] + np.complex(0,-1)*raw_data[:,2*j+5]

      tnp = raw_data[:,12]
      noise_cov = np.zeros((raw_data.shape[0],num_ch,num_ch),dtype=np.complex)
      for t in range(raw_data.shape[0]):      
        for i in range(num_ch):
          for j in range(num_ch):
            k = 13 + (i*num_ch*2) + (2*j)
            noise_cov[t,i,j] = np.complex(raw_data[t,k], raw_data[t,k+1])

      for site_id in set(site_ids):
        site = _per_site_data(site_id)
        site.est_ids = est_ids[site_ids == site_id]
        site.t = timestamps[site_ids == site_id]
        site.edsp = edsp[site_ids == site_id] # a.k.a. power
        site.signal_vector = signal_vector[site_ids == site_id]
        site.tnp = tnp[site_ids == site_id]
        site.noise_cov = noise_cov[site_ids == site_id]
        site.count = np.sum(site_ids == site_id)
        self.table[site_id] = site

      self.t_start = np.min(timestamps)
      self.t_end = np.max(timestamps)
  
  def __getitem__(self, *index):
    if len(index) == 1: 
      return self.table[index[0]] # Access a site
    elif len(index) > 1 and index[1] in ['t', 'power', 'signal_vector', 'est_ids']: 
      if len(index) == 2: # Access a data array for a site
        return self.table[index[0]].getattr(index[1])
      elif len(index) == 3: # Access a row of a data array for a site
        return self.table[index[0]].getattr(index[1])[index[2]]
    return None

  def __len__(self):
    return len(self.table)

  def get_site_ids(self):
    ''' Return a list of site ID's. ''' 
    return self.table.keys()

  @classmethod
  def MLE(self, per_site_data, sv):
    assert isinstance(per_site_data, _per_site_data)
    return per_site_data.MLE(sv)
  
  @classmethod
  def Bartlet(self, per_site_data, sv):
    assert isinstance(per_site_data, _per_site_data)
    return per_site_data.Bartlet(sv)


class _per_site_data: 

  def __init__(self, site_id):
  
    ''' Per site signal object, methods for direction-of-arrival estimation. 
    
      Data are stored in time-ordered arrays. Likelihoods for DOA are computed
      for whole-degree bearings. The result is a matrix with as many rows as
      there are pulses and 360 columns. 
    
      Input: site_id -- identifies a site in the DB. 
    ''' 

    self.site_id = site_id     # Site ID
    self.est_ids = None        # Signal (pulse) ID's
    self.t = None              # timestamps (in seconds) 
    self.tnp = None            # Total noise power
    self.edsp = None           # eigenvalue decomposition signal power
    self.signal_vector = None  # eigenvalue decomposition of signal 
    self.noise_cov = None      # noise covariance matrix
    self.count = 0             # Number of signals (pulses)
    
  def __len__(self):
    return self.count

  def p(self, sv): 
    ''' Compute p(V | theta) in the signal model.  
    
      The Hermation operator, as in $V^H$ or $G_i(\theta)^H in the equations, 
      is written here as `np.conj(np.transpose())`. 

      Input: sv -- instance of `class SteeringVectors`.
    ''' 
    p = np.zeros((self.count, 360), dtype=np.float)
    V = np.matrix(self.signal_vector)
    for j in range(360):
      G = np.matrix(sv.steering_vectors[self.site_id][j]).transpose()
      G = np.dot(G, np.conj(np.transpose(G)))
      for i in range(self.count):
        R = G + (self.noise_cov[i] / self.edsp[i])
        det = np.abs(np.linalg.det(R))
        R = np.linalg.inv(R)
        a = np.dot(np.transpose(np.conj(np.transpose(V[i]))), 
                       np.dot(R, np.transpose(V[i])))
        p[i,j] = np.exp(-np.abs(a.flat[0])) / (det * pi_n)
    return p

  def MLE(self, sv):
    ''' ML estimator for DOA given the model. Use `argmin`. '''
    p = np.zeros((self.count, 360), dtype=np.float)
    V = np.matrix(self.signal_vector)
    for j in range(360):
      G = np.matrix(sv.steering_vectors[self.site_id][j]).transpose()
      G = np.dot(G, np.conj(np.transpose(G)))
      for i in range(self.count):
        R = G + (self.noise_cov[i] / self.edsp[i])
        det = np.abs(np.linalg.det(R))
        R = np.linalg.inv(R)
        a = np.dot(np.transpose(np.conj(np.transpose(V[i]))), 
                       np.dot(R, np.transpose(V[i])))
        p[i,j] = np.abs(a.flat[0]) + np.log(det) 
    return p

  def Bartlet(self, sv): 
    ''' Bartlet's estimator for DOA. Use `argmax`. ''' 
    V = self.signal_vector 
    G = sv.steering_vectors[self.site_id] 
    self.bearing = sv.bearings[self.site_id]
    left_half = np.dot(V, np.conj(np.transpose(G))) 
    return np.real(left_half * np.conj(left_half)) 


### Position estimation. ######################################################

def PositionEstimator(sites, center, signal, sv, method=Signal.Bartlet):
  ''' Estimate the source of a signal. 
  
    Inputs: 
      
      sites -- a set of site locations represented in UTM easting/northing 
               as an `np.complex`. The imaginary component is easting and 
               the real part is northing.

      center -- initial guess of position, represented in UTM as an `np.complex`. 
                A good value would be the centroid of the sites.  

      signal -- instance of `class Signal`, signal data. 

      sv -- instance of `class SteeringVectors`, calibration data. 

      method -- Specify method for computing bearing likelihood distribution.

    Returns UTM position estimate as a complex number. 
  ''' 
  if method == Signal.Bartlet: obj = np.argmax
  elif method == Signal.MLE:   obj = np.argmin
  else: obj = np.argmax

  splines = {}
  for site_id in signal.get_site_ids():
    l = aggregate_bearing(method(signal[site_id], sv))
    splines[site_id] = compute_bearing_spline(l)
 
  if len(splines) > 1: # Need at least two site bearings. 
    p_hat, likelihood = compute_position(sites, splines, center, obj, half_span=15)
    return p_hat
  
  else: return None


def WindowedPositionEstimator(sites, center, signal, sv, t_step, t_win, 
                              method=Signal.Bartlet):
  ''' Estimate the source of a signal, aggregate site data. 
  
    Inputs: 
    
      sites, center, signal, sv
      
      t_step, t_win -- time step and window respectively. A position 
                       is computed for each timestep. 

    Returns a sequence of UTM positions. 
  ''' 
  if method == Signal.Bartlet: obj = np.argmax
  elif method == Signal.MLE:   obj = np.argmin
  else: obj = np.argmax
  
  positions = []

  A = {} # Precomputed bearing likelihoods. 
  for site_id in signal.get_site_ids():
    A[site_id] = method(signal[site_id], sv)
  
  for (t_start, t_end) in util.compute_time_windows(
                      signal.t_start, signal.t_end, t_step, t_win):
    
    # Aggregate site data, compute splines for pos. estimation. 
    num_est = 0
    splines = {}  
    activity = {}
    bearing = {}
    for (id, L) in A.iteritems():
      mask = (t_start <= signal[id].t) & (signal[id].t < t_end)
      edsp = signal[id].edsp[mask]
      if edsp.shape[0] > 0:
        l = aggregate_bearing(L[mask])
        splines[id] = compute_bearing_spline(l)
        activity[id] = (np.sum((edsp - np.mean(edsp))**2)**0.5)/np.sum(edsp)
        theta = obj(l); bearing[id] = (theta, l[theta])
        num_est += edsp.shape[0]
   
    if len(splines) > 1: # Need at lesat two site bearings.
      p_hat, likelihood = compute_position(sites, splines, center, obj, half_span=15)
    else: p_hat, likelihood = None, None
      
    t = (t_end + t_start) / 2
    positions.append((p_hat,       # pos. estimate
                      t,           # middle of time window 
                      likelihood,  # likelihood of pos. esstimate
                      num_est,     # total pulses used in calculation
                      bearing,     # siteID -> (theta, likelihood)
                      activity))   # siteID -> activity
  
  return positions


def InsertPositions(db_con, dep_id, positions, zone):
  ''' Insert positions into database. ''' 
  cur = db_con.cursor()
  number, letter = zone
  max_id = 0
  for (pos, t, likelihood, num_est, bearing, activity) in positions:
    if pos is None: 
      continue
    lat, lon = utm.to_latlon(pos.imag, pos.real, number, letter)
    cur.execute('''INSERT INTO position
                     (deploymentID, timestamp, latitude, longitude, easting, northing, 
                      utm_zone_number, utm_zone_letter, likelihood, 
                      activity, number_est_used)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                     (dep_id, t, round(lat,6), round(lon,6),
                      pos.imag, pos.real, number, letter, 
                      likelihood / len(activity), 
                      np.mean(activity.values()), num_est))
    max_id = max(cur.lastrowid, max_id)

  return max_id


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


def compute_position(sites, splines, center, obj, half_span=15): 
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

    # Generate a grid of positions with p_hat at the center. 
    positions = np.zeros((half_span*2+1, half_span*2+1),np.complex)
    for e in range(-half_span,half_span+1):
      for n in range(-half_span,half_span+1):
        positions[e + half_span, n + half_span] = p_hat + np.complex(n * scale, e * scale)

    # Compute the likelihood of each position as the sum of the likelihoods 
    # of bearing to each site. 
    likelihoods = np.zeros(positions.shape, dtype=float)
    for id in splines.keys():
      bearing_to_positions = np.angle(positions - sites[id]) * 180 / np.pi
      likelihoods += splines[id](bearing_to_positions.flat).reshape(bearing_to_positions.shape)
    
    index = obj(likelihoods)
    p_hat = positions.flat[index]
    likelihood = likelihoods.flat[index]
    scale /= 10

  return p_hat, likelihood




### class GeneralizedVonMises. ################################################

class GeneralizedVonMises: 
  
  def __init__(self, mu1, mu2, kappa1, kappa2):
  
    ''' Bimodal von Mises distribution.
  
      Compute a probability density function from the bimodal von Mises 
      distribution paramterized by `mu1` and `mu2`, the peaks of the two 
      humps, and `kappa1` and `kappa2`, the "spread" of `mu1` and `mu2`
      resp., the concentration parameters. 
    ''' 
    
    assert 0 <= mu1 and mu1 < two_pi
    assert 0 <= mu2 and mu2 < two_pi
    assert kappa1 >= 0
    assert kappa2 >= 0 

    self.mu1    = mu1
    self.mu2    = mu2
    self.kappa1 = kappa1
    self.kappa2 = kappa2

    delta = (mu1 - mu2) % np.pi
    G0 = self.normalizingFactor(delta, kappa1, kappa2, rounds=100)
    self.denom = 2 * np.pi * G0

  def __call__(self, theta):
    ''' Evaluate the probability density function at `theta`. ''' 
    num =  np.exp(self.kappa1 * np.cos(theta - self.mu1) + \
                  self.kappa2 * np.cos(2 * (theta - self.mu2))) 
    return num / self.denom

  @classmethod
  def normalizingFactor(cls, delta, kappa1, kappa2, rounds=10):
    ''' Compute the GvM normalizing factor. ''' 
    G0 = 0.0 
    for j in range(1,rounds):
      G0 += I(2*j, kappa1) * I(j, kappa2) * np.cos(2 * j * delta)
    G0 = (G0 * 2) + (I(0,kappa1) * I(0,kappa2))
    return G0

  @classmethod 
  def mle(cls, bearings):
    ''' Maximum likelihood estimator for the von Mises distribution. 
      
      Find the most likely parameters for the set of bearing observations
      `bearings` and return an instance of this class. A generalized von
      Mises distribution can be represented in canonical form as a member
      of the exponential family. This yields a maximul likelihood estimator.
      The Simplex algorithm is used to solve the system.
    '''
    
    n = len(bearings)

    T = np.array([0,0,0,0], dtype=np.float128)
    for theta in bearings:
      T += np.array([np.cos(theta),     np.sin(theta),
                     np.cos(2 * theta), np.sin(2 * theta)], dtype=np.float128)

    def l(u1, u2, k1, k2) :
          
       return np.dot(np.array([k1 * np.cos(u1),     k1 * np.sin(u1), 
                               k2 * np.cos(2 * u2), k2 * np.sin(2 * u2)], 
                         dtype=np.float128), 
                           
                 T) - (n * (np.log(two_pi) + np.log(
                  cls.normalizingFactor((u1 - u2) % np.pi, 
                                        k1, k2, rounds=10))))

    obj = lambda(x) : -l(x[0], x[1], np.exp(x[2]), np.exp(x[3]))

    x = fmin(obj, np.array([0,0,0,0], dtype=np.float128),
             ftol=0.001, disp=False)
    
    x[0] %= two_pi
    x[1] %= two_pi
    x[2] = np.exp(x[2])
    x[3] = np.exp(x[3])
    return cls(*x)


### class Bearing. ############################################################

class Bearing:
  
  def __init__(self, db_con, dep_id, t_start, t_end):
    
    ''' Represent bearings stored in the `qraat.bearing` table. ''' 
   
    self.length = None
    self.max_id = -1
    self.dep_id = dep_id
    self.table = {}
    cur = db_con.cursor()
    cur.execute('''SELECT siteID, ID, timestamp, bearing, likelihood, activity
                     FROM bearing
                    WHERE deploymentID = %s
                      AND timestamp >= %s
                      AND timestamp <= %s
                    ORDER BY timestamp ASC''', (dep_id, t_start, t_end))
    for row in cur.fetchall():
      site_id = int(row[0])
      row = (int(row[1]), float(row[2]), 
             float(row[3]), float(row[4]), float(row[5]))
      if self.table.get(site_id) is None:
        self.table[site_id] = [row]
      else: self.table[site_id].append(row)
      if row[0] > self.max_id: 
        self.max_id = row[0]

  def __len__(self):
    if self.length is None:
      self.length = sum(map(lambda(table): len(table), self.table.values()))
    return self.length

  def __getitem__(self, *index):
    if len(index) == 1: 
      return self.table[index[0]]
    elif len(index) == 2:
      return self.table[index[0]][index[1]]
    elif len(index) == 3:
      return self.table[index[0]][index[1]][index[2]]
    else: return None
  
  def get_sites(self):
    return self.table.keys()

  def get_bearings(self, site_id):
    return map(lambda(row) : (row[2] * np.pi) / 180, self.table[site_id])

  def get_max_id(self): 
    return self.max_id






### Testing, testing ... ######################################################

def test_exp():
  
  # von Mises
  mu1 = 0;      mu2 = 1
  kappa1 = 0.8; kappa2 = 3
  p = GeneralizedVonMises(mu1, mu2, kappa1, kappa2)

  # Exponential representation
  def yeah(theta, u1, u2, k1, k2):
      l = np.array([k1 * np.cos(u1),     k1 * np.sin(u1),      
                    k2 * np.cos(2 * u2), k2 * np.sin(2 * u2)])
      T = np.array([np.cos(theta),    np.sin(theta),
                    np.cos(2 * theta), np.sin(2 * theta)])
      G0 = GeneralizedVonMises.normalizingFactor((u1 - u2) % np.pi, k1, k2)
      K = np.log(2*np.pi) + np.log(G0)
      return np.exp(np.dot(l, T) - K) 
          
  f = lambda(x) : yeah(x, mu1, mu2, kappa1, kappa2)

  fig, ax = pp.subplots(1, 1)
  
  # Plot most likely distribution.
  x = np.arange(0, 2*np.pi, np.pi / 180)
  print np.sum(p(x) * (np.pi / 180))
  pp.xlim([0,2*np.pi])
  ax.plot(x, f(x), 'r-', lw=10, alpha=0.25, label='Exponential representation')
  ax.plot(x, p(x), 'k-', lw=1, 
    label='$\mu_1=%.2f$, $\mu_2=%.2f$, $\kappa_1=%.2f$, $\kappa_2=%.2f$' % (
             mu1, mu2, kappa1, kappa2))
  
  ax.legend(loc='best', frameon=False)
  pp.show()


def test_mle():

  # Generate a noisy bearing distribution "sample".  
  mu1 = 0;      mu2 = 1
  kappa1 = 0.8; kappa2 = 3
  P = GeneralizedVonMises(mu1, mu2, kappa1, kappa2)
  
  theta = np.arange(0, 2*np.pi, np.pi / 30)
  prob = P(theta) + np.random.uniform(-0.1, 0.1, 60)
  bearings = []
  for (a, b) in zip(theta, prob):
    bearings += [ a for i in range(int(b * 100)) ]

  # Find most likely parameters for a von Mises distribution
  # fit to (theta, prob). 
  p = GeneralizedVonMises.mle(bearings)

  # Plot observation.
  fig, ax = pp.subplots(1, 1)
  N = 50
  n, bins, patches = ax.hist(bearings, 
                             bins = [ (i * 2 * np.pi) / N for i in range(N) ],
                             normed=1.0,
                             facecolor='blue', alpha=0.25)
 
  # Plot most likely distribution.
  x = np.arange(0, 2*np.pi, np.pi / 180)
  print np.sum(p(x) * (np.pi / 180))
  pp.xlim([0,2*np.pi])
  ax.plot(x, p(x), 'k-', lw=2, 
    label='$\mu_1=%.2f$, $\mu_2=%.2f$, $\kappa_1=%.2f$, $\kappa_2=%.2f$' % (
             p.mu1, p.mu2, p.kappa1, p.kappa2))
  
  ax.legend(loc='best', frameon=False)
  pp.show()


def test_bearing(): 
  
  cal_id = 3
  dep_id = 105
  t_start = 1407452400 
  t_end = 1407455985 #- (50 * 60)

  db_con = util.get_db('reader')
  sv = position.steering_vectors(db_con, cal_id)
  signal = Signal(db_con, dep_id, t_start, t_end)

  bearings = signal.get_bearings(sv, 3)
  p = GeneralizedVonMises.mle(bearings)

  fig, ax = pp.subplots(1, 1)

  # Plot bearing distribution.
  N = 100
  n, bins, patches = ax.hist(bearings,
                             bins = [ (i * 2 * np.pi) / N for i in range(N) ],
                             normed = 1.0,
                             facecolor='blue', alpha=0.25)

  # Plot fitted vonMises distribution.
  x = np.arange(0, 2*np.pi, np.pi / 180)
  print np.sum(p(x) * (np.pi / 180))
  pp.xlim([0,2*np.pi])
  ax.plot(x, p(x), 'k-', lw=2, 
    label='$\mu_1=%.2f$, $\mu_2=%.2f$, $\kappa_1=%.2f$, $\kappa_2=%.2f$' % (
             p.mu1, p.mu2, p.kappa1, p.kappa2))

  pp.xlim([0,2*np.pi])
  
  ax.legend(loc='best', frameon=False)
  pp.show()


def test1(): 
  
  cal_id = 3
  dep_id = 105
  t_start = 1407452400 
  t_end = 1407455985# - (50 * 60)

  db_con = util.get_db('writer')
  sv = SteeringVectors(db_con, cal_id)
  signal = Signal(db_con, dep_id, t_start, t_end)

  sites = util.get_sites(db_con)
  (center, zone) = util.get_center(db_con)
  assert zone == util.get_utm_zone(db_con)
  
  positions = WindowedPositionEstimator(sites, center, signal, sv, 5, 30,
                                         method=Signal.Bartlet)
  InsertPositions(db_con, dep_id, positions, zone)

if __name__ == '__main__':
  

  #test_exp()
  #test_bearing()
  #test_mle()
  test1()
