# gvm.py -- Bimodal von Mises distribution. 

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
    



### Testing, testing ... ######################################################

if __name__ == '__main__':

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
