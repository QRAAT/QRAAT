# sim.py -- Run simulations. 

import util
import signal1
import position1

import pickle
import numpy as np
import matplotlib.pyplot as pp

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



def montecarlo(exp_params, sys_params, sv, conf_level=None):
  s = 2 * exp_params['half_span'] + 1
  shape = (len(exp_params['pulse_ct']), len(exp_params['sig_n']), s, s, exp_params['trials'])
  pos = np.zeros(shape, dtype=np.complex)
  if conf_level: # conf[i,j,e,n,k,:] = (axes[0], axes[1], angle)
    conf = np.zeros(shape + (3,), dtype=np.float)
  else: conf = None
  
  if sys_params['method'] == 'bartlet': 
    method = signal1.Signal.Bartlet
  elif sys_params['method'] == 'MLE': 
    method = signal1.Signal.MLE
  else: raise Exception('Unknown method')

  if exp_params['simulator'] == 'ideal':
    simulator = signal1.IdealSimulator
  elif exp_params['simulator'] == 'real':
    simulator = signal1.Simulator
  else: raise Exception('Unknown simulator')

  sites = sys_params['sites']
  for i, pulse_ct in enumerate(exp_params['pulse_ct']): 
    print 'pulse_ct=%d' % pulse_ct
    for j, sig_n in enumerate(exp_params['sig_n']): 
      print '  sig_n=%f' % sig_n
      for e in range(s): #easting 
        for n in range(s): #northing
          P = exp_params['center']  + np.complex((n - exp_params['half_span']) * exp_params['scale'], 
                                                 (e - exp_params['half_span']) * exp_params['scale'])
          for k in range(exp_params['trials']): 
            # Run simulation. 
            sig = simulator(P, sites, sv, exp_params['rho'], sig_n, pulse_ct, sys_params['include'])
          
            # Estimate position.
            P_hat = position1.PositionEstimator(999, sites, sys_params['center'], sig, sv, method)
            pos[i,j,e,n,k] = P_hat.p

            # Estimate confidence region. 
            if conf_level:
              C = position1.ConfidenceRegion(P_hat, sites, conf_level, 
                      sys_params['conf_half_span'], sys_params['conf_scale']) 
              conf[i,j,e,n,k,:] = np.array([C.e.axes[0], C.e.axes[1], C.e.angle])
  return (pos, conf)


def save(prefix, pos, conf, exp_params, sys_params, conf_level=None):
  np.savez(prefix + '-pos', pos)
  if conf_level:
    np.savez(prefix + '-%0.2fconf' % conf_level, conf)
  pickle.dump((exp_params, sys_params), open(prefix + '-params', 'w'))

def load(prefix, conf_level=None):
  pos = np.load(prefix + '-pos.npz')['arr_0']
  if conf_level:
    conf = np.load(prefix + '-%0.2fconf.npz' % conf_level)['arr_0']
  else: conf = None
  (exp_params, sys_params) = pickle.load(open(prefix + '-params'))
  return (pos, conf, exp_params, sys_params)
    
def report(pos, conf, exp_params, sys_params, conf_level):
  s = 2 * exp_params['half_span'] + 1
  for i, pulse_ct in enumerate(exp_params['pulse_ct']): 
    print 'pulse_ct=%d' % pulse_ct
    for j, sig_n in enumerate(exp_params['sig_n']): 
      print '  sig_n=%f' % sig_n
      for e in range(s): #easting 
        for n in range(s): #northing
          p = exp_params['center']  + np.complex((n - exp_params['half_span']) * exp_params['scale'], 
                                                 (e - exp_params['half_span']) * exp_params['scale'])
          p_hat = pos[i,j,e,n,:]
          mean = np.mean(p_hat)
          mean = [mean.imag, mean.real]

          rmse = np.sqrt(np.mean(np.abs(p_hat - p) ** 2))# / res.shape[3])
          #rmse = [ 
          #  np.sqrt(np.mean((np.imag(p_hat) - p.imag) ** 2)), # / res.shape[3]),
          #  np.sqrt(np.mean((np.real(p_hat) - p.real) ** 2))] # / res.shape[3])]
          #print rmse, np.std(np.imag(p_hat)), np.std(np.real(p_hat))
         
          try: 
            C = np.cov(np.imag(p_hat), np.real(p_hat))
            E = position1.compute_conf(p, C, conf_level)
          except: 
            print "skippiong positive definite"
  
          print '   [%0.2f, %0.2f] -> [%0.2f, %0.2f] %0.5f' % (p.imag, p.real, mean[0], mean[1], rmse), 
          if conf_level:
            ct = 0
            for k in range(exp_params['trials']):
              axes = np.array([conf[i,j,e,n,k,0], conf[i,j,e,n,k,1]])
              angle = conf[i,j,e,n,k,2]
              E_hat = position1.Ellipse(p_hat[k], angle, axes, 
                                sys_params['conf_half_span'], sys_params['conf_scale'])
              if p in E_hat: 
                ct += 1
            print '%0.2f' % (float(ct) / exp_params['trials'])
          else: print 


def plot(pos, conf, exp_params, sys_params):
  s = 2 * exp_params['half_span'] + 1
  for i, pulse_ct in enumerate(exp_params['pulse_ct']): 
    print 'pulse_ct=%d' % pulse_ct
    for j, sig_n in enumerate(exp_params['sig_n']): 
      print '  sig_n=%f' % sig_n
      for e in range(s): #easting 
        for n in range(s): #northing
          f = lambda p : [p.imag, p.real]
          P = f(exp_params['center'])
          X = np.array(map(f, pos[i,j,e,n,:])) 
          fig = pp.gcf()
      
          pp.xlim([P[0]-100, P[0]+100])
          pp.ylim([P[1]-100, P[1]+100])
          
          # x_hat's 
          pp.scatter(X[:,0], X[:,1], alpha=0.1, edgecolor='none')
          
          # x
          pp.scatter(P[0], P[1], color='r', zorder=11)
          
          pp.title('$\sigma_n^2$=%0.4f, sample_ct=%d' % (sig_n, pulse_ct))
          pp.show()
          pp.clf()


def grid_test(): 
  
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



def conf_test(prefix, center, sites, sv, conf_level): 
  
  exp_params = { 'simulator' : 'real',
                 'rho'       : 1,
                 'sig_n'     : np.arange(0.000, 0.012, 0.002),
                 'pulse_ct'  : [1,2,5,10,100],
                 'center'    : (4260838.3+574049j), 
                 'half_span' : 0,
                 'scale'     : 1,
                 'trials'    : 10000 }

  sys_params = { 'method'         : 'bartlet', 
                 'include'        : [4, 8, 6],
                 'center'         : center,
                 'sites'          : sites,
                 'conf_half_span' : position1.HALF_SPAN*10, 
                 'conf_scale'     : 1 }

  (pos, conf) = montecarlo(exp_params, sys_params, sv, conf_level)
  save(prefix, pos, conf, exp_params, sys_params, conf_level)
  pos, conf, exp_params, sys_params = load(prefix, conf_level)
  report(pos, conf, exp_params, sys_params, conf_level)




if __name__ == '__main__':

  db_con = util.get_db('reader')
  sv = signal1.SteeringVectors(db_con, cal_id)
  sites = util.get_sites(db_con)
  (center, zone) = util.get_center(db_con)
  
  gamma=0.95
  #conf_test('exp/real', center, sites, sv, gamma)
  res = load('exp/ideal', gamma)
  #plot(*res)
  report(*res, conf_level=gamma)

 
