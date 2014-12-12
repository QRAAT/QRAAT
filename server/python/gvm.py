# gvm.py -- Bimodal von Mises distribution. 

import numpy as np
from scipy.special import iv as I # Modified Bessel of the first kind.

class VonMises2: 

  def __init__(self, mu1, mu2, kappa1, kappa2):
    
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
    
    num =  np.exp(self.kappa1 * np.cos(theta - self.mu1) + \
                  self.kappa2 * np.cos(2 * (theta - self.mu2))) 
    return num / self.denom

  def normalizingFactor(self, delta, kappa1, kappa2, rounds=10):
    G0 = 0 
    for j in range(1,rounds):
      G0 += I(2*j, kappa1) * I(j, kappa2) * np.cos(2 * j * delta)
    G0 = (G0 * 2) + (I(0,kappa1) * I(0,kappa2))
    return G0


### Testing, testing ... ######################################################

if __name__ == '__main__':

  mu1 = 0;      mu2 = 1
  kappa1 = 0.8; kappa2 = 3
  p = VonMises2(mu1, mu2, kappa1, kappa2)

  import matplotlib.pyplot as pp
  fig, ax = pp.subplots(1, 1)
  fig.canvas.draw()

  x = np.arange(0, 2*np.pi, np.pi / 100)
  
  print np.sum(p(x) * (np.pi / 100))
  pp.xlim([0,2*np.pi])
  ax.plot(x, p(x), 'k-', lw=2, 
    label='$\mu_1=%.2f$, $\mu_2=%.2f$, $\kappa_1=%.2f$, $\kappa_2=%.2f$' % (
             mu1, mu2, kappa1, kappa2))
  ax.legend(loc='best', frameon=False)
  pp.show()

