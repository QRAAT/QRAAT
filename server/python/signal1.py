# signal1.py -- Represent signal data in the databse, compute bearing 
# likelihoods. This file is part of QRAAT, an automated animal tracking
# system. 
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
# TODO Update SteeringVectors to handle arbitrary bearing sets. 
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

import util

import multiprocessing
import functools
import numpy as np
from scipy.special import iv as I # Modified Bessel of the first kind.
from scipy.optimize import fmin   # Downhill simplex minimization algorithm. 
from scipy.interpolate import InterpolatedUnivariateSpline as spline1d
    
num_ch = 4
two_pi = 2 * np.pi
pi_n = np.pi ** num_ch

### Simulation. ###############################################################

def Simulator(p, sites, sv_splines, rho, sig_n, trials, include=[]): 
  ''' Generate a number of signal recordings based on signal model. 
  
    p -- Location of transmitter. 

    sites -- A map of site_ids to locations of receivers. 

    sv_splines -- Interpolation of in-phase and quadrature combponents of the 
                  steering vector channels. 

    rho -- Transmission power. 

    sig_n -- Signal noise. 

    trials -- Number of recordings to generate per site. 

    include -- Sites to generate signals from. If this array is empty, then all 
               sites in ``sites`` are included. 
  ''' 
 
  # Elements of noise vector are modelled as independent, identically
  # distributed, circularly-symmetric complex normal random varibles. 
  mu_n =  np.complex(0,0)
  mean_n = np.array([mu_n.real, mu_n.imag])
  cov_n = 0.5 * np.array([[sig_n.real, sig_n.imag],
                        [sig_n.imag, sig_n.real]])
    
  # Noise covariance matrix. 
  Sigma = np.matrix(np.zeros((4,4), dtype=np.complex))
  np.fill_diagonal(Sigma, sig_n)
  
  # Signal power.
  edsp = rho**2 
  tnp = np.trace(Sigma)

  sig = Signal()
    
  sig.t_start = 0
  sig.t_end = trials

  if include == []: 
    include = sites.keys()
 
  # Scale transmission coefficients to rho. The transmission power degrades 
  # with distance according to the inverse-square law well-known in radio 
  # engineering.  
  T = {}
  for id in include:
    T[id] = np.sqrt(rho / (np.abs(p - sites[id]) ** 2))

  # Generate a signal for each site. 
  for id in include:
    bearing = np.angle(p - sites[id]) * 180 / np.pi
    
    # Compute modelled steering vector for DOA. 
    G = np.zeros(num_ch, dtype=np.complex)
    for i in range(num_ch):
      (I, Q) = sv_splines[id][i]
      G[i] = np.complex(I(bearing), Q(bearing))
    
    sig.table[id] = _per_site_data(id)
    sig.table[id].count = trials

    V = []; timestamps = []; est_ids = []
    for i in range(trials):
      timestamps.append(i)
      est_ids.append(i)

      # Generate noise vector. 
      N = np.array(map(lambda(x) : np.complex(x[0], x[1]), 
            np.random.multivariate_normal(mean_n, cov_n, num_ch)))

      # Modelled signal. 
      V.append((T[id] * G) + N) 
    
    sig.table[id].est_ids = np.array(est_ids)
    sig.table[id].t = np.array(timestamps)
    sig.table[id].signal_vector = np.array(V)
    sig.table[id].tnp = np.array([tnp] * trials)
    sig.table[id].edsp = np.array([edsp] * trials)
    sig.table[id].noise_cov = np.array([Sigma] * trials)

  return sig


def compute_bearing_splines(sv):
  ''' Interpolate steering vectors. ''' 
  x = np.arange(-360,360)
  splines = {}
  for (id, G) in sv.steering_vectors.iteritems():
    splines[id] = []
    for i in range(num_ch):
      y = np.array(G)[:,i]; 
      y = np.hstack((y,y))
      I = spline1d(x, np.real(y)) # In-phase
      Q = spline1d(x, np.imag(y)) # Quadrature
      splines[id].append((I, Q)) 
  return splines
      

def scale_tx_coeff(p, rho, sites, include=[]):
  ''' Scale transmission power to nearest site.
  
    Fix the transmission power so that the transmission coefficient at 
    the nearest site in ``include`` is 1. 
  '''
  if include == []: 
    include = sites.keys()
  nearest_id = include[0]
  for id in include: 
    if np.abs(p - sites[id]) < np.abs(p - sites[nearest_id]): 
      nearest_id = id
  scaled_rho = (rho * np.abs(p - sites[nearest_id]))**2
  return scaled_rho  



### class SteeringVectors. ####################################################

class SteeringVectors:
  
  suffix = 'csv'
  delim = ','

  def __init__(self, db_con=None, cal_id=None, include=[]):

    ''' Represent steering vectors.
      
      The bearings and their corresponding steering vectors are stored in 
      dictionaries indexed by site ID. This class also stores provenance 
      information for direction-of-arrival and position estimation. Note 
      that it is implicitly assumed in the code that there are steering 
      vectors for whole-degree bearings (0, 1, ... 359). 

      Inputs:
          
        db_con -- Interface to the database. 

        cal_id -- Calibration ID, identifies the set of steering vectors to 
                  use for direction-of-arrival and position estimation. 

        include -- Sites to include. If this is empty, use all sites in the 
                   table `qraat.site`. 
    ''' 

    # Get steering vector data.
    self.steering_vectors = {} # site.ID -> sv
    self.bearings = {}         # site.ID -> bearing
    self.sv_id = {}            # site.ID -> steering_vectors.ID
    self.cal_id = cal_id

    if db_con:
      to_be_removed = []
      self.cal_id = cal_id
      cur = db_con.cursor()
      if include == []: 
        include = util.get_sites(db_con).keys()
      for site_id in include:
        cur.execute('''SELECT ID, Bearing,
                              sv1r, sv1i, sv2r, sv2i,
                              sv3r, sv3i, sv4r, sv4i
                         FROM steering_vectors
                        WHERE SiteID=%s and Cal_InfoID=%s
                     ORDER BY Bearing''', (site_id, cal_id))
        raw_data = cur.fetchall()
        sv_data = np.array(raw_data,dtype=float)
        if sv_data.shape[0] > 0:
          self.steering_vectors[site_id] = np.array(sv_data[:,2::2] + np.complex(0,1) * sv_data[:,3::2])
          self.bearings[site_id] = np.array(sv_data[:,1])
          self.sv_id[site_id] = np.array(sv_data[:,0], dtype=int)
        else:
          to_be_removed.append(site)
      while len(to_be_removed) > 0:
        self.sites.table.remove(to_be_removed.pop())


  def write(self, suffix='sv'):
    fn = '%s%s.%s' % (suffix, self.cal_id, self.suffix)
    fd = open(fn, 'w')

    header = ['site_id', 'id', 'bearing']
    for i in range(num_ch): header.append('sv%d' % (i+1))
    fd.write(self.delim.join(header) + '\n')
    
    for (site_id, sv) in self.steering_vectors.iteritems():
      for i in range(sv.shape[0]):
        line = [site_id, self.sv_id[site_id][i], self.bearings[site_id][i]] 
        line += list(sv[i])
        fd.write(self.delim.join(map(lambda x: str(x), line)) + '\n')
   

  @classmethod
  def read(cls, cal_id, prefix='sv'):
    sv = cls()
    fn = '%s%s.%s' % (prefix, cal_id, sv.suffix)
    fd = open(fn, 'r')

    header = fd.readline()
    for line in fd.readlines():
      row = line.split(sv.delim)
      site_id = int(row[0])
      if sv.steering_vectors.get(site_id) is None:
        sv.steering_vectors[site_id] = []
        sv.bearings[site_id] = []
        sv.sv_id[site_id] = []
        
      sv.sv_id[site_id].append(int(row[1]))
      sv.bearings[site_id].append(float(row[2]))
      sv.steering_vectors[site_id].append(map(lambda x: np.complex(x), row[3:]))
    return sv
  


### class Signal. #############################################################

class Signal:

  def __init__(self, db_con=None, dep_id=None, t_start=0, t_end=0, 
               score_threshold=None, exclude=[]):
   
    ''' Represent signals in the `qraat.est` table.
    
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
    self.t_start = float("+inf")
    self.t_end =   float("-inf")
    
    if db_con: 
      cur = db_con.cursor()
      if score_threshold is not None: 
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
      else:
        ct = cur.execute('''SELECT ID, siteID, timestamp, edsp, 
                                   ed1r,  ed1i,  ed2r,  ed2i,  
                                   ed3r,  ed3i,  ed4r,  ed4i, tnp,
                                   nc11r, nc11i, nc12r, nc12i, nc13r, nc13i, nc14r, nc14i, 
                                   nc21r, nc21i, nc22r, nc22i, nc23r, nc23i, nc24r, nc24i, 
                                   nc31r, nc31i, nc32r, nc32i, nc33r, nc33i, nc34r, nc34i, 
                                   nc41r, nc41i, nc42r, nc42i, nc43r, nc43i, nc44r, nc44i 
                              FROM est
                             WHERE deploymentID= %s
                               AND timestamp >= %s 
                               AND timestamp <= %s
                             ORDER BY timestamp''', 
                  (dep_id, t_start, t_end))
   
      if ct > 0:
        raw_data = np.array(cur.fetchall(), dtype=float)
        est_ids = np.array(raw_data[:,0], dtype=int)
        self.max_est_id = np.max(est_ids)
        include = np.array(raw_data[:,1], dtype=int)
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

        for site_id in set(include).difference(set(exclude)):
          site = _per_site_data(site_id)
          site.est_ids = est_ids[include == site_id]
          site.t = timestamps[include == site_id]
          site.edsp = edsp[include == site_id] # a.k.a. power
          site.signal_vector = signal_vector[include == site_id]
          site.tnp = tnp[include == site_id]
          site.noise_cov = noise_cov[include == site_id]
          site.count = np.sum(include == site_id)
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

  def write(self):
    for (id, site) in self.table.iteritems():
      site.write()

  @classmethod
  def read(cls, site_ids, prefix='sig'):
    sig = cls()
    for id in site_ids:  
      sig.table[id] = _per_site_data(id)
      sig.table[id].read(prefix)
      sig.t_start = min(sig.t_start, 
                        min(sig.table[id].t))
      sig.t_end = max(sig.t_end, 
                      max(sig.table[id].t))
    return sig

  def estimate_var(self): 
    sig_t = {}; sig_n = {}
    for (site_id, site) in self.table.iteritems():
      A = []; B = []
      for (id, t, edsp, ed, nc) in site:
        tr = np.trace(nc) #np.real(np.trace(nc))
        A.append(edsp - tr)   # sig_t 
        B.append(tr / num_ch) # sig_n
      sig_t[site_id] = (np.mean(A), np.std(A))
      sig_n[site_id] = (np.mean(B), np.std(B))
    return (sig_n, sig_t)

  def get_site_ids(self):
    ''' Return a list of site ID's. ''' 
    return self.table.keys()

  @classmethod
  def MLE(self, per_site_data, sv):
    assert isinstance(per_site_data, _per_site_data)
    return (per_site_data.mle(sv), np.argmax)

  @classmethod
  def Bartlet(self, per_site_data, sv):
    assert isinstance(per_site_data, _per_site_data)
    return (per_site_data.bartlet(sv), np.argmax)

  
def _mle(V, G, edsp, noise_cov, ct, j): 
  ''' Parallelizable MLE bearing spectrum computation. 
    
    See ``_per_site_data.mle()``. 
  '''
  p = np.zeros(ct, dtype=np.float)
  G = np.matrix(G[j]).transpose()
  G = np.dot(G, np.conj(np.transpose(G)))
  for i in range(ct):
    R = (edsp[i] * G) + noise_cov[i] 
    det = np.abs(np.linalg.det(R))
    R = np.linalg.inv(R)
    a = np.dot(np.transpose(np.conj(np.transpose(V[i]))), 
                   np.dot(R, np.transpose(V[i])))
    p[i] = -np.log(det * pi_n) - np.abs(a.flat[0])
  return p


class _per_site_data: 
  
  suffix = 'csv'
  delim = ','

  def __init__(self, site_id):
  
    ''' Per site signal object, methods for direction-of-arrival estimation. 
    
      Data are stored in time-ordered arrays. Likelihoods for DOA are computed
      for whole-degree bearings. The result is a matrix with as many rows as
      there are pulses and 360 columns. 
    
      site_id -- identifies a site in the DB. 
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

  def __iter__(self): 
    for i in range(self.count):
      yield (self.est_ids[i], self.t[i], self.edsp[i],
             self.signal_vector[i], self.noise_cov[i])

  def read(self, prefix):
    fn = '%s%d.%s' % (prefix, self.site_id, self.suffix)
    fd = open(fn, 'r')
    
    id = []; t = []; edsp = []
    tnp = []; ed = []; nc = []
    header = fd.readline()
    for line in fd.readlines():
      row = line.split(self.delim)
      id.append(int(row[0]))
      t.append(float(row[1]))
      edsp.append(float(row[2]))
      tnp.append(float(row[3]))
      ed.append(map(lambda x : np.complex(x), row[4:4+num_ch]))
      nc.append(map(lambda x : np.complex(x), row[4+num_ch:]))
    self.count = len(id)
    self.est_ids = np.array(id)
    self.t = np.array(t)
    self.edsp = np.array(edsp)
    self.tnp = np.array(tnp)
    self.signal_vector = np.array(ed)
    self.noise_cov = np.array(nc).reshape((self.count, num_ch, num_ch))

  def write(self, suffix='sig'):
    fn = '%s%d.%s' % (suffix, self.site_id, self.suffix)
    fd = open(fn, 'w')
    
    header = ['id', 't', 'edsp', 'tnp'] 
    for i in range(num_ch): header.append('ed%d' % (i+1))
    for i in range(num_ch): 
      for j in range(num_ch): 
        header.append('nc%d%d' % (i+1, j+1))
    fd.write(self.delim.join(header) + '\n')

    for (id, t, edsp, tnp, ed, nc) in zip(self.est_ids.tolist(), 
                                          self.t.tolist(), 
                                          self.edsp.tolist(),
                                          self.tnp.tolist(),
                                          self.signal_vector.tolist(),
                                          list(self.noise_cov)):
      row = [id, t, edsp, tnp] + ed + list(nc.flat)
      fd.write(self.delim.join(map(lambda x: str(x), row)) + '\n')
  
  def mle(self, sv): 
    ''' ML estimator for DOA given the model. Use `argmax`. 
      
      Compute ln(f(V | theta)). The Hermation operator, as in $V^H$ or 
      $G_i(\theta)^H in the equations, is written here as 
      `np.conj(np.transpose())`. 

      sv -- instance of `class SteeringVectors`.
    ''' 
    # FIXME Test to see if this crashes. 
    f = functools.partial(_mle, np.matrix(self.signal_vector), 
                                sv.steering_vectors[self.site_id],
                                self.edsp, self.noise_cov, self.count)
    p = np.zeros((self.count, 360), dtype=np.float64)
    for j in range(360):
      p[:,j] = f(j)
    return p

  def bartlet(self, sv): 
    ''' Bartlet's estimator for DOA. Use `argmax`. ''' 
    V = self.signal_vector 
    G = sv.steering_vectors[self.site_id] 
    self.bearing = sv.bearings[self.site_id]
    left_half = np.dot(V, np.conj(np.transpose(G))) 
    return np.real(left_half * np.conj(left_half)) 



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


