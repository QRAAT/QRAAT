# sim.py -- Run simulations. 

import util
import signal1
import position1

import pickle
import numpy as np
import matplotlib.pyplot as pp
import scipy

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
              try: 
                C = position1.ConfidenceRegion2(P_hat, sites, conf_level, p_known=P)
                conf[i,j,e,n,k,:] = np.array([C.e.axes[0], C.e.axes[1], C.e.angle])
              #except IndexError: # Hessian matrix computation
              #  print "Warning!"
              except np.linalg.linalg.LinAlgError:
                print "Singular matrix!"
              except position1.UnboundedConfRegionError:
                print "Unbounded!"
              except position1.PosDefError:
                print "Positive definite!"

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
    
def pretty_report(pos, conf, exp_params, sys_params, conf_level):
  Qt = scipy.stats.chi2.ppf(conf_level, 2)
  fmt = lambda x : '%9s' % ('%0.2f' % x)
  s = 2 * exp_params['half_span'] + 1
  num_sites = len(sys_params['include'])
  print 'SITES =', sys_params['include'], 'TRIALS = %d' % exp_params['trials']
  for e in range(s): #easting 
    for n in range(s): #northing
      p = exp_params['center']  + np.complex((n - exp_params['half_span']) * exp_params['scale'], 
                                             (e - exp_params['half_span']) * exp_params['scale'])
      print 'TRUE POSITION = (%.2f, %.2f)\n' % (p.imag, p.real)
      for i, pulse_ct in enumerate(exp_params['pulse_ct']): 
        print 'pulse_ct=%d' % pulse_ct
        for j, sig_n in enumerate(exp_params['sig_n']): 
          print '  sig_n=%.3f' % sig_n,
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
            E = position1.compute_conf(p, C, Qt)
          except position1.PosDefError:
            E = None
            print "skippiong positive definite"
  
          print '  (%s, %s)' % (fmt(mean[0]), fmt(mean[1])), fmt(rmse), 
          if conf_level:
            a = b = 0
            area = 0
            for k in range(exp_params['trials']):
              axes = np.array([conf[i,j,e,n,k,0], conf[i,j,e,n,k,1]])
              angle = conf[i,j,e,n,k,2]
              E_hat = position1.Ellipse(p_hat[k], angle, axes, 
                                sys_params['conf_half_span'], sys_params['conf_scale'])
              area += E_hat.area()
              if p in E_hat:    a += 1
              if not E or p_hat[k] in E: b += 1
            print fmt(float(a) / exp_params['trials']), \
                  fmt(float(b) / exp_params['trials']), \
                  fmt((area / exp_params['trials'])), fmt((E.area() if E else 1)), \
                  fmt((area / exp_params['trials']) / (E.area() if E else 1))
          else: print 


def plot(pos, conf, exp_params, sys_params, conf_level):
  num_sites = len(sys_params['include'])
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
          f = lambda p : [p.imag, p.real]
          P = f(exp_params['center'])
          X = np.array(map(f, p_hat)) 
          
          fig = pp.gcf()
      
          extent = 50
          pp.xlim([P[0]-extent, P[0]+extent])
          pp.ylim([P[1]-extent, P[1]+extent])
          
          # x_hat's 
          pp.scatter(X[:,0], X[:,1], alpha=0.1, edgecolor='none')
          
          # Confidence interval
          try:
            C = np.cov(np.imag(p_hat), np.real(p_hat))
            E = position1.compute_conf(p, C, conf_level, k=num_sites)
            (E_x, E_y) = E.cartesian()
            pp.plot(E_x + p.imag, E_y + p.real, color='k', zorder=11)
          except position1.PosDefError: 
            print '    skipping pos. def. covariance'

          # x
          pp.scatter(P[0], P[1], color='r', zorder=11)
          
          pp.title('$\sigma_n^2$=%0.4f, sample_ct=%d' % (sig_n, pulse_ct))
          pp.show()
          pp.clf()


def plot_hist(pos, conf, exp_params, sys_params, conf_level):
  num_sites = len(sys_params['include'])
  s = 2 * exp_params['half_span'] + 1
  for i, pulse_ct in enumerate(exp_params['pulse_ct']): 
    print 'pulse_ct=%d' % pulse_ct
    for j, sig_n in enumerate(exp_params['sig_n']): 
      print '  sig_n=%f' % sig_n
      for e in range(s): #easting 
        for n in range(s): #northing
          fig = pp.gcf()
          
          p = exp_params['center']  + np.complex((n - exp_params['half_span']) * exp_params['scale'], 
                                                 (e - exp_params['half_span']) * exp_params['scale'])
          p_hat = pos[i,j,e,n,:]
          
          area = []; dist = []
          for k in range(exp_params['trials']):
            axes = np.array([conf[i,j,e,n,k,0], conf[i,j,e,n,k,1]])
            angle = conf[i,j,e,n,k,2]
            E_hat = position1.Ellipse(p_hat[k], angle, axes, 
                              sys_params['conf_half_span'], sys_params['conf_scale'])
            dist.append(np.abs(p - p_hat[k]))
            area.append(E_hat.area()) 
     
          print "Correlation: (%0.4f, %0.4f)" % scipy.stats.stats.pearsonr(area, dist)

          n, bins, patches = pp.hist(area, 50, normed=1, facecolor='green', alpha=0.75)
          pp.title('$\sigma_n^2$=%0.4f, sample_ct=%d' % (sig_n, pulse_ct))
          pp.show()
          pp.clf()



def conf_test(prefix, center, sites, sv, conf_level, sim): 
  
  exp_params = { 'simulator' : sim,
                 'rho'       : 1,
                 'sig_n'     : [0.01, 0.02, 0.05],#, 0.01, 0.02, 0.05],#np.arange(0.002, 0.012, 0.002),
                 'pulse_ct'  : [3,4,5],#,6,7,8,9,10],
                 'center'    : (4260838.3+574049j), 
                 'half_span' : 0,
                 'scale'     : 1,
                 'trials'    : 1000 }

  sys_params = { 'method'         : 'bartlet', 
                 'include'        : [4,6,8],#[2, 3, 4, 5, 6, 8],
                 'center'         : center,
                 'sites'          : sites,
                 'conf_half_span' : position1.HALF_SPAN*10, 
                 'conf_scale'     : 1 }

  (pos, conf) = montecarlo(exp_params, sys_params, sv, conf_level)
  save(prefix, pos, conf, exp_params, sys_params, conf_level)
  pretty_report(pos, conf, exp_params, sys_params, conf_level)


if __name__ == '__main__':

  cal_id = 3   
  db_con = util.get_db('reader')
  sv = signal1.SteeringVectors(db_con, cal_id)
  sites = util.get_sites(db_con)
  (center, zone) = util.get_center(db_con)
  
  conf_test('exp/conf3', center, sites, sv, 0.90, 'real')
  #res = load('exp/conf2', 0.90); pretty_report(*res, conf_level=0.90)
  #res = load('exp/conf5', 0.68); pretty_report(*res, conf_level=0.68)
  
