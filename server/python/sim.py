# sim.py -- Run simulations. 

import util
import signal1
import position1

import numpy as np

cal_id = 3   # Calibration ID, specifies steering vectors to use. 

def sim(trials, pulses, rho, noise, sv, sites, center, half_span, scale, method, simulator, include=[]):
  s = 2 * half_span + 1
  res = np.zeros((len(noise), s, s, trials), dtype=np.complex)
  for (e, sig_n) in enumerate(noise): 
    print 'sig_n=%f' % sig_n
    for i in range(s):
      for j in range(s):
        p = center + np.complex((i - half_span) * scale, 
                                (j - half_span) * scale)
        print '.',
        for n in range(trials):
          # Run simulation. 
          sig = simulator(p, sites, sv, rho, sig_n, pulses, include)
          # Estimate position.
          pos = position1.PositionEstimator(999, sites, center, 
                  sig, sv, method=method)
          res[e,i,j,n] = pos.p
      print ' '
  return res

def report(res, rho, noise, center, half_span, scale):
  s = 2 * half_span + 1
  for (e, sig_n) in enumerate(noise):
    print 'sig_n=%f' % sig_n
    for i in range(s):
      for j in range(s):
        p = center + np.complex((i - half_span) * scale, 
                                (j - half_span) * scale)
        p_hat = res[e,i,j,:]
        mean = np.mean(p_hat)
        mean = [mean.imag, mean.real]
        print mean

        rmse = np.sqrt(np.mean(np.abs(p_hat - p) ** 2))# / res.shape[3])
        print rmse, np.std(p_hat)
        #rmse = [ 
        #  np.sqrt(np.mean((np.imag(p_hat) - p.imag) ** 2)), # / res.shape[3]),
        #  np.sqrt(np.mean((np.real(p_hat) - p.real) ** 2))] # / res.shape[3])]
        #print rmse, np.std(np.imag(p_hat)), np.std(np.real(p_hat))
        
        cov = np.cov(np.imag(p_hat), np.real(p_hat))
        print cov



def save(fn, res, trials, pulses, rho, noise, center, half_span, scale, sites):
  np.savez(fn, 
           exp=np.array([trials, pulses, half_span, scale]), 
           params=np.array([rho] + noise), 
           center=np.array([center]),
           sites=np.array(sites), 
           res=res)

def load(fn): 
  data = np.load(fn)
  trials, pulses, half_span, scale = tuple(data['exp'])
  rho = data['params'][0]
  noise = data['params'][1:]
  sites = data['sites']
  center = data['center'][0]
  res = data['res']
  return (res, trials, pulses, rho, noise, center, half_span, scale, sites)


def sim2(trials, pulses, sig_t, sig_n, sv, sites, p, center):
    ct = 0
    for n in range(trials):
      sig = signal1.Simulator(p, sites, sv, sig_n, sig_t, pulses)
      pos = position1.PositionEstimator(999, sites, center, 
                       sig, sv, method=signal1.Signal.Bartlet)
      conf = position1.ConfidenceRegion(pos, sites, 0.683)
      if p in conf:
        ct += 1
    print float(ct) / trials


def sim3(trials, pulses, sv, sites, p, center):
    guy = [0.002, 0.004, 0.006, 0.008, 0.01, 0.02, 0.03]
    for sig_n in guy: 
      ct = 0
      for n in range(trials):
        sig = signal1.IdealSimulator(p, sites, sv, sig_n, pulses)
        pos = position1.PositionEstimator(999, sites, center, 
                         sig, sv, method=signal1.Signal.Bartlet)
        conf = position1.ConfidenceRegion(pos, sites, 0.683)
        if p in conf:
          ct += 1
      print sig_n, float(ct) / trials



     


if __name__ == '__main__':

  db_con = util.get_db('reader')
  sv = signal1.SteeringVectors(db_con, cal_id)
  sites = util.get_sites(db_con)
  (center, zone) = util.get_center(db_con)
  
  rho = 1 
  noise = np.arange(0.001, 0.011, 0.001)
  center = (4260838.3+574049j)
  half_span = 3 
  scale = 50
  trials = 10000
  pulses = 1
  include = []
 
  # Ideal Bartlet
  res = sim(trials, pulses, rho, noise, sv, sites, center, half_span, scale, 
              signal1.Signal.Bartlet, signal1.IdealSimulator, [4, 8, 6])
  _sites = sites.keys() if include == [] else include
  save('ideal-bartlet', res, trials, pulses, rho, noise, center, half_span, scale, _sites)
  
  # Ideal MLE
  #res = sim(trials, pulses, rho, noise, sv, sites, center, half_span, scale, 
  #            signal1.Signal.MLE, signal1.IdealSimulator, [4, 8, 6])
  #_sites = sites.keys() if include == [] else include
  #save('ideal-mle', res, trials, pulses, rho, noise, center, half_span, scale, _sites)
  
  # Real Bartlet
  res = sim(trials, pulses, rho, noise, sv, sites, center, half_span, scale, 
              signal1.Signal.Bartlet, signal1.Simulator, [4, 8, 6])
  _sites = sites.keys() if include == [] else include
  save('real-bartlet', res, trials, pulses, rho, noise, center, half_span, scale, _sites)
  

  #(res, trials, pulses, rho, noise, center, half_span, scale, _sites) = load('ideal.npz')
  #report(res, rho, noise, center, half_span, scale)
