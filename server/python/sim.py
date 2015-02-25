# sim.py -- Run simulations. 

import util
import signal1
import position1

import numpy as np

cal_id = 3   # Calibration ID, specifies steering vectors to use. 

# Variance of transmission coefficient. This value models how the 
# signal changes as the result of the environment in route to the 
# receiver. It is assumed to be noncoherent with the channel noise. 
sig_t = complex(0.01, 0.00) 

# Background noise of the signal.  
sig_n = complex(0.0006, 0.00)

def sim(trials, pulses, sv, sites, center, half_span, scale):
  res = {}
  for i in range(-half_span, half_span+1):
    for j in range(-half_span, half_span+1):
      p = center + np.complex(i * scale, j * scale)
      res[p] = []
      print '.',
      for n in range(trials):
        # Run simulation. 
        sig = signal1.Simulator(p, sites, sv, sig_n, sig_t, pulses)
        # Estimate position.
        pos = position1.PositionEstimator(999, sites, center, 
                sig, sv, method=signal1.Signal.Bartlet)
        # 68%-confidence of estimate. 
        conf = position1.ConfidenceRegion(pos, sites, 0.68)
        res[p].append((pos.p, conf))
    print ' '
  return res


def report(res):
  for (p, trials) in res.iteritems():
    ct = 0
    for (p_hat, conf) in trials:
      if p in conf: ct += 1
    print p, "%0.5f" % (float(ct) / len(trials))
     
       

if __name__ == '__main__':

  db_con = util.get_db('reader')
  sv = signal1.SteeringVectors(db_con, cal_id)
  sites = util.get_sites(db_con)
  (center, zone) = util.get_center(db_con)

  p = center + np.complex(650, 0)
  res = sim(100, 40, sv, sites, p, 0, 10)
  report(res)

