# sim.py -- Run simulations. 

import util
import signal1
import position1

import numpy as np

cal_id = 3   # Calibration ID, specifies steering vectors to use. 

# Variance of transmission coefficient. This value models how the 
# signal changes as the result of the environment in route to the 
# receiver. It is assumed to be noncoherent with the channel noise. 
sig_t = 1 

# Background noise of the signal.  
sig_n = 0.001

def sim(trials, pulses, sv, sites, p, center, half_span, scale):
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


def sim2(trials, pulses, sig_t, sig_n, sv, sites, p, center):
    ct = 0
    for n in range(trials):
      sig = signal1.Simulator(p, sites, sv, sig_n, sig_t, pulses)
      pos = position1.PositionEstimator(999, sites, center, 
                       sig, sv, method=signal1.Signal.Bartlet)
      conf = position1.ConfidenceRegion(pos, sites, 0.68)
      if p in conf:
        ct += 1
    print float(ct) / trials


def sim3(trials, pulses, sv, sites, p, center):
    for sig_n in [0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05]:
      ct = 0
      for n in range(trials):
        sig = signal1.Simulator(p, sites, sv, sig_n, 1, pulses)
        pos = position1.PositionEstimator(999, sites, center, 
                         sig, sv, method=signal1.Signal.MLE)
        conf = position1.ConfidenceRegion(pos, sites, 0.68)
        if p in conf:
          ct += 1
      print sig_n, float(ct) / trials



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
  sim3(100, 10, sv, sites, p, center)

