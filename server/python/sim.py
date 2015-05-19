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

JOBS = 2 # Number of processes to spawn in montecarlo_huge()

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

def montecarlo(exp_params, sys_params, sv, nearest=None, max_dist=None, compute_cov=True, scale_tx_pwr=True):
  s = 2 * exp_params['half_span'] + 1
  shape = (len(exp_params['pulse_ct']), len(exp_params['sig_n']), s, s, exp_params['trials'])
  pos = np.zeros(shape, dtype=np.complex)
  if compute_cov:
    cov_asym = create_array_from_params(exp_params, sys_params) # Asymptotic 
    cov_boot = create_array_from_params(exp_params, sys_params) # Bootstrap
  else: 
    cov_asym = cov_boot = None

  if sys_params['method'] == 'bartlet': 
    method = signal1.Signal.Bartlet
  elif sys_params['method'] == 'mle': 
    method = signal1.Signal.MLE
  else: raise Exception('Unknown method')

  sites = sys_params['sites']
  
  # Fix transmission power. 
  if scale_tx_pwr: 
    scaled_rho = signal1.scale_tx_coeff(exp_params['center'], 
                                        exp_params['rho'],
                                        sites,
                                        sys_params['include'])
  else: 
    scaled_rho = exp_params['rho']
  
  # Interpolate steering vector splines.
  sv_splines = signal1.compute_bearing_splines(sv)

  for i, pulse_ct in enumerate(exp_params['pulse_ct']): 
    print 'pulse_ct=%d' % pulse_ct
    for j, sig_n in enumerate(exp_params['sig_n']): 
      print '  sig_n=%f' % sig_n
      for e in range(s): #easting 
        print e, '|',
        for n in range(s): #northing
          P = exp_params['center']  + np.complex((n - exp_params['half_span']) * exp_params['scale'], 
                                                 (e - exp_params['half_span']) * exp_params['scale'])
          if nearest is not None and max_dist is not None: 
            raise Exception("Use either `nearest` or `max_dist`, not both.")
          elif nearest is not None:
            include = nearest_sites(P, sites, nearest)
          elif max_dist is not None:
            include = sites_within_dist(P, sites, max_dist)
          else: 
            include = sys_params['include']

          for k in range(exp_params['trials']): 
            # Run simulation.
            sig = signal1.Simulator(P, sites, sv_splines, scaled_rho, sig_n, pulse_ct, include)
          
            # Estimate position.
            # NOTE For convergence test use `sys_params['center']` for initial guess 
            # instead of `P`. The true position is used here to assure convergence to 
            # the global maximum. 
            P_hat = position1.PositionEstimator(999, sites, P, sig, sv, method, 
                             s=POS_EST_S, m=POS_EST_M, n=POS_EST_N, delta=POS_EST_DELTA)
            pos[i,j,e,n,k] = P_hat.p

            # Estimate confidence region. 
            if compute_cov:
              cov_asym[i][j][e][n].append(position1.Covariance(P_hat, sites, p_known=P))
              try: 
                cov_boot[i][j][e][n].append(position1.BootstrapCovariance(P_hat, sites))
              except np.linalg.linalg.LinAlgError:
                print "Singular matrix!"
                cov_boot[i][j][e][n].append(None)
          print n,
        print
  return (pos, (cov_asym, cov_boot))


def montecarlo_huge(prefix, exp_params, sys_params, sv, nearest=None, compute_cov=True):
  s = 2 * exp_params['half_span'] + 1
  shape = (len(exp_params['pulse_ct']), len(exp_params['sig_n']), exp_params['trials'])

  if sys_params['method'] == 'bartlet': 
    method = signal1.Signal.Bartlet
  elif sys_params['method'] == 'mle': 
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
            cov_asym[i][j].append(position1.Covariance(P_hat, sites, p_known=P))
            try: 
              cov_boot[i][j].append(position1.BootstrapCovariance(P_hat, sites))
            except np.linalg.linalg.LinAlgError:
              print "Singular matrix!"
              cov_boot[i][j].append(None)

    # Save intermediate results. 
    save(prefix, pos, (cov_asym, cov_boot), 
      exp_params, sys_params, add=POS_EXT_FMT % (e, n))


def montecarlo_spectrum(exp_params, sys_params, sv):
  ''' MLE / Bartlet. ''' 
  s = 2 * exp_params['half_span'] + 1
  shape = (len(exp_params['pulse_ct']), len(exp_params['sig_n']), s, s, exp_params['trials'])
  pos_bartlet = np.zeros(shape, dtype=np.complex)
  pos_mle = np.zeros(shape, dtype=np.complex)

  sites = sys_params['sites']
  include = sys_params['include']
  
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
        print e, '|',
        for n in range(s): #northing
          P = exp_params['center']  + np.complex((n - exp_params['half_span']) * exp_params['scale'], 
                                                 (e - exp_params['half_span']) * exp_params['scale'])
          for k in range(exp_params['trials']): 
            # Run simulation.
            sig = signal1.Simulator(P, sites, sv_splines, scaled_rho, sig_n, pulse_ct, include)
          
            # Estimate position.
            A = position1.PositionEstimator(999, sites, P, sig, sv, signal1.Signal.Bartlet, 
                             s=POS_EST_S, m=POS_EST_M, n=POS_EST_N, delta=POS_EST_DELTA)
            pos_bartlet[i,j,e,n,k] = A.p
            B = position1.PositionEstimator(999, sites, P, sig, sv, signal1.Signal.MLE, 
                             s=POS_EST_S, m=POS_EST_M, n=POS_EST_N, delta=POS_EST_DELTA)
            pos_mle[i,j,e,n,k] = B.p
          print n,
        print
  return (pos_bartlet, pos_mle)



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



def plot_distribution(fn, exp_params, sys_params, pulse_ct, sig_n, pos, alpha=0.1):
  i = exp_params['pulse_ct'].index(pulse_ct)
  j = exp_params['sig_n'].index(sig_n)
  e = 0; n = 0;
  
  pp.rc('text', usetex=True)
  pp.rc('font', family='serif')
  
  fig = pp.gcf()
  fig.set_size_inches(4,2)
  ax = fig.add_subplot(111)
  ax.axis('equal')
  ax.set_xlabel('easting (m)')
  ax.set_ylabel('northing (m)')

  X = np.imag(pos[i,j,e,n].flat)
  Y = np.real(pos[i,j,e,n].flat)
  
  pp.scatter(X, Y, label='estimates', alpha=alpha, facecolors='b', edgecolors='none', s=5)
  pp.xlim([np.min(X) - 0, np.max(X) + 0])
  pp.ylim([np.min(Y) - 0, np.max(Y) + 0])
  l = np.max(X) - 10; h = np.max(Y) - 10

  p = exp_params['center']  + np.complex((n - exp_params['half_span']) * exp_params['scale'], 
                                         (e - exp_params['half_span']) * exp_params['scale'])
  pp.plot(p.imag, p.real, label='grid', color='w', marker='o', ms=5)
  
  pp.savefig(fn, dpi=300, bbox_inches='tight')
  pp.clf()



def plot_contour(fn, exp_params, sys_params, pulse_ct, sig_n, pos, conf_level):
  i = exp_params['pulse_ct'].index(pulse_ct)
  j = exp_params['sig_n'].index(sig_n)
  Qt = scipy.stats.chi2.ppf(conf_level, 2)
  
  fig = pp.gcf()
  fig.set_size_inches(12,10)
  ax = fig.add_subplot(111)
  ax.axis('equal')
  ax.set_xlabel('easting (m)')
  ax.set_ylabel('northing (m)')

  s = 2 * exp_params['half_span'] + 1


  # Plot positions.
  angle = np.zeros((s,s), dtype=float)
  eccentricity = np.zeros((s,s), dtype=float)
  area = np.zeros((s,s), dtype=float)
  for e in range(s): #easting 
    for n in range(s): #northing
      p = exp_params['center']  + np.complex((n - exp_params['half_span']) * exp_params['scale'], 
                                             (e - exp_params['half_span']) * exp_params['scale'])
      p_hat = pos[i,j,e,n,:]
      C = np.cov(np.imag(p_hat), np.real(p_hat))
      E = position1.Ellipse(p, *position1.compute_conf(C, Qt))
      angle[e,n] = E.angle
      eccentricity[e,n] = E.axes[1] / E.axes[0]
      area[e,n] = E.area()


  c_norm  = colors.Normalize(vmin=np.min(eccentricity), vmax=np.max(eccentricity))
  scalar_map = cmx.ScalarMappable(norm=c_norm,cmap='YlGnBu')
 
  # Eccentricity
  for e in range(s):
    for n in range(s):
      p = exp_params['center']  + np.complex((n - exp_params['half_span']) * exp_params['scale'], 
                                             (e - exp_params['half_span']) * exp_params['scale'])
      b = scalar_map.to_rgba(eccentricity[e,n])
      pp.scatter(p.imag, p.real, marker='s', color=b, edgecolors='none', s=50, alpha=0.8) 

  # Area, orientation
  area = area / np.max(area)
  weight = 0.5
  lweight = 50
  for e in range(s): #easting 
    for n in range(s): #northing
      p = exp_params['center']  + np.complex((n - exp_params['half_span']) * exp_params['scale'], 
                                             (e - exp_params['half_span']) * exp_params['scale'])
      a = area[e,n]
      dx = np.cos(angle[e,n]) * a * lweight
      dy = np.sin(angle[e,n]) * a * lweight
      pp.plot([p.imag - dx/2, p.imag + dx/2], 
              [p.real - dy/2, p.real + dy/2],
              lw=weight, color='k') 
  
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

  #X = np.imag(pos.flat)
  #Y = np.real(pos.flat)
  #pp.scatter(X, Y, label='estimates', alpha=0.1, facecolors='b', edgecolors='none', s=5)

  pp.savefig(fn, dpi=600)
  pp.clf()



def plot_distance(fn, pos, exp_params, sys_params, pulse_ct, sig_n, conf_level, step):
  i = exp_params['pulse_ct'].index(pulse_ct)
  j = exp_params['sig_n'].index(sig_n)
  Qt = scipy.stats.chi2.ppf(conf_level, 2)
  
  pp.rc('text', usetex=True)
  pp.rc('font', family='serif')
  fig = pp.gcf()
  #fig.set_size_inches(8,6)
  ax = fig.add_subplot(111)
  #ax.axis('equal')
  ax.set_xlabel('Distance to site 1 (m)')
  ax.set_ylabel('Eccentricity of ellipse')

  # Eccentricity of confidence intervals
  p  = exp_params['center']
  dist2 = np.abs(p - sys_params['sites'][1])
  D = [] # distance 
  E = [] # eccentricity
  for (k, P) in enumerate(pos): 
    C = np.cov(np.imag(P[i,j,:,:,:].flat), np.real(P[i,j,:,:,:].flat))
    (angle, axes) = position1.compute_conf(C, Qt)
    D.append(dist2 + (step * k))
    E.append(position1.Ellipse(p, angle, axes).eccentricity())
  pp.plot(D, E)
  
  l = 300; h = 0.17
  pp.text(l, h, '$\sigma_n^2=%0.3f$' % exp_params['sig_n'][j])
  pp.text(l, h-0.033, '$%d$ samples/site' % exp_params['pulse_ct'][i])
  #pp.title('Varying distance, {0}\%-confidence'.format(int(100 * conf_level)))
  pp.savefig(fn, dpi=300, bbox_inches='tight')
  pp.clf()



def plot_angular(fn, pos, site2_pos, exp_params, sys_params, pulse_ct, sig_n, conf_level, step):
  i = exp_params['pulse_ct'].index(pulse_ct)
  j = exp_params['sig_n'].index(sig_n)
  Qt = scipy.stats.chi2.ppf(conf_level, 2)
  
  pp.rc('text', usetex=True)
  pp.rc('font', family='serif')

  f, axarr = pp.subplots(2, sharex=True)

  # Plot position
  p  = exp_params['center']
  
  # Confidence intervals
  angle = []
  orientation = []
  eccentricity = []
  for (k, P) in enumerate(pos): # Plot positions.
    C = np.cov(np.imag(P[i,j,:,:,:].flat), np.real(P[i,j,:,:,:].flat))
    E = position1.Ellipse(p, *position1.compute_conf(C, Qt))
    angle.append((180 * (k+1)) / step)
    orientation.append((180 * E.angle / np.pi) % 180)
    eccentricity.append(E.eccentricity())

  axarr[0].plot(angle, orientation)
  axarr[0].set_ylabel('Orientation of major axis')
  axarr[1].plot(angle, eccentricity)
  axarr[1].set_ylabel('Eccentricity')

  #axarr[0].set_title('Varying angle, {0}\%-confidence'.format(int(100 * conf_level)))
  axarr[1].set_xlabel('Angle between sites 0 and 1')
  pp.savefig(fn, dpi=300, bbox_inches='tight')
  pp.clf()
  
  
def plot_rmse(fn, pos, p, exp_params, sys_params): 
  x = position1.transform_coord(p, exp_params['center'], 
                  exp_params['half_span'], exp_params['scale'])
  e = x[0]; n = x[1]
  
  pp.rc('text', usetex=True)
  pp.rc('font', family='serif')
  fig = pp.gcf()
  fig.set_size_inches(6,4)
  ax = fig.add_subplot(111)
  ax.set_xlabel('Samples per site')
  ax.set_ylabel('$\\textsc{Rmse}$')
  
  for (j, sig_n) in enumerate(exp_params['sig_n']):
    rmse = []
    for (i, pulse_ct) in enumerate(exp_params['pulse_ct']):
      rmse.append(
        np.sqrt(np.mean(np.abs(pos[i,j,e,n,:] - p) ** 2)))
    pp.plot(exp_params['pulse_ct'], rmse, label='$\sigma_n^2=%0.3f$' % sig_n)

  #pp.legend(title='Noise level', ncol=2)
  pp.savefig(fn, dpi=300, bbox_inches='tight')
  pp.clf()


def plot_area(fn, pos, p, exp_params, sys_params, conf_level, cov=None): 
  x = position1.transform_coord(p, exp_params['center'], 
                  exp_params['half_span'], exp_params['scale'])
  e = x[0]; n = x[1]
  Qt = scipy.stats.chi2.ppf(conf_level, 2)
  
  pp.rc('text', usetex=True)
  pp.rc('font', family='serif')
  fig = pp.gcf()
  fig.set_size_inches(6,4)
  ax = fig.add_subplot(111)
  ax.set_xlabel('Samples per site')
  ax.set_ylabel('Area of {0}\%--conf. region (m$^2$)'.format(int(100 * conf_level)))
  for (j, sig_n) in enumerate(exp_params['sig_n']):
    area = []
    for (i, pulse_ct) in enumerate(exp_params['pulse_ct']):
      p_hat = pos[i,j,e,n,:]
      C = np.cov(np.imag(p_hat), np.real(p_hat))
      (angle, axes) = position1.compute_conf(C, Qt)
      area.append(
        position1.Ellipse(p, angle, axes).area())
    pp.plot(exp_params['pulse_ct'], area, label='$\sigma_n^2=%0.3f$' % sig_n)

  pp.legend(title='Noise level', ncol=2)
  pp.savefig(fn, dpi=300, bbox_inches='tight')
  pp.clf()




### EXPERIMENTS ###############################################################


def conf_test(prefix, center, sites, sv, conf_level): 
  
  position1.NORMALIZE_SPECTRUM = True
  exp_params = { 'rho'       : 1,
                 'sig_n'     : [0.01],
                 'pulse_ct'  : [6],
                 'center'    : (4260738.3+574549j), 
                 'half_span' : 0,
                 'scale'     : 1,
                 'trials'    : 1000 }

  sys_params = { 'method'         : 'mle', 
                 'include'        : [],
                 'center'         : center,
                 'sites'          : sites } 

  (pos, cov) = montecarlo(exp_params, sys_params, sv, nearest=3, compute_cov=True)
  res = generate_report(pos, cov[1], exp_params, sys_params, conf_level)
  display_report(res, exp_params, sys_params)  


def asym_test(prefix, center, sites, sv, conf_level): 
  
  exp_params = { 'rho'       : 1,
                 'sig_n'     : [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1],
                 'pulse_ct'  : [10,20,50,100],
                 'center'    : (4260738.3+574549j), 
                 'half_span' : 2,
                 'scale'     : 350,
                 'trials'    : 1000 }

  sys_params = { 'method'  : 'bartlet', 
                 'include' : [],
                 'center'  : center,
                 'sites'   : sites } 

  # Run simulations.
  print "Running simulations"
  montecarlo_huge(prefix, exp_params, sys_params, 
                              sv, compute_cov=True, nearest=3)
  
  # Save summary statistics.
  print "Generating summary statistics"
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
      for i in range(shape[0]): 
        for j in range(shape[1]):
          cov_asym[i][j][0][0] = cov[0][i][j]
      p = center + np.complex((n - exp_params['half_span']) * exp_params['scale'], 
                              (e - exp_params['half_span']) * exp_params['scale'])
      exp_params['center'] = p
      asym = generate_report(pos, cov_asym, exp_params, sys_params, conf_level, offset=False)
      for key in asym_res.keys():
        asym_res[key][:,:,e,n] = asym[key][:,:,0,0]
  exp_params['center'] = center
  pickle.dump(asym_res, open(prefix + '-stats', 'w'))

  # Plot summary statistics.
  asym_res = pickle.load(open(prefix + '-stats'))
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
  
  pp.rc('text', usetex=True)
  pp.rc('font', family='serif')
  #fig, axs = pp.subplots(nrows=1, ncols=1, sharex=True)
  fig = pp.gcf()
  fig.set_size_inches(5,3.5)
  ax0 = fig.add_subplot(111)
  ax0.set_xscale('log')
  ax0.set_xlim([exp_params['sig_n'][0]/2, exp_params['sig_n'][-1]*2])
  ax0.set_xlabel('$\sigma_n^2$')
  ax0.set_ylabel('Coverage probability')
  #ax0.set_title('Asymptotic')
  
  for i, pulse_ct in enumerate(exp_params['pulse_ct']):
    ax0.errorbar(exp_params['sig_n'], mean[0,i,:], yerr=std[0,i,:], 
      fmt='o', label='%d' % pulse_ct)
    
  pp.legend(title='Samples per site', ncol=1, bbox_to_anchor=(1.05,1), loc=2, borderaxespad=0)
  pp.savefig('asym_cvg_prob.png', dpi=300, bbox_inches='tight')
  pp.clf()

# asym_test()


def grid_test(prefix, center, sites, sv, conf_level): 
  
  exp_params = { 'rho'       : 1,
                 'sig_n'     : [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1],
                 'pulse_ct'  : [2,4,6,8,10],
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

# grid_test()


def contour_test(prefix, center, sites, sv, conf_level): 
  
  exp_params = { 'rho'       : 74101.39, # Scaled so that contour_test() and grid_test() are comparable. 
                 'sig_n'     : None, 
                 'pulse_ct'  : [5],
                 'center'    : (4260738.3+574549j), 
                 'half_span' : 50,
                 'scale'     : 25,
                 'trials'    : 1000 }

  sys_params = { 'method'  : 'bartlet', 
                 'include' : [],
                 'center'  : center,
                 'sites'   : sites } 

  # Spawn a process for each noise level. 
  proc = []
  for sig_n in [0.001, 0.01, 0.1]:
    proc.append( Process(target=_contour_test, args=(exp_params, sys_params, sv, sig_n)) )
    proc[-1].start()

  # Wait for them to finish. 
  for i in range(3): 
    proc[i].join()
    
  sig_n = 0.001
  (pos, cov, exp_params, sys_params) = load(prefix+('-%0.3f' % sig_n))
  plot_grid('contour-grid.png', exp_params, sys_params,
       exp_params['pulse_ct'][0], exp_params['sig_n'][0], pos)
  plot_contour('contour.png', exp_params, sys_params, 
       exp_params['pulse_ct'][0], exp_params['sig_n'][0], pos, conf_level)

def _contour_test(exp_params, sys_params, sv, sig_n):
  exp_params['sig_n'] = [sig_n]
  (pos, cov) = montecarlo(exp_params, sys_params, sv, 
      max_dist=1000, compute_cov=False, scale_tx_pwr=False)
  save(prefix+('-%0.3f' % sig_n), pos, cov, exp_params, sys_params)

# contour_test()


def convergence_test(prefix, center, sites, sv, conf_level): 
    
  exp_params = { 'rho'       : 1,
                 'sig_n'     : [0.001],
                 'pulse_ct'  : [10],
                 #'center'    : 4260738.3+575199j + 0-50j,
                 'center'    : (4260738.3+574549j), 
                 'half_span' : 6,
                 'scale'     : 150,
                 'trials'    : 10 }

  sys_params = { 'method'         : 'bartlet', 
                 'include'        : [],
                 'center'         : center,
                 'sites'          : sites } 

  (pos, cov) = montecarlo(exp_params, sys_params, sv, max_dist=1000, compute_cov=False)
  plot_grid('convergence.png', exp_params, sys_params, 10, 0.001, pos)


def one_test(db_con, prefix, conf_level):
  
  cal_id = 6
  sv = signal1.SteeringVectors(db_con, cal_id, include=[0])
  sv.steering_vectors[1] = sv.steering_vectors[0]
  sv.bearings[1] = sv.bearings[0]
  sv.sv_id[1] = sv.sv_id[0]

  sites = { 0 : (0+100j), 
            1 : (100+0j) } 

  exp_params = { 'rho'       : 1,
                 'sig_n'     : [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1],
                 'pulse_ct'  : [1,2,3,4,5,6,7,8,9,10],
                 'center'    : (0+0j), 
                 'half_span' : 0,
                 'scale'     : 1,
                 'trials'    : 10000 }
                 

  sys_params = { 'method'  : 'bartlet', 
                 'include' : [],
                 'sites'   : sites.copy() } 
  
  #(pos, cov) = montecarlo(exp_params, sys_params, sv, compute_cov=False)
  #save(prefix, pos, cov, exp_params, sys_params)
  (pos, _, exp_params, sys_params) = load(prefix)
  #plot_rmse('rmse.png', pos, exp_params['center'], exp_params, sys_params)
  #plot_area('area.png', pos, exp_params['center'], exp_params, sys_params, 0.95)
  plot_grid('noise-sample-ill.png', exp_params, sys_params, 5, 0.1, pos)
  #report(pos, None, exp_params, sys_params, conf_level)


def spectrum_test(db_con, prefix, center, conf_level): 
  
  cal_id = 6
  sv = signal1.SteeringVectors(db_con, cal_id, include=[0])
  sv.steering_vectors[1] = sv.steering_vectors[0]
  sv.bearings[1] = sv.bearings[0]
  sv.sv_id[1] = sv.sv_id[0]
  
  sites = { 0 : (0+100j), 
            1 : (200+50j) } 

  exp_params = { 'rho'       : 1,
                 'sig_n'     : [0.5],
                 'pulse_ct'  : [5],
                 'center'    : (0+0j), 
                 'half_span' : 0,
                 'scale'     : 1,
                 'trials'    : 10 }

  sys_params = { 'include'        : [],
                 'sites'          : sites } 

  (pos_bartlet, pos_mle) = montecarlo_spectrum(exp_params, sys_params, sv)
  plot_grid('pos_bartlet.png', exp_params, sys_params, 
    exp_params['pulse_ct'][0], exp_params['sig_n'][0], pos_bartlet, alpha=1)
  plot_grid('pos_mle.png', exp_params, sys_params, 
    exp_params['pulse_ct'][0], exp_params['sig_n'][0], pos_mle, alpha=1)


def distance_test(db_con, prefix, center, conf_level):
  
  cal_id = 6
  sv = signal1.SteeringVectors(db_con, cal_id, include=[0])
  sv.steering_vectors[1] = sv.steering_vectors[0]
  sv.bearings[1] = sv.bearings[0]
  sv.sv_id[1] = sv.sv_id[0]

  sites = { 0 : (0+100j), 
            1 : (100+0j) } 

  exp_params = { 'rho'       : 1,
                 'sig_n'     : [0.005],
                 'pulse_ct'  : [5],
                 'center'    : (0+0j), 
                 'half_span' : 0,
                 'scale'     : 1,
                 'trials'    : 10000 }
                 

  sys_params = { 'method'  : 'bartlet', 
                 'include' : [],
                 'center'  : center,
                 'sites'   : sites.copy() } 
  
  pos = []
  step = 5
  for i in range(50):
    #(P, cov) = montecarlo(exp_params, sys_params, sv, compute_cov=False)
    #save(prefix + str(i), P, cov, exp_params, sys_params)
    (P, _, exp_params, sys_params) = load(prefix + str(i))
    sys_params['sites'][1] += step
    pos.append(P) 
  sys_params['sites'] = sites
  plot_distance('dist.png', pos, exp_params, sys_params, 
      exp_params['pulse_ct'][0], exp_params['sig_n'][0], conf_level, step)
  plot_distribution('dist-ill.png', exp_params, sys_params, 
    exp_params['pulse_ct'][0], exp_params['sig_n'][0], pos[20], alpha=0.1)
      

def angular_test(db_con, prefix, center, conf_level):
  
  cal_id = 6
  sv = signal1.SteeringVectors(db_con, cal_id, include=[0])
  sv.steering_vectors[1] = sv.steering_vectors[0]
  sv.bearings[1] = sv.bearings[0]
  sv.sv_id[1] = sv.sv_id[0]

  sites = { 0 : (0+100j), 
            1 : (0-100j) } 

  exp_params = { 'rho'       : 1,
                 'sig_n'     : [0.005],
                 'pulse_ct'  : [5],
                 'center'    : (0+0j), 
                 'half_span' : 0,
                 'scale'     : 1,
                 'trials'    : 10000 }
                 
  sys_params = { 'method'  : 'bartlet', 
                 'include' : [],
                 'center'  : center,
                 'sites'   : sites.copy() } 
  step = 40
  # NOTE if `step` is too large than the position estimator won't 
  # converge on extreme angles!
  p = np.array([sys_params['sites'][0].imag, 
                sys_params['sites'][0].real]) 
  c = np.array([exp_params['center'].imag, 
                exp_params['center'].real])
  
  pos = []; site2_pos = []
  for i in range(step-1):
    theta = (np.pi * (i+1)) / step
    A = np.array([[  np.cos(theta), np.sin(theta) ], 
                  [ -np.sin(theta), np.cos(theta) ]])
    b = np.dot(A, p-c) + c
    site2_pos.append(b)
    sys_params['sites'][1] = np.complex(b[1], b[0])
    #(P, cov) = montecarlo(exp_params, sys_params, sv, compute_cov=False)
    #save(prefix + str(i), P, cov, exp_params, sys_params)
    (P, cov, exp_params, sys_params) = load(prefix + str(i))
    pos.append(P)
  site2_pos = np.vstack(site2_pos)

  plot_angular('angle.png', pos, site2_pos, exp_params, sys_params, 
                exp_params['pulse_ct'][0], exp_params['sig_n'][0], conf_level, step)
  plot_distribution('angle-ill.png', exp_params, sys_params, 
    exp_params['pulse_ct'][0], exp_params['sig_n'][0], pos[30], alpha=0.1)

 

### Testing, testing ... ######################################################

if __name__ == '__main__':

  cal_id = 3   
  db_con = util.get_db('reader')
  sv = signal1.SteeringVectors(db_con, cal_id)
  sites = util.get_sites(db_con)
  (center, zone) = util.get_center(db_con)

  conf_test('exp/test', center, sites, sv, 0.95)

  #### ONE ###################################################################
  #one_test(db_con, 'exp/one', 0.95)

  #### SPECTRUM ##############################################################
  #spectrum_test(db_con, 'exp/spectrum', center, 0.95)

  #### DISTANCE ###############################################################
  #distance_test(db_con, 'exp/dist', center, 0.95)
  
  #### ANGLE ##################################################################
  #angular_test(db_con, 'exp/angle', center, 0.95)

  #### GRID ###################################################################
  #grid_test('exp/grid', center, sites, sv, 0.95)

  #### CONTOUR ################################################################
  #contour_test('exp/contour', center, sites, sv, 0.95)
  
  #### ASYMPTOTIC-CONF#########################################################
  #asym_test('exp/asym', center, sites, sv, 0.95)
