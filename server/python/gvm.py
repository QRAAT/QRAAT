# gvm.py -- Bimodal von Mises distribution. 

import util, position

import sys
import numpy as np
import matplotlib.pyplot as pp
from scipy.special import iv as I # Modified Bessel of the first kind.
from scipy.optimize import fmin # Downhill simplex minimization algorithm. 
from scipy.optimize import minimize

two_pi = 2 * np.pi

class VonMises2: 

  def __init__(self, mu1, mu2, kappa1, kappa2):
  
    ''' Bimodal von Mises distribution.
  
      Compute a probability density function from the bimodal von Mises 
      distribution paramterized by `mu1` and `mu2`, the peaks of the two 
      humps, and `kappa1` and `kappa2`, the "spread" of `mu1` and `mu2`
      resp., analogous to variance. 
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
    ''' Compute the normalizing factor. ''' 
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
      The parameters are found with the Simplex algorithm. 
    '''
    
    n = len(bearings)

    T = np.array([0,0,0,0], dtype=np.float128)
    for theta in bearings:
      T += np.array([np.cos(theta),     np.sin(theta),
                     np.cos(2 * theta), np.sin(2 * theta)], dtype=np.float128)

    def ll(u1, u2, k1, k2) :
          
       return np.dot(np.array([k1 * np.cos(u1),     k1 * np.sin(u1), 
                               k2 * np.cos(2 * u2), k2 * np.sin(2 * u2)], 
                         dtype=np.float128), 
                           
                 T) - (n * (np.log(two_pi) + np.log(
                  cls.normalizingFactor((u1 - u2) % np.pi, 
                                        k1, k2, rounds=10))))

    obj = lambda(x) : -ll(x[0], x[1], np.exp(x[2]), np.exp(x[3]))

    x = fmin(obj, np.array([0,0,0,0], dtype=np.float128),
             ftol=0.001, disp=False)
    
    x[0] %= two_pi
    x[1] %= two_pi
    x[2] = np.exp(x[2])
    x[3] = np.exp(x[3])
    return cls(*x)



### class Signal. #############################################################

class Signal:

  def __init__(self, db_con, dep_id, t_start, t_end, score_threshold=0):
    
    self.table = {}
    cur = db_con.cursor()
    ct = cur.execute('''SELECT ID, siteID, timestamp, edsp, 
                               ed1r,  ed1i,  ed2r,  ed2i,  
                               ed3r,  ed3i,  ed4r,  ed4i 
                   FROM est
                   JOIN estscore ON est.ID = estscore.estID
                  WHERE deploymentID= %s
                    AND timestamp >= %s 
                    AND timestamp <= %s
                    AND (score / theoretical_score) >= %s''', 
              (dep_id, t_start, t_end, score_threshold))
 
    if ct:
      raw_data = np.array(cur.fetchall(), dtype=float)
      est_ids = np.array(raw_data[:,0], dtype=int)
      self.max_est_id = np.max(est_ids)
      site_ids = np.array(raw_data[:,1], dtype=int)
      timestamps = raw_data[:,2]
      power = raw_data[:,3]
      signal_vector = np.zeros((raw_data.shape[0], position.num_ch),dtype=np.complex)
      for j in range(position.num_ch):
        signal_vector[:,j] = raw_data[:,2*j+4] + np.complex(0,-1)*raw_data[:,2*j+5]
      
      for site_id in set(site_ids):
        site = _site_data(site_id)
        site.est_ids = est_ids[site_ids == site_id]
        site.t = timestamps[site_ids == site_id]
        site.power = power[site_ids == site_id]
        site.signal_vector = signal_vector[site_ids == site_id]
        site.count = np.sum(site_ids == site_id)
        self.table[site_id] = site
  
  def __getitem__(self, *index):
    if len(index) == 1: 
      return self.table[index[0]]
    else: return None

  def get_sites(self):
    return self.table.keys()

  def get_bearings(self, sv, site_id):
    return map(lambda (theta) : (theta * np.pi) / 180, 
               self.table[site_id].bartlets_estimator(sv))


class _site_data: 

  def __init__(self, site_id):
    self.site_id = site_id
    self.est_ids = None
    self.t = None
    self.power = None
    self.signal_vector = None
    self.count = 0
    
    self.cal_id = None
    self.bearing = None 
    self.bearing_likelihood = None
    self.theta_hat = None

  def __len__(self):
    return self.count

  def bartlets_estimator(self, sv):
    ''' Compute the most likely bearing for each signal. '''

    if self.cal_id != sv.calID[self.site_id]:
      
      # Compute bearing likelihood for each pulse.
      V = self.signal_vector #records X channels
      G = sv.steering_vectors[self.site_id] #bearings X channels
      self.bearing = sv.bearings[self.site_id]
      self.cal_id = sv.calID[self.site_id]
      left_half = np.dot(V, np.conj(np.transpose(G))) #records X bearings
      self.bearing_likelihood = np.real(left_half * np.conj(left_half)) #records X bearings
      self.site_position = sv.sites.get(ID=self.site_id).pos
    
      # Most likely bearing for each pulse.
      self.bearing_estimate = np.argmax(self.bearing_likelihood)
      self.theta_hat = np.zeros(self.count, dtype=float)
      for i in range(self.count):
        self.theta_hat[i] = np.argmax(self.bearing_likelihood[i])
        self.theta_hat[i] = self.bearing[self.theta_hat[i]]
      return self.theta_hat


### class Bearing. ############################################################

class Bearing:
  
  def __init__(self, db_con, dep_id, t_start, t_end):
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
  p = VonMises2(mu1, mu2, kappa1, kappa2)

  # Exponential representation
  def yeah(theta, u1, u2, k1, k2):
      l = np.array([k1 * np.cos(u1),     k1 * np.sin(u1),      
                    k2 * np.cos(2 * u2), k2 * np.sin(2 * u2)])
      T = np.array([np.cos(theta),    np.sin(theta),
                    np.cos(2 * theta), np.sin(2 * theta)])
      G0 = VonMises2.normalizingFactor((u1 - u2) % np.pi, k1, k2)
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
  P = VonMises2(mu1, mu2, kappa1, kappa2)
  
  theta = np.arange(0, 2*np.pi, np.pi / 30)
  prob = P(theta) + np.random.uniform(-0.1, 0.1, 60)
  bearings = []
  for (a, b) in zip(theta, prob):
    bearings += [ a for i in range(int(b * 100)) ]

  # Find most likely parameters for a von Mises distribution
  # fit to (theta, prob). 
  p = VonMises2.mle(bearings)

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
  p = VonMises2.mle(bearings)

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


if __name__ == '__main__':
  
  #test_exp()
  test_bearing()
  #test_mle()
