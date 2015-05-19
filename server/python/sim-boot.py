# sim.py -- Run simulations. 

import util
import signal1
import position1

import pickle, gzip, copy
import os, os.path
from multiprocessing import Process 
import numpy as np
import matplotlib.pyplot as pp
import matplotlib.colors as colors
import matplotlib.patches as patches
import matplotlib.cm as cmx
import scipy


### SIMULATION ################################################################

JOBS = 3 # Number of processes to spawn in montecarlo_huge()

POS_EXT_FMT = '-%02d.%02d'

# Constraint: (delta * s)^m = 1500. m=2, n=-1, delta=10, s=150.
POS_EST_M = 3
POS_EST_N = -1
POS_EST_DELTA = 5
POS_EST_S = 10


def nearest_sites(p, sites, k):
  # k nearest sites to p 
  (site_ids, _) = zip(*sorted(list(sites.iteritems()), 
                          key=lambda(item) : np.abs(p - item[1])))
  return list(site_ids[:k])

def sites_within_dist(p, sites, dist): 
  # sites within `dist` meters of `p`
  site_ids = []
  for (id, site) in sites.iteritems():
    if np.abs(p - site) <= dist: 
      site_ids.append(id)
  return site_ids

def create_array_from_params(exp_params, sys_params):
  s = 2 * exp_params['half_span'] + 1
  return [[[[[] for n in range(s) ] 
                  for e in range(s) ]
                    for j in range(len(exp_params['sig_n'])) ] 
                      for i in range(len(exp_params['pulse_ct'])) ]

def create_array_from_shape(shape):
  return [[[[[] for n in range(shape[3]) ] 
                  for e in range(shape[2]) ]
                    for j in range(shape[1]) ] 
                      for i in range(shape[0]) ]


def montecarlo_huge(prefix, exp_params, sys_params, sv, nearest=None, compute_cov=True):
  s = 2 * exp_params['half_span'] + 1
  shape = (len(exp_params['pulse_ct']), len(exp_params['sig_n']), exp_params['trials'])

  if sys_params['method'] == 'bartlet': 
    method = signal1.Signal.Bartlet
  elif sys_params['method'] == 'MLE': 
    method = signal1.Signal.MLE
  else: raise Exception('Unknown method')

  sites = sys_params['sites']
  
  # Fix transmission power. 
  scaled_rho = signal1.scale_tx_coeff(exp_params['center'], 
                                      exp_params['rho'],
                                      sites,
                                      sys_params['include'])
  print 'scaled_rho:', scaled_rho

  # Interpolate steering vector splines.
  sv_splines = signal1.compute_bearing_splines(sv)

  # Compile a list of points to simulate. 
  Q = []
  for e in range(s): #easting 
    for n in range(s): #northing
      if not os.path.isfile(prefix+(POS_EXT_FMT % (e,n))+'-pos.npz'):
        Q.append((e,n))

  # Partition points into processes. 
  Qs = [] 
  q = len(Q) / JOBS
  for j in range(JOBS): 
    Qs.append(Q[q*j:q*(j+1)])
  Qs[-1] += Q[q*JOBS:]
  
  args = (prefix, exp_params, sys_params, sv, nearest, compute_cov, 
             shape, method, sites, scaled_rho, sv_splines)

  # Spawn a process for each set of points. 
  proc = []
  for Q in Qs: 
    proc.append( Process(target=_montecarlo_huge, args=args + (Q,)) )
    proc[-1].start()

  # Wait for them to finish. 
  for i in range(len(Qs)): 
    proc[i].join()


def _montecarlo_huge(prefix, exp_params, sys_params, sv, nearest, compute_cov, 
                       shape, method, sites, scaled_rho, sv_splines, Q):
  for (e,n) in Q:
    print e,n
    pos = np.zeros(shape, dtype=np.complex)
    if compute_cov:
      cov_asym = [[[] for j in range(len(exp_params['sig_n'])) ] 
                          for i in range(len(exp_params['pulse_ct'])) ]
      cov_boot = [[[] for j in range(len(exp_params['sig_n'])) ] 
                          for i in range(len(exp_params['pulse_ct'])) ]
    else: 
      cov_asym = cov_boot = None
    
    for i, pulse_ct in enumerate(exp_params['pulse_ct']): 
      print 'pulse_ct=%d' % pulse_ct
      for j, sig_n in enumerate(exp_params['sig_n']): 
        print '  sig_n=%f' % sig_n
        P = exp_params['center']  + np.complex((n - exp_params['half_span']) * exp_params['scale'], 
                                               (e - exp_params['half_span']) * exp_params['scale'])
        for k in range(exp_params['trials']): 
          # Run simulation.
          if nearest is None:
            include = sys_params['include']
          else: 
            include = nearest_sites(P, sites, nearest)
          sig = signal1.Simulator(P, sites, sv_splines, scaled_rho, sig_n, pulse_ct, include)
        
          # Estimate position.
          P_hat = position1.PositionEstimator(999, sites, P, sig, sv, method, 
                           s=POS_EST_S, m=POS_EST_M, n=POS_EST_N, delta=POS_EST_DELTA)
          pos[i,j,k] = P_hat.p

          # Estimate confidence region. 
          if compute_cov:
            try: 
              cov_asym[i][j].append(position1.BootstrapCovariance2(P_hat, sites))
            except np.linalg.linalg.LinAlgError:
              print "Singular matrix!"
              cov_asym[i][j].append(None)
            
            try: 
              cov_boot[i][j].append(position1.BootstrapCovariance(P_hat, sites))
            except np.linalg.linalg.LinAlgError:
              print "Singular matrix!"
              cov_boot[i][j].append(None)

    # Save intermediate results. 
    save(prefix, pos, (cov_asym, cov_boot), 
      exp_params, sys_params, add=POS_EXT_FMT % (e, n))


### SAVE RESULTS ##############################################################

def save(prefix, pos, cov, exp_params, sys_params, add=''):
  np.savez(prefix+add + '-pos', pos)
  pickle.dump(cov[0], open(prefix+add + '-cov0', 'w'))
  pickle.dump(cov[1], open(prefix+add + '-cov1', 'w'))
  pickle.dump((exp_params, sys_params), open(prefix + '-params', 'w'))

def load(prefix, add=''):
  pos = np.load(prefix+add + '-pos.npz')['arr_0']
  cov0 = pickle.load(open(prefix+add + '-cov0', 'r'))
  cov1 = pickle.load(open(prefix+add + '-cov1', 'r'))
  (exp_params, sys_params) = pickle.load(open(prefix + '-params'))
  return (pos, (cov0, cov1), exp_params, sys_params)
 
def load_grid(prefix, exp_params, sys_params): 
  s = 2 * exp_params['half_span'] + 1
  shape = (len(exp_params['pulse_ct']), len(exp_params['sig_n']), s, s, exp_params['trials'])
  pos = np.zeros(shape, dtype=np.complex)
  for e in range(s):
    for n in range(s):
      (P, _, _, _) = load(prefix, add=POS_EXT_FMT % (e,n))
      pos[:,:,e,n,:] = P
  return pos


### SUMARIZE RESULTS ##########################################################

def generate_report(pos, cov, exp_params, sys_params, conf_level, offset=True):
  
  # Results
  res = { 'cvg_prob' : np.zeros(pos.shape[:-1], dtype=np.float),
          'mean' : np.zeros(pos.shape[:-1], dtype=np.complex),
          'rmse' : np.zeros(pos.shape[:-1], dtype=np.float),
          'area' : np.zeros(pos.shape[:-1], dtype=np.float),
          'ecc' : np.zeros(pos.shape[:-1], dtype=np.float),
          'avg_area' : np.zeros(pos.shape[:-1], dtype=np.float),
          'avg_ecc' : np.zeros(pos.shape[:-1], dtype=np.float),
          'area_ratio' : np.zeros(pos.shape[:-1], dtype=np.float) }

  Qt = scipy.stats.chi2.ppf(conf_level, 2)
  fmt = lambda x : '%9s' % ('%0.2f' % x)
  num_sites = len(sys_params['include'])
  for e in range(pos.shape[2]): #easting 
    for n in range(pos.shape[3]): #northing
      p = exp_params['center']
      if offset: 
        p += np.complex((n - exp_params['half_span']) * exp_params['scale'], 
                        (e - exp_params['half_span']) * exp_params['scale'])
      for i, pulse_ct in enumerate(exp_params['pulse_ct']): 
        for j, sig_n in enumerate(exp_params['sig_n']): 
          p_hat = pos[i,j,e,n,:]
          mean = np.mean(p_hat)
          mean = [mean.imag, mean.real]
          rmse = np.sqrt(np.mean(np.abs(p_hat - p) ** 2))# / res.shape[3])
          
          res['mean'][i,j,e,n] = np.complex(mean[1], mean[0])
          res['rmse'][i,j,e,n] = rmse
          
          try: 
            C = np.cov(np.imag(p_hat), np.real(p_hat))
            (angle, axes) = position1.compute_conf(C, Qt)
            E = position1.Ellipse(p, angle, axes)
            res['area'][i,j,e,n] = E.area()
            res['ecc'][i,j,e,n] = E.eccentricity()
          except position1.PosDefError:
            E = None
            res['area'][i,j,e,n] = None
            res['ecc'][i,j,e,n] = None

          if cov is not None:
            a = b = ct = 0
            area = 0
            ecc = 0
            for k in range(len(cov[i][j][e][n])):
              if cov[i][j][e][n][k] is not None: 
                try:
                  E_hat = cov[i][j][e][n][k].conf(conf_level)
                  if E_hat.axes[0] > 0:
                    area += E_hat.area()
                    ecc += E_hat.eccentricity()
                    ct += 1
                    if p in E_hat: a += 1
                  if not E or p_hat[k] in E: b += 1
                except position1.PosDefError:
                  pass # print "Positive definite!"
            
            if ct == 0:
              res['cvg_prob'][i,j,e,n] = None
              res['avg_area'][i,j,e,n] = None
              res['avg_ecc'][i,j,e,n] = None
              res['area_ratio'][i,j,e,n] = None
            else:
              res['cvg_prob'][i,j,e,n] = float(a) / ct
              res['avg_area'][i,j,e,n] = area / ct
              res['avg_ecc'][i,j,e,n] = ecc / ct
              res['area_ratio'][i,j,e,n] = res['avg_area'][i,j,e,n] / res['area'][i,j,e,n]

          else: 
            res['cvg_prob'][i,j,e,n] = None
            res['avg_area'][i,j,e,n] = None
            res['avg_ecc'][i,j,e,n] = None
            res['area_ratio'][i,j,e,n] = None

  return res


def display_report(res, exp_params, sys_params, compute_cov=True, offset=True):  
  fmt = lambda x : '%9s' % ('%0.2f' % x)
  print 'SITES =', sys_params['include'], 'TRIALS = %d' % exp_params['trials']
  s = res['rmse'].shape[2]
  for e in range(s): #easting 
    for n in range(s): #northing
      p = exp_params['center']
      if offset: 
        p += np.complex((n - exp_params['half_span']) * exp_params['scale'], 
                        (e - exp_params['half_span']) * exp_params['scale'])
      print 'TRUE POSITION = (%.2f, %.2f)\n' % (p.imag, p.real)
      for i, pulse_ct in enumerate(exp_params['pulse_ct']): 
        print 'pulse_ct=%d' % pulse_ct
        for j, sig_n in enumerate(exp_params['sig_n']): 
          print '  sig_n=%.3f' % sig_n,
          print '  (%s, %s)' % (fmt(res['mean'][i,j,e,n].imag), 
                                fmt(res['mean'][i,j,e,n].real)), 
          print fmt(res['rmse'][i,j,e,n]),
          if compute_cov is True: 
            if res['cvg_prob'][i,j,e,n] is None: 
              print 'bad'
            else: 
              print fmt(res['cvg_prob'][i,j,e,n]), 
              print fmt(res['area'][i,j,e,n]), 
              print fmt(res['avg_area'][i,j,e,n]), 
              print fmt(res['avg_area'][i,j,e,n] / res['area'][i,j,e,n])
          else: 
            print fmt(res['area'][i,j,e,n])



### PLOTTING ##################################################################

def plot_grid(fn, exp_params, sys_params, pulse_ct, sig_n, pos=None, nearest=None, alpha=0.1):
  i = exp_params['pulse_ct'].index(pulse_ct)
  j = exp_params['sig_n'].index(sig_n)
  
  pp.rc('text', usetex=True)
  pp.rc('font', family='serif')
  
  fig = pp.gcf()
  #fig.set_size_inches(12,10)
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
  l = np.max(X) - 10; h = np.max(Y) - 20

  offset = 20
  for (id, (x,y)) in zip(site_ids, zip(X,Y)): 
    pp.text(x+offset, y+offset, id)
  pp.scatter(X, Y, label='sites', facecolors='r', s=10)

  # Plot positions.
  if pos is not None: 
    X = np.imag(pos[i,j].flat)
    Y = np.real(pos[i,j].flat)
  pp.scatter(X, Y, label='estimates', alpha=alpha, facecolors='b', edgecolors='none', s=5)

  # Plot grid
  offset = 20
  s = 2*exp_params['half_span'] + 1
  for e in range(s): #easting 
    for n in range(s): #northing
      p = exp_params['center']  + np.complex((n - exp_params['half_span']) * exp_params['scale'], 
                                             (e - exp_params['half_span']) * exp_params['scale'])
      pp.plot(p.imag, p.real, label='grid', color='w', marker='o', ms=3)
      if nearest:
        include = nearest_sites(p, sys_params['sites'], nearest)
        a = ', '.join(map(lambda(id) : str(id), sorted(include))) 
        pp.text(p.imag-(offset*7), p.real+(offset), a, fontsize=8)
  
  pp.savefig(fn, dpi=300, bbox_inches='tight')
  pp.clf()




### EXPERIMENTS ###############################################################
def grid_test(prefix, center, sites, sv, conf_level): 
  
  exp_params = { 'rho'       : 1,
                 'sig_n'     : [0.001, 0.005, 0.01, 0.05, 0.1],
                 'pulse_ct'  : [2,6,10],
                 'center'    : (4260738.3+574549j), 
                 'half_span' : 2,
                 'scale'     : 350,
                 'trials'    : 1000 }

  sys_params = { 'method'  : 'bartlet', 
                 'include' : [],
                 'center'  : center,
                 'sites'   : sites } 

  # Run simulations.
  montecarlo_huge(prefix, exp_params, sys_params, 
                              sv, compute_cov=True, nearest=3)
  
  # Load and plot grid. 
  pos = load_grid(prefix, exp_params, sys_params)
  plot_grid('grid.png', exp_params, sys_params, 6, 0.005, pos, nearest=3)
  
  # Save summary statistics.
  s = 2 * exp_params['half_span'] + 1
  shape = (len(exp_params['pulse_ct']), len(exp_params['sig_n']), s, s)
  asym_res = { 'cvg_prob' : np.zeros(shape, dtype=np.float),
               'mean' : np.zeros(shape, dtype=np.complex),
               'rmse' : np.zeros(shape, dtype=np.float),
               'area' : np.zeros(shape, dtype=np.float),
               'ecc' : np.zeros(shape, dtype=np.float),
               'avg_area' : np.zeros(shape, dtype=np.float),
               'avg_ecc' : np.zeros(shape, dtype=np.float),
               'area_ratio' : np.zeros(shape, dtype=np.float) }
  boot_res = copy.deepcopy(asym_res)
  center = exp_params['center']
  s = 2 * exp_params['half_span'] + 1
  shape = (len(exp_params['pulse_ct']), len(exp_params['sig_n']), 1, 1, exp_params['trials'])
  for e in range(s):
    for n in range(s):
      print e,n
      (P, cov, _, _) = load(prefix, add=POS_EXT_FMT % (e,n))
      pos = np.zeros(shape, dtype=np.complex)
      pos[:,:,0,0,:] = P
      cov_asym = create_array_from_shape(shape)
      cov_boot = create_array_from_shape(shape)
      for i in range(shape[0]): 
        for j in range(shape[1]):
          cov_asym[i][j][0][0] = cov[0][i][j]
          cov_boot[i][j][0][0] = cov[1][i][j]
      p = center + np.complex((n - exp_params['half_span']) * exp_params['scale'], 
                              (e - exp_params['half_span']) * exp_params['scale'])
      exp_params['center'] = p
      asym = generate_report(pos, cov_asym, exp_params, sys_params, conf_level, offset=False)
      boot = generate_report(pos, cov_boot, exp_params, sys_params, conf_level, offset=False)
      for key in asym_res.keys():
        asym_res[key][:,:,e,n] = asym[key][:,:,0,0]
        boot_res[key][:,:,e,n] = boot[key][:,:,0,0]
  exp_params['center'] = center
  pickle.dump((asym_res, boot_res), open(prefix + '-stats', 'w'))

  # Plot summary statistics.
  (asym_res, boot_res) = pickle.load(open(prefix + '-stats'))
  I = len(exp_params['pulse_ct'])
  J = len(exp_params['sig_n'])

  feature = 'cvg_prob'
  title = 'Coverage probability'
  mean = np.zeros((2,I,J), dtype=np.float)
  std  = np.zeros((2,I,J), dtype=np.float)
  for i in range(I): 
    for j in range(J): 
      A = asym_res[feature][i,j].flat[~np.isnan(asym_res[feature][i,j].flat)]
      mean[0,i,j] = np.mean(A)
      std[0,i,j] =  np.std(A)
      B = boot_res[feature][i,j].flat[~np.isnan(boot_res[feature][i,j].flat)]
      mean[1,i,j] = np.mean(B)
      std[1,i,j] =  np.std(B)
  
  pp.rc('text', usetex=True)
  pp.rc('font', family='serif')
  fig, axs = pp.subplots(nrows=1, ncols=2, sharex=True)
  fig.set_size_inches(10,3.5)
  ax0 = axs[0]
  ax0.set_xscale('log')
  ax0.set_xlim([exp_params['sig_n'][0]/2, exp_params['sig_n'][-1]*2])
  ax0.set_xlabel('$\sigma_n^2$')
  ax0.set_ylabel('Coverage probability')
  ax0.set_title('Asymptotic')
  ax1 = axs[1]
  ax1.set_xscale('log')
  ax1.set_title('Bootstrap')
  ax1.set_xlim([exp_params['sig_n'][0]/2, exp_params['sig_n'][-1]*2])
  ax1.set_xlabel('$\sigma_n^2$')
  
  for i, pulse_ct in enumerate(exp_params['pulse_ct']):
    ax0.errorbar(exp_params['sig_n'], mean[0,i,:], yerr=std[0,i,:], 
      fmt='o', label='%d' % pulse_ct)
    ax1.errorbar(exp_params['sig_n'], mean[1,i,:], yerr=std[1,i,:], 
      fmt='o', label='%d' % pulse_ct)
    
  pp.legend(title='Samples per site', ncol=1, bbox_to_anchor=(1.05,1), loc=2, borderaxespad=0)
  pp.savefig('cvg_prob.png', dpi=300, bbox_inches='tight')
  pp.clf()


### Testing, testing ... ######################################################

if __name__ == '__main__':

  cal_id = 3   
  db_con = util.get_db('reader')
  sv = signal1.SteeringVectors(db_con, cal_id)
  sites = util.get_sites(db_con)
  (center, zone) = util.get_center(db_con)

  #### GRID ###################################################################
  grid_test('exp/boot', center, sites, sv, 0.95)

