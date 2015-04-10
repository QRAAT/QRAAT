# sim.py -- Run simulations. 

import util
import signal1
import position1

import pickle, gzip
import numpy as np
import matplotlib.pyplot as pp
import scipy

def nearest_sites(p, sites, k):
  # k nearest sites to p 
  (site_ids, _) = zip(*sorted(list(sites.iteritems()), 
                          key=lambda(item) : np.abs(p - item[1])))
  return list(site_ids[:k])

def create_array(exp_params, sys_params):
  s = 2 * exp_params['half_span'] + 1
  return [[[[[] for n in range(s) ] 
                  for e in range(s) ]
                    for j in range(len(exp_params['sig_n'])) ] 
                      for i in range(len(exp_params['pulse_ct'])) ]
  

def montecarlo(exp_params, sys_params, sv, nearest=None, compute_cov=True):
  s = 2 * exp_params['half_span'] + 1
  shape = (len(exp_params['pulse_ct']), len(exp_params['sig_n']), s, s, exp_params['trials'])
  pos = np.zeros(shape, dtype=np.complex)
  if compute_cov:
    cov0 = create_array(exp_params, sys_params) # bootstrap
    cov1 = create_array(exp_params, sys_params) # true position
  else: 
    cov0 = cov1 = None

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
  
  # Fix transmission power. 
  scaled_rho = signal1.scale_tx_coeff(exp_params['center'], 
                                      exp_params['rho'],
                                      sites,
                                      sys_params['include'])

  # Interpolate steering vector splines.
  sv_splines = signal1.compute_bearing_splines(sv)

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
            if nearest is None:
              include = sys_params['include']
            else: 
              include = nearest_sites(P, sites, nearest)
            sig = simulator(P, sites, sv_splines, scaled_rho, sig_n, pulse_ct, include)
          
            # Estimate position.
            P_hat = position1.PositionEstimator(999, sites, sys_params['center'], sig, sv, method)
            pos[i,j,e,n,k] = P_hat.p

            # Estimate confidence region. 
            if compute_cov:
              try: 
                cov0[i][j][e][n].append(position1.Covariance(P_hat, sites, p_known=P))
                cov1[i][j][e][n].append(position1.BootstrapCovariance(P_hat, sites))
              #except IndexError: # Hessian matrix computation
              #  print "Warning!"
              except np.linalg.linalg.LinAlgError:
                print "Singular matrix!"
              except position1.UnboundedContourError:
                print "Unbounded!"
              except position1.PosDefError:
                print "Positive definite!"

  return (pos, (cov0, cov1))


def save(prefix, pos, cov, exp_params, sys_params,):
  np.savez(prefix + '-pos', pos)
  pickle.dump(cov[0], open(prefix + '-cov0', 'w'))
  pickle.dump(cov[1], open(prefix + '-cov1', 'w'))
  #pickle.dump(cov[0], gzip.open(prefix + '-cov0' + '.gz', 'wb'))
  #pickle.dump(cov[1], gzip.open(prefix + '-cov1' + '.gz', 'wb'))
  pickle.dump((exp_params, sys_params), open(prefix + '-params', 'w'))

def load(prefix):
  pos = np.load(prefix + '-pos.npz')['arr_0']
  cov0 = pickle.load(open(prefix + '-cov0', 'r'))
  cov1 = pickle.load(open(prefix + '-cov1', 'r'))
  #cov0 = pickle.load(gzip.open(prefix + '-cov0' + '.gz', 'rb'))
  #cov1 = pickle.load(gzip.open(prefix + '-cov1' + '.gz', 'rb'))
  (exp_params, sys_params) = pickle.load(open(prefix + '-params'))
  return (pos, (cov0, cov1), exp_params, sys_params)
    
def pretty_report(pos, cov, exp_params, sys_params, conf_level):
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
            (angle, axes) = position1.compute_conf(C, Qt)
            E = position1.Ellipse(p, angle, axes)
          except position1.PosDefError:
            E = None
            print "skippiong positive definite"
  
          print '  (%s, %s)' % (fmt(mean[0]), fmt(mean[1])), fmt(rmse), 

          if cov is not None:
            a = b = ct = 0
            area = 0
            for k in range(len(cov[i][j][e][n])):
              try:
                E_hat = cov[i][j][e][n][k].conf(conf_level)
                if E_hat.axes[0] > 0:
                  area += E_hat.area()
                  ct += 1
                  if p in E_hat: a += 1
                if not E or p_hat[k] in E: b += 1
              except position1.PosDefError:
                print "Positive definite!"
            
            print fmt(float(a) / ct), \
                  fmt(float(b) / exp_params['trials']), \
                  fmt(area / ct), fmt((E.area() if E else 1)), \
                  fmt((area / exp_params['trials']) / (E.area() if E else 1))

          else: 
            b = 0
            for k in range(exp_params['trials']):
              if not E or p_hat[k] in E: b += 1
            print fmt(float(b) / exp_params['trials']), \
                  fmt((E.area() if E else 1))

            

def plot_hist(pos, conf, exp_params, sys_params, conf_level): # TODO out-of-date
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
            E_hat = position1.Ellipse(p_hat[k], angle, axes)
            dist.append(np.abs(p - p_hat[k]))
            area.append(E_hat.area()) 
     
          print "Correlation: (%0.4f, %0.4f)" % scipy.stats.stats.pearsonr(area, dist)

          n, bins, patches = pp.hist(area, 50, normed=1, facecolor='green', alpha=0.75)
          pp.title('$\sigma_n^2$=%0.4f, sample_ct=%d' % (sig_n, pulse_ct))
          pp.show()
          pp.clf()


def plot_grid(fn, exp_params, sys_params, pos=None, nearest=None):
  
  fig = pp.gcf()
  fig.set_size_inches(12,10)
  ax = fig.add_subplot(111)
  ax.axis('equal')
  ax.set_xlabel('easting (m)')
  ax.set_ylabel('northing (m)')

  # Plot sites
  (site_ids, P) = zip(*sys_params['sites'].iteritems())
  X = np.imag(P)
  Y = np.real(P)
  pp.xlim([np.min(X) - 100, np.max(X) + 100])
  pp.ylim([np.min(Y) - 100, np.max(Y) + 100])
  
  offset = 20
  for (id, (x,y)) in zip(site_ids, zip(X,Y)): 
    pp.text(x+offset, y+offset, id)
  pp.scatter(X, Y, label='sites', facecolors='r')

  # Plot positions.
  if pos is not None: 
    X = np.imag(pos.flat)
    Y = np.real(pos.flat)
  pp.scatter(X, Y, label='estimates', alpha=0.1, facecolors='b', edgecolors='none', s=5)

  # Plot grid
  offset = 10
  s = 2*exp_params['half_span'] + 1
  for e in range(s): #easting 
    for n in range(s): #northing
      p = exp_params['center']  + np.complex((n - exp_params['half_span']) * exp_params['scale'], 
                                             (e - exp_params['half_span']) * exp_params['scale'])
      pp.plot(p.imag, p.real, label='grid', color='w', marker='o', ms=5)
      if nearest:
        include = nearest_sites(p, sys_params['sites'], nearest)
        a = ', '.join(map(lambda(id) : str(id), sorted(include)))
        pp.text(p.imag+offset, p.real+offset, a, fontsize=8)

  pp.savefig(fn)
  pp.clf()



# Testing, testing ... 

def conf_test(prefix, center, sites, sv, conf_level, sim): 
  
  exp_params = { 'simulator' : sim,
                 'rho'       : 1,
                 'sig_n'     : [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1],
                 'pulse_ct'  : [3,4,5,6,7,8,9,10],
                 'center'    : (4260838.3+574049j), 
                 'half_span' : 0,
                 'scale'     : 1,
                 'trials'    : 1000 }

  sys_params = { 'method'         : 'bartlet', 
                 'include'        : [4,6,8],
                 'center'         : center,
                 'sites'          : sites } 

  (pos, cov) = montecarlo(exp_params, sys_params, sv)
  save(prefix, pos, cov, exp_params, sys_params)
  pos, cov, exp_params, sys_params = load(prefix)
  print "Covariance\n"
  pretty_report(pos, cov[0], exp_params, sys_params, conf_level)
  print "BootstrapCovariance\n"
  pretty_report(pos, cov[1], exp_params, sys_params, conf_level)


def grid_test(prefix, center, sites, sv, conf_level, sim): 
  
  exp_params = { 'simulator' : sim,
                 'rho'       : 1,
                 'sig_n'     : [0.005],
                 'pulse_ct'  : [5],
                 'center'    : (4260738.3+574549j), 
                 'half_span' : 3,
                 'scale'     : 300,
                 'trials'    : 1000 }

  sys_params = { 'method'         : 'bartlet', 
                 'include'        : [],
                 'center'         : center,
                 'sites'          : sites } 

  (pos, cov) = montecarlo(exp_params, sys_params, sv, compute_cov=True, nearest=3)
  save(prefix, pos, cov, exp_params, sys_params)
  pretty_report(pos, cov[0], exp_params, sys_params, conf_level)
  plot_grid('fella.png', exp_params, sys_params, pos, nearest=3)

if __name__ == '__main__':

  cal_id = 3   
  db_con = util.get_db('reader')
  sv = signal1.SteeringVectors(db_con, cal_id)
  sites = util.get_sites(db_con)
  (center, zone) = util.get_center(db_con)
  
  grid_test('exp/grid', center, sites, sv, 0.95, 'real')
  #pos, cov, exp_params, sys_params = load('exp/grid')
  #plot_grid('grid.png', exp_params, sys_params, pos, 3)
  #print "Covariance\n"
  #pretty_report(pos, cov[0], exp_params, sys_params, conf_level)
  #print "BootstrapCovariance\n"
  #pretty_report(pos, cov[1], exp_params, sys_params, conf_level)
