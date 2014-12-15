# gvm.py -- Bimodal von Mises distribution. 

import util

import numpy as np
import matplotlib.pyplot as pp
from scipy.special import iv as I # Modified Bessel of the first kind.

class VonMises2: 

  def __init__(self, mu1, mu2, kappa1, kappa2):
  
    ''' Bimodal von Mises distribution.
  
      Compute a probability density function from the bimodal von Mises 
      distribution paramterized by `mu1` and `mu2`, the peaks of the two 
      humps, and `kappa1` and `kappa2`, the "spread" of `mu1` and `mu2`
      resp., analogous to variance. 
    ''' 
    
    assert 0 <= mu1 and mu1 < 2*np.pi
    assert 0 <= mu2 and mu2 < 2*np.pi
    assert kappa1 >= 0
    assert kappa2 >= 0 

    self.mu1    = mu1
    self.mu2    = mu2
    self.kappa1 = kappa1
    self.kappa2 = kappa2

    delta = (mu1 - mu2) % np.pi
    G0 = self.normalizingFactor(delta, kappa1, kappa2)
    self.denom = 2 * np.pi * G0

  def __call__(self, theta):
    ''' Evaluate the probability density function at `theta`. ''' 
    num =  np.exp(self.kappa1 * np.cos(theta - self.mu1) + \
                  self.kappa2 * np.cos(2 * (theta - self.mu2))) 
    return num / self.denom

  def normalizingFactor(self, delta, kappa1, kappa2, rounds=10):
    ''' Compute the normalizing factor. ''' 
    G0 = 0 
    for j in range(1,rounds):
      G0 += I(2*j, kappa1) * I(j, kappa2) * np.cos(2 * j * delta)
    G0 = (G0 * 2) + (I(0,kappa1) * I(0,kappa2))
    return G0

  @classmethod 
  def mle(cls, theta, prob):
    ''' Maximum likelihood estimator for the von Mises distribution. 
      
      Find the most likely parameters for the observed bearing probability 
      distribution and return an instance of this class. 
    '''
    
    # TODO 
    mu1 = 0;      mu2 = 1
    kappa1 = 0.8; kappa2 = 3
    
    return cls(mu1, mu2, kappa1, kappa2)


class Bearing:
  
  def __init__(self, db_con, dep_id, t_start, t_end):
    self.length = None
    self.max_id = -1
    self.dep_id = dep_id
    self.site_table = {}
    cur = db_con.cursor()
    cur.execute('''SELECT siteID, ID, timestamp, bearing, likelihood, activity
                     FROM bearing
                    WHERE deploymentID = %s
                      AND timestamp >= %s
                      AND timestamp <= %s
                    ORDER BY timestamp ASC''', (dep_id, t_start, t_end))
    for row in cur.fetchall():
      site_id = int(row[0])
      row = (int(row[1]), float(row[2]), float(row[3]), float(row[4]), float(row[5]))
      if self.site_table.get(site_id) is None:
        self.site_table[site_id] = [row]
      else: self.site_table[site_id].append(row)
      if row[0] > self.max_id: 
        self.max_id = row[0]

  def __len__(self):
    if self.length is None:
      self.length = sum(map(lambda(table): len(table), self.site_table.values()))
    return self.length

  def __getitem__(self, *index):
    if len(index) == 1: 
      return self.site_table[index[0]]
    elif len(index) == 2:
      return self.site_table[index[0]][index[1]]
    elif len(index) == 3:
      return self.site_table[index[0]][index[1]][index[2]]
    else: return None
  
  def get_sites(self):
    return self.site_table.keys()

  def get_site_bearings(self, site_id):
    #return map(lambda(row) : row[2], self.site_table[site_id])
    return map(lambda(row) : (row[2] * np.pi) / 180, self.site_table[site_id])

  def get_max_id(self): 
    return self.max_id






### Testing, testing ... ######################################################

def test_mle():

  # Generate a noisy bearing distribution "sample".  
  mu1 = 0;      mu2 = 1
  kappa1 = 0.8; kappa2 = 3
  P = VonMises2(mu1, mu2, kappa1, kappa2)
  
  theta = np.arange(0, 2*np.pi, np.pi / 30)
  prob = P(theta) + np.random.uniform(-0.1, 0.1, 60)
  
  # Find most likely parameters for a von Mises distribution
  # fit to (theta, prob). 
  p = VonMises2.mle(theta, prob)

  # Plot observation.
  fig, ax = pp.subplots(1, 1)
  ax.plot(theta, prob, linestyle='steps')
 
  # Plot most likely distribution.
  x = np.arange(0, 2*np.pi, np.pi / 180)
  print np.sum(p(x) * (np.pi / 360))
  pp.xlim([0,2*np.pi])
  ax.plot(x, p(x), 'k-', lw=2, 
    label='$\mu_1=%.2f$, $\mu_2=%.2f$, $\kappa_1=%.2f$, $\kappa_2=%.2f$' % (
             mu1, mu2, kappa1, kappa2))
  
  ax.legend(loc='best', frameon=False)
  pp.show()


def test_bearing(): 
  
  dep_id = 105
  t_start = 1407452400
  t_end = 1407455985 #- (50 * 60)

  db_con = util.get_db('reader')
  bearing = Bearing(db_con, dep_id, t_start, t_end)
  
  #(hist, bins) = np.histogram(bearing.get_site_bearings(2), 360)
  fig, ax = pp.subplots(1, 1)

  N = 100
  n, bins, patches = ax.hist(bearing.get_site_bearings(3), 
                             bins = [ (i * 2 * np.pi) / N for i in range(N) ],
                             facecolor='blue', alpha=0.25)
 
  # Plot most likely distribution.
  pp.xlim([0,2*np.pi])
  
  ax.legend(loc='best', frameon=False)
  pp.show()


if __name__ == '__main__':
  
  test_bearing()
  #test_mle()
