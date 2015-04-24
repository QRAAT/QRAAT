# sim.py -- Run simulations. 

import util
import signal1
import position1

import pickle, gzip, os
import numpy as np
import matplotlib.pyplot as pp
import matplotlib.colors as colors
import matplotlib.patches as patches
import matplotlib.cm as cmx
import scipy


### SIMULATION ################################################################

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
    cov0 = create_array(exp_params, sys_params) # Asymptotic 
    cov1 = create_array(exp_params, sys_params) # Bootstrap
  else: 
    cov0 = cov1 = None

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
            if nearest is None:
              include = sys_params['include']
            else: 
              include = nearest_sites(P, sites, nearest)
            sig = signal1.Simulator(P, sites, sv_splines, scaled_rho, sig_n, pulse_ct, include)
          
            # Estimate position.
            P_hat = position1.PositionEstimator(999, sites, P, sig, sv, method, 
                                                  s=15, m=2, n=-1, delta=10)
            pos[i,j,e,n,k] = P_hat.p

            # Estimate confidence region. 
            if compute_cov:
              cov0[i][j][e][n].append(position1.Covariance(P_hat, sites, p_known=P))
              cov1[i][j][e][n].append(None)
              #try: 
              #  cov1[i][j][e][n].append(position1.BootstrapCovariance(P_hat, sites))
              #except np.linalg.linalg.LinAlgError:
              #  print "Singular matrix!"
              #  cov1[i][j][e][n].append(None)
          print n,
        print
  return (pos, (cov0, cov1))

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
                                                  s=15, m=3, n=-1, delta=10)
            pos_bartlet[i,j,e,n,k] = A.p
            B = position1.PositionEstimator(999, sites, P, sig, sv, signal1.Signal.MLE, 
                                                  s=15, m=3, n=-1, delta=10)
            pos_mle[i,j,e,n,k] = B.p
          print n,
        print
  return (pos_bartlet, pos_mle)



### SAVE RESULTS ##############################################################

def save(prefix, pos, cov, exp_params, sys_params,):
  np.savez(prefix + '-pos', pos)
  pickle.dump(cov[0], open(prefix + '-cov0', 'w'))
  pickle.dump(cov[1], open(prefix + '-cov1', 'w'))
  pickle.dump((exp_params, sys_params), open(prefix + '-params', 'w'))

def load(prefix):
  pos = np.load(prefix + '-pos.npz')['arr_0']
  cov0 = pickle.load(open(prefix + '-cov0', 'r'))
  cov1 = pickle.load(open(prefix + '-cov1', 'r'))
  (exp_params, sys_params) = pickle.load(open(prefix + '-params'))
  return (pos, (cov0, cov1), exp_params, sys_params)
  

### SUMARIZE RESULTS ##########################################################

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
              if cov[i][j][e][n][k] is not None: 
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



### PLOTTING ##################################################################

def plot_grid(fn, exp_params, sys_params, pulse_ct, sig_n, pos=None, nearest=None, alpha=0.1):
  i = exp_params['pulse_ct'].index(pulse_ct)
  j = exp_params['sig_n'].index(sig_n)
  
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
  pp.scatter(X, Y, label='estimates', alpha=alpha, facecolors='b', edgecolors='none', s=5)

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
  ax.set_xlabel('Distance to site 2 (m)')
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
  axarr[1].set_xlabel('Angle between sites 1 and 2')
  pp.savefig(fn, dpi=300, bbox_inches='tight')
  pp.clf()
  
  



### EXPERIMENTS ###############################################################

def conf_test(prefix, center, sites, sv, conf_level): 
  
  exp_params = { 'rho'       : 1,
                 'sig_n'     : [0.001, 0.01, 0.1],#[0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1],
                 'pulse_ct'  : [10,20,50,100],#[3,4,5,6,7,8,9,10],
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
  #(pos, cov, exp_params, sys_params) = load(prefix)
  print "Covariance\n"
  pretty_report(pos, cov[0], exp_params, sys_params, conf_level)
  #print "BootstrapCovariance\n"
  #pretty_report(pos, cov[1], exp_params, sys_params, conf_level)


def grid_test(prefix, center, sites, sv, conf_level): 
  
  exp_params = { 'rho'       : 1,
                 'sig_n'     : [0.005],
                 'pulse_ct'  : [5],
                 'center'    : (4260738.3+574549j), 
                 'half_span' : 3,
                 'scale'     : 300,
                 'trials'    : 1000 }

  sys_params = { 'method'  : 'bartlet', 
                 'include' : [],
                 'center'  : center,
                 'sites'   : sites } 

  (pos, cov) = montecarlo(exp_params, sys_params, sv, compute_cov=True, nearest=3)
  save(prefix, pos, cov, exp_params, sys_params)
  print "Covariance\n"
  pretty_report(pos, cov[0], exp_params, sys_params, conf_level)
  print "Covariance2\n"
  pretty_report(pos, cov[1], exp_params, sys_params, conf_level)
  print "BootstrapCovariance\n"
  pretty_report(pos, cov[2], exp_params, sys_params, conf_level)
  plot_grid('grid.png', exp_params, sys_params, 
      exp_params['pulse_ct'][0], exp_params['sig_n'][0], pos, nearest=3)


def contour_test(prefix, center, sites, sv, conf_level): 
  
  exp_params = { 'rho'       : 1,
                 'sig_n'     : [0.005],
                 'pulse_ct'  : [5],
                 'center'    : (4260738.3+574549j), 
                 'half_span' : 3 * 12,
                 'scale'     : 300 / 12,
                 'trials'    : 100 }

  sys_params = { 'method'  : 'bartlet', 
                 'include' : [],
                 'center'  : center,
                 'sites'   : sites } 

  #(pos, cov) = montecarlo(exp_params, sys_params, sv, compute_cov=False)
  #save(prefix, pos, cov, exp_params, sys_params)
  (pos, cov, exp_params, sys_params) = load(prefix)
  plot_grid('contour_grid.png', exp_params, sys_params, 
      exp_params['pulse_ct'][0], exp_params['sig_n'][0])
  plot_contour('contour.png', exp_params, sys_params, 
      exp_params['pulse_ct'][0], exp_params['sig_n'][0], pos, conf_level)


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
    (P, cov, exp_params, sys_params) = load(prefix + str(i))
    sys_params['sites'][1] += step
    pos.append(P) 
  sys_params['sites'] = sites
  plot_distance('dist.png', pos, exp_params, sys_params, 
      exp_params['pulse_ct'][0], exp_params['sig_n'][0], conf_level, step)



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

 

### Testing, testing ... ######################################################

if __name__ == '__main__':

  cal_id = 3   
  db_con = util.get_db('reader')
  sv = signal1.SteeringVectors(db_con, cal_id)
  sites = util.get_sites(db_con)
  (center, zone) = util.get_center(db_con)
 
  #### SPECTRUM ##############################################################
  #spectrum_test(db_con, 'exp/spectrum', center, 0.95)

  #### DISTANCE ###############################################################
  #distance_test(db_con, 'exp/dist', center, 0.95)
  
  #### ANGLE ##################################################################
  #angular_test(db_con, 'exp/angle', center, 0.95)

  #### GRID ###################################################################
  #grid_test('exp/grid', center, sites, sv, 0.95)

  #### CONTOUR ###################################################################
  #contour_test('exp/contour', center, sites, sv, 0.95)
  
  #### CONF ###################################################################
  conf_test('exp/asym', center, sites, sv, 0.95)
