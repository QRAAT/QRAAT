# signal.py -- Represetnations of received signals and steering vectors, 
# simulation, and filtering of signals based on parameters and timing. 
#
# High level calls:
#  - Simulator
#  - Filter
# 
# Objects defined here:
#  - class SteeringVectors
#  - class Signal
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

from . import util

import sys
import numpy as np
import functools
from scipy.interpolate import InterpolatedUnivariateSpline as spline1d



### class SteeringVectors. ####################################################

class SteeringVectors:
  
  suffix = 'csv'
  delim = ','

  def __init__(self, *args, **kwargs):
    ''' Represent steering vectors.
      
      The bearings and their corresponding steering vectors are stored in 
      dictionaries indexed by site ID. This class also stores provenance 
      information for direction-of-arrival and position estimation. Note 
      that it is implicitly assumed in the code that there are steering 
      vectors for whole-degree bearings (0, 1, ... 359). 

      If arguments are provided, then `signal.SteeringVectors.read_db()` 
      is called. If `fn` is a keyword argument, then read from file. 
    '''
    self.steering_vectors = {} # site.ID -> sv
    self.bearings = {}         # site.ID -> bearing
    self.sv_id = {}            # site.ID -> steering_vectors.ID
    self.cal_id = None
  
    if len(args) == 2: 
      self.read_db(*args, **kwargs)
   
  def read_db(self, db_con, cal_id, include=[]):
    ''' Read steering vectors from database. 

      Inputs:
          
        db_con -- Interface to the database. 

        cal_id -- Calibration ID, identifies the set of steering vectors to 
                  use for direction-of-arrival and position estimation. 

        include -- Sites to include. If this is empty, use all sites in the 
                   table `qraat.site`. 
    '''

    self.cal_id = cal_id
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

  @classmethod
  def read(cls, cal_id, prefix='sv'):
    ''' Read steering vectors from file. ''' 
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
  
  def write(self, fn):
    ''' Write steering vectors to file. ''' 
    fd = open(fn, 'w')
    header = ['site_id', 'id', 'bearing']
    for i in range(NUM_CHANNELS): header.append('sv%d' % (i+1))
    fd.write(self.delim.join(header) + '\n')
    for (site_id, sv) in self.steering_vectors.iteritems():
      for i in range(sv.shape[0]):
        line = [site_id, self.sv_id[site_id][i], self.bearings[site_id][i]] 
        line += list(sv[i])
        fd.write(self.delim.join(map(lambda x: str(x), line)) + '\n')

  


### class Signal. #############################################################

# Number of input channels on radio receivers.
NUM_CHANNELS = 4 

# Constants for signal model. 
TWO_PI = 2 * np.pi
PI_N = np.pi ** NUM_CHANNELS

class Signal:

  def __init__(self, *args, **kwargs):
    ''' Represent signals in the `qraat.est` table.
    
      Store data in a dictionary mapping sites to time-indexed signal data. 
      The relevant data are the eigenvalue decomposition of the signal (ed1r, 
      ed1i, ... ed4r, ed4i), the noise covariance matrix (nc11r, nc11i, ... 
      nc44r, nc44i), and the signal power (edsp). Each pulse is assigned
      an ID (est_id). Time is represented in seconds as a floating point 
      number (timestamp). 
    '''
    self.table = {}
    self.t_start = float("+inf")
    self.t_end = float("-inf")
    self.max_id = 0

    if len(args) >= 4:
      self.read_db(*args, **kwargs)

  def read_db(self, db_con, dep_id, t_start, t_end,
                score_threshold=None, include=[], exclude=[]):
    ''' Read signals from database. 

      Inputs: 

        db_con -- MySQL database connector

        dep_id -- deploymentID, identifies a target/transmitter. 

        t_start, t_end -- time range of query set represented as 
                          Unix timestamps (GMT). 

        score_threshold -- Signals are given scores based on how likely we 
                           think they are real signals and not just noise. 
    '''
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
      site_ids = np.array(raw_data[:,1], dtype=int)
      timestamps = raw_data[:,2]
      edsp = raw_data[:,3]
      signal_vector = np.zeros((raw_data.shape[0], NUM_CHANNELS),dtype=np.complex)
      for j in range(NUM_CHANNELS):
        signal_vector[:,j] = raw_data[:,2*j+4] + np.complex(0,-1)*raw_data[:,2*j+5]

      tnp = raw_data[:,12]
      noise_cov = np.zeros((raw_data.shape[0],NUM_CHANNELS,NUM_CHANNELS),dtype=np.complex)
      for t in range(raw_data.shape[0]):      
        for i in range(NUM_CHANNELS):
          for j in range(NUM_CHANNELS):
            k = 13 + (i*NUM_CHANNELS*2) + (2*j)
            noise_cov[t,i,j] = np.complex(raw_data[t,k], raw_data[t,k+1])

      if include == []:
        inc = set(site_ids)
      else: 
        inc = set(include)

      for site_id in inc.difference(set(exclude)):
        mask = site_ids == site_id
        site = _per_site_data(site_id)
        site.est_ids = est_ids[mask]
        site.t = timestamps[mask]
        site.edsp = edsp[mask] # a.k.a. power
        site.signal_vector = signal_vector[mask]
        site.tnp = tnp[mask]
        site.noise_cov = noise_cov[mask]
        site.count = len(est_ids)
        self.table[site_id] = site

      self.t_start = np.min(timestamps)
      self.t_end = np.max(timestamps)
      self.max_id = np.max(est_ids)

  @classmethod
  def read(cls, site_ids, prefix='sig'):
    ''' Read signals from files. ''' 
    sig = Signal()
    for id in site_ids:  
      sig.table[id] = _per_site_data(id)
      sig.table[id].read(prefix)
      sig.t_start = min(sig.t_start, 
                        min(sig.table[id].t))
      sig.t_end = max(sig.t_end, 
                      max(sig.table[id].t))
    return sig
  
  def write(self):
    ''' Write signals to files.. ''' 
    for (id, site) in self.table.iteritems():
      site.write()
  
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
    ''' Return number of sites. ''' 
    return len(self.table)

  def get_count(self):
    ''' Return total number pulses across sites. '''
    return sum(map(lambda site_data: site_data.count, self. table.values()))

  def estimate_var(self): 
    ''' Estimate variance paramter of background noise from noise covariance. ''' 
    sig_t = {}; sig_n = {}
    for (site_id, site) in self.table.iteritems():
      A = []; B = []
      for (id, t, edsp, ed, nc) in site:
        tr = np.trace(nc) #np.real(np.trace(nc))
        A.append(edsp - tr)   # sig_t 
        B.append(tr / NUM_CHANNELS) # sig_n
      sig_t[site_id] = (np.mean(A), np.std(A))
      sig_n[site_id] = (np.mean(B), np.std(B))
    return (sig_n, sig_t)

  def get_site_ids(self):
    ''' Return a list of site ID's. ''' 
    return self.table.keys()

  @classmethod
  def MLE(self, per_site_data, sv):
    ''' Compute bearing spectrum of signals with respect to the MLE. '''    
    assert isinstance(per_site_data, _per_site_data)
    return (per_site_data.mle(sv), np.argmax)

  @classmethod
  def Bartlet(self, per_site_data, sv):
    ''' Compute bearing spectrum of signals with respect to Bartlet's estimator. ''' 
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
    p[i] = -np.log(det * PI_N) - np.abs(a.flat[0])
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
      ed.append(map(lambda x : np.complex(x), row[4:4+NUM_CHANNELS]))
      nc.append(map(lambda x : np.complex(x), row[4+NUM_CHANNELS:]))
    self.count = len(id)
    self.est_ids = np.array(id)
    self.t = np.array(t)
    self.edsp = np.array(edsp)
    self.tnp = np.array(tnp)
    self.signal_vector = np.array(ed)
    self.noise_cov = np.array(nc).reshape((self.count, NUM_CHANNELS, NUM_CHANNELS))

  def write(self, suffix='sig'):
    fn = '%s%d.%s' % (suffix, self.site_id, self.suffix)
    fd = open(fn, 'w')
    
    header = ['id', 't', 'edsp', 'tnp'] 
    for i in range(NUM_CHANNELS): header.append('ed%d' % (i+1))
    for i in range(NUM_CHANNELS): 
      for j in range(NUM_CHANNELS): 
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

      Input: 
        
        sv -- instance of `class SteeringVectors`.

      Returns the bearing spectrum. 
    ''' 
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




### Simulator. ################################################################

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
    G = np.zeros(NUM_CHANNELS, dtype=np.complex)
    for i in range(NUM_CHANNELS):
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
            np.random.multivariate_normal(mean_n, cov_n, NUM_CHANNELS)))

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
    for i in range(NUM_CHANNELS):
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




###############################################################################
#                                                                             #
# Signal filter -- This program attempts to remove false positives from the   #
#  pulse data based on the rate at which the transmitter emits pulses.        #
#  Neighboring points are used to coraborate the validity of a given point.   #
#  This is on a per transmitter per site basis; a useful extension to this    #
#  work will be to coroborate points between sites.                           #
#                                                                             #
#  NOTE (duty cycle of RMG module) We don't yet account for the               #
#       percentage of time the system is listening for the transmitter.       #
#       This should be encorpoerated into the theoretical score over the      #
#       pulse's neighborhood.                                                 #
#                                                                             #
###############################################################################

#### Constants and parameters for per site/transmitter pulse filtering. #######

# Burst filter parameters. 
BURST_INTERVAL = 10     # seconds
BURST_THRESHOLD = 20    # pulses/second

# Time filter paramters. These defaults may be overwritten by the calling script.
SCORE_INTERVAL = 60     # seconds
SCORE_NEIGHBORHOOD = 20 # seconds

# Score error for pulse corroboration, as a function of the variation over 
# the interval. (Second moment of the mode pulse interval). These curves were 
# fit to a particular false negative / positive trade-off over a partitioned
# data set. See github.com/qraat/time-filter for details. 

# Results for SCORE_THRESHOLD=0.2. 
#SCORE_ERROR = lambda(x) : (-0.6324 / (x + 7.7640)) + 0.1255 # hyper
#SCORE_ERROR = lambda(x) : 0.02                              # const_low
SCORE_ERROR = lambda(x) : 0.1255                             # const_high

# Minumum percentage of transmitter's nominal pulse interval that the expected
# pulse_interval is allowed to drift. Tiny pulse intervals frequently result 
# from particularly noisy, but it may not be enough to trigger the burst 
# filter.
# Valid range is MIN_DRIFT_PRECENTAGE*Rate to (2-MIN_DRIFT_PRECENTAGE)*Rate
#    or +/- (1-MIN_DRIFT_PERCENTAGE)
MIN_DRIFT_PERCENTAGE = 0.33

# Eliminate noisy intervals. 
MAX_VARIATION = 4


#### System parameters ... these shouldn't be changed. ########################

# Factor by which to multiply timestamps. 
TIMESTAMP_PRECISION = 1000

# Controls the number of bins in histograms. 
BIN_WIDTH = 0.02 

# Some constants. 
PARAM_BAD = -1
BURST_BAD = -2 

# Log output. 
VERBOSE = False



#### High level calls. ########################################################

def debug_output(msg): 
  if VERBOSE: 
    print "signal: %s" % msg


def Filter(db_con, dep_id, t_start, t_end, param_filter=True): 
  
  total = 0; max_id = 0
  tx_params = get_tx_params(db_con, dep_id)
  debug_output("depID=%d parameters: band3=%s, band10=%s, pulse_rate=%s" 
     % (dep_id, 'nil' if tx_params['band3'] == sys.maxint else tx_params['band3'],
                'nil' if tx_params['band10'] == sys.maxint else tx_params['band10'], 
                tx_params['pulse_rate']))
  
  
  cur = db_con.cursor() 
  cur.execute('SELECT ID FROM site')
  sites = map(lambda(row) : row[0], cur.fetchall())


  interval_data = {} # Keep track of pulse rate of each window. 
  for site_id in sites: 
    interval_data[site_id] = []

  for interval in get_score_intervals(t_start, t_end):

    # Using overlapping windows in order to mitigate 
    # score bias on points at the end of the windows. 
    augmented_interval = (interval[0] - (SCORE_NEIGHBORHOOD / 2), 
                          interval[1] + (SCORE_NEIGHBORHOOD / 2))

    data = {}
    for site_id in sites: 
      data[site_id] = get_est_data(db_con, dep_id, site_id, augmented_interval)
        
    no_data = True
    for site_id in sites:
      
      if data[site_id].shape[0] == 0: # Skip empty chunks.
        debug_output("siteID=%s: skipping empty chunk" % site_id)
        continue
      else:
        no_data = False

      debug_output("siteID=%s: processing %.2f to %.2f (%d pulses)" % (site_id,
                                                                       interval[0], 
                                                                       interval[1], 
                                                                       data[site_id].shape[0]))
      
      if param_filter:
        parametric_filter(data[site_id], tx_params)
        
      if data[site_id].shape[0] >= BURST_THRESHOLD: 
        burst_filter(data[site_id], augmented_interval)

    if not no_data:
      (pulse_interval, pulse_variation) = expected_pulse_interval(data, tx_params['pulse_rate'])

    for site_id in sites:

      # The only way to coroborate isolated points is with other sites. 
      if data[site_id].shape[0] > 2 and pulse_interval > 0:
        time_filter(data[site_id], pulse_interval, pulse_variation)
        interval_data[site_id].append((interval[0], float(pulse_interval) / TIMESTAMP_PRECISION, pulse_variation))
      
      # When inserting, exclude overlapping points.
      if data[site_id].shape[0] > 0:
        (count, id) = update_estscore(db_con, 
          data[site_id][(data[site_id][:,2] >= (interval[0] * TIMESTAMP_PRECISION)) * 
                        (data[site_id][:,2] <  (interval[1] * TIMESTAMP_PRECISION))])
        total += count
        max_id = id if max_id < id else max_id
  
  for site_id in sites:
    update_intervals(db_con, dep_id, site_id, interval_data[site_id])
  
  return (total, max_id)





#### Handle pulse data. ####################################################### 

def get_score_intervals(t_start, t_end): 
  ''' Return a list of scoring windows given arbitrary start and finish. '''  
 
  t_start = int(t_start); t_end = int(t_end)+1
  for i in range(t_start - (t_start % SCORE_INTERVAL), 
                 t_end,
                 SCORE_INTERVAL):
    yield (i, i + SCORE_INTERVAL)


def get_est_data(db_con, dep_id, site_id, interval):
  ''' Get pulse data for interval. 
  
    Last columns are for the score and theoretically best score of the
    record. (X[:,5], X[:,6] resp.) Initially, there values are 0. 
  ''' 

  cur = db_con.cursor()
  cur.execute('''SELECT ID, siteID, timestamp, band3, band10, 0, 0, 0  
                   FROM est
                  WHERE deploymentID = %s
                    AND timestamp >= %s
                    AND timestamp < %s
                    AND siteID = %s
                  ORDER BY timestamp''', 
                (dep_id, interval[0], interval[1], site_id,))
 
  data = []
  for row in cur.fetchall():
    data.append(list(row))
    data[-1][2] = int(data[-1][2] * TIMESTAMP_PRECISION)
  
  return np.array(data, dtype=np.int64)


def update_estscore(db_con, data): 
  ''' Insert scored data, updating existng records. 
  
    Return the number of inserted scores and the maximum estID. 
  ''' 
  
  (row, _) = data.shape; 
  inserts = []; deletes = []
  for i in range(row):
    inserts.append((data[i,0], data[i,5], data[i,6], data[i,7]))
    deletes.append(data[i,0])

  cur = db_con.cursor()
  cur.executemany('DELETE FROM estscore WHERE estID = %s', deletes)
  cur.executemany('''INSERT INTO estscore (estID, score, theoretical_score, max_score) 
                            VALUES (%s, %s, %s, %s)''', inserts)

  max_id = np.max(data[:,0]) if len(inserts) > 0 else 0
  return (len(inserts), max_id)


def update_intervals(db_con, dep_id, site_id, intervals):
  ''' Insert interval data for (dep, site). ''' 
  
  if len(intervals) > 0: 

    cur = db_con.cursor()
    cur.execute('''DELETE FROM estinterval 
                    WHERE timestamp >= %s 
                      AND timestamp <= %s
                      AND deploymentID = %s
                      AND siteID = %s''', 
              (intervals[0][0], intervals[-1][0], dep_id, site_id))

    inserts = []
    for (t, pulse_rate, pulse_variation) in intervals:
      inserts.append((dep_id, site_id, t, SCORE_INTERVAL, pulse_rate, pulse_variation))
      
    cur.executemany('''INSERT INTO estinterval (deploymentID, siteID, timestamp, 
                                                duration, pulse_interval, pulse_variation)
                             VALUE (%s, %s, %s, %s, %s, %s)''', inserts)



def get_tx_params(db_con, dep_id): 
  ''' Get transmitter parameters for band filter as a dictionary.
    
    `band3` and `band10` are expected to be among the tramsitter's 
    paramters and converted to integers. If they're unspecified (NULL), 
    they are given `sys.maxint`. `pulse_ratae` is interpreted as a float
    pulses / minute. All other paramters are treated as strings.
  ''' 

  cur = db_con.cursor()
  cur.execute('''SELECT param.name, param.value
                   FROM tx_parameters AS param
                   JOIN tx ON tx.ID = param.txID
                  WHERE tx.ID = (SELECT tx.ID FROM tx
                                   JOIN deployment ON tx.ID = deployment.txID
                                  WHERE deployment.ID = %s)''', (dep_id,))
  
  params = {} 
  for (name, value) in cur.fetchall(): 
    if name == 'band3': 
      if value == '':
        params['band3'] = sys.maxint
      else: 
        params['band3'] = int(value)
    
    elif name == 'band10': 
      if value == '':
        params['band10'] = sys.maxint
      else: 
        params['band10'] = int(value)

    elif name == 'pulse_rate': 
      params[name] = float(value)

    else: 
      params[name] = value

  return params



##### Per site/transmitter filters. ###########################################

def expected_pulse_interval(data_dict, pulse_rate): 
  ''' Compute expected pulse rate over data.
  
    Data is assumed to be sorted by timestamp and timestamps should be
    multiplied by `TIMESTAMP_PRECISION`. (See `get_est_data()`.)  

    :param pulse_rate: Transmitter's nominal pulse rate in pulses / minute. 
  ''' 
  
  max_interval = ((60 * (2 - MIN_DRIFT_PERCENTAGE)) / pulse_rate) * TIMESTAMP_PRECISION
  min_interval = ((60 * MIN_DRIFT_PERCENTAGE) / pulse_rate) * TIMESTAMP_PRECISION
  bin_width = int(BIN_WIDTH * TIMESTAMP_PRECISION)

  # Compute pairwise time differentials. 
  diffs = []
  for data in data_dict.itervalues():
    if data.shape[0] > 0:
      filtered_data = data[(data[:,5] >= 0),2]#remove already determined "bad" points
      rows = filtered_data.shape[0]
      for i in range(rows):
        for j in range(i+1, rows): 
          diff = filtered_data[j] - filtered_data[i]
          if min_interval < diff and diff < max_interval: 
            diffs.append(diff)

  if len(diffs) <= 2: 
    return (0, 0)

  # Create a histogram. Bins are scaled by `BIN_WIDTH`. 
  (hist, bins) = np.histogram(diffs, bins = 1 + ((max(diffs) - min(diffs)) / bin_width))
  
  # Mode pulse interval = expected pulse interval. 
  i = np.argmax(hist)
  mode = int(bins[i] + bins[i+1]) / 2

  # Second moment of mode. 
  second_moment = 0
  if mode > 0:
    m = float(mode) / TIMESTAMP_PRECISION
    for j in range(hist.shape[0]-1): 
      x = float(bins[j] + bins[j+1]) / (2 * TIMESTAMP_PRECISION)
      f = float(hist[j]) / hist[i] 
      second_moment += BIN_WIDTH * f * (x - m) ** 2 

  return (mode, second_moment)


def parametric_filter(data, tx_params): 
  ''' Parametric filter. Set score to `PARAM_BAD`.

    So far we only look at `band3` and `band10`. 
  '''

  (rows, _) = data.shape
  for i in range(rows): 
    if data[i,3] > tx_params['band3'] or data[i,4] > tx_params['band10']:
      data[i,5] = PARAM_BAD


def burst_filter(data, interval): 
  ''' Burst filter. Set score to `BURST_BAD`.
    
    Remove segments of points whose density exceed the a priori 
    pulse rate by an order of magnitude. For now, it is assumed
    that no transmitter produces more than two pulses a second. 
    Note that we could eventually use the 'pulse_rate' parameter
    in `qraat.tx_parameter`. 
  ''' 

  # Create histogram of pulses with `BURST_INTERVAL` second bins. 
  #remove already determined "bad" points
  (hist, bins) = np.histogram(data[(data[:,5] >= 0), 2], 
                              range = (interval[0] * TIMESTAMP_PRECISION, 
                                       interval[1] * TIMESTAMP_PRECISION),
                              bins = SCORE_INTERVAL / BURST_INTERVAL)
  
  # Find bins with bursts. 
  bad_intervals = []
  for i in range(len(hist)): 
    #print "%d pulses from %.2f to %.2f." % (hist[i], 
    #                float(bins[i]) / TIMESTAMP_PRECISION, 
    #                float(bins[i+1]) / TIMESTAMP_PRECISION)
    if (float(hist[i]) / BURST_INTERVAL) > BURST_THRESHOLD: 
      bad_intervals.append((bins[i], bins[i+1]))
      # NOTE If it were possible to carry around the row index when
      # computing the histogram, we could mark signals within bad 
      # bins here. 

  # Mark signals within bad bins. 
  (rows, _) = data.shape
  for i in range(rows): 
    for (t0, t1) in bad_intervals:
      if t0 <= data[i,2] and data[i,2] <= t1:
        data[i,5] = BURST_BAD


def time_filter(data, pulse_interval, pulse_variation, thresh=None):
  ''' Time filter. Calculate absolute score and normalize. 
    
    `thresh` is either None or in [0 .. 1]. If `thresh` is not none,
    it returns data with relative score of at least this value. 
  ''' 

  pulse_error = int(SCORE_ERROR(pulse_variation) * TIMESTAMP_PRECISION)
  delta = SCORE_NEIGHBORHOOD * TIMESTAMP_PRECISION / 2 
    
  # Best score theoretically possible for this interval. 
  theoretical_count = SCORE_NEIGHBORHOOD * TIMESTAMP_PRECISION / pulse_interval

  # Put pulses into at most score_neighborhood / pulse_error bins. 
  bins = {}
  for i in range(data.shape[0]):
    if data[i,5] < 0: # Skip if pulse didn't pass a previous filter. 
      continue
  
    t = data[i,2] - (data[i,2] % pulse_error)
    if bins.get(t): 
      bins[t].append(i)
    else: bins[t] = [i]

  # Score pulses in bins with exactly one pulse. 
  for points in bins.itervalues():
    if len(points) > 1: 
      data[i,5] = 0

    else:
      count = 0
      i = points[0]
      N = (delta / pulse_interval) 
      for n in range(-N+1, N):
        t = data[i,2] + (pulse_interval * n)
        t -= (t % pulse_error)
        if bins.get(t):
          count += 1 
      data[i,5] = count - 1 # Counted myself.
  
  data[:,6] = theoretical_count
  data[:,7] = np.max(data[:,5]) # Max count. 
