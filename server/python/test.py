# Test code for position estimation. To run, you'll need the following
# Python packages:
#  utm, numdifftools (available through pip)
#  numpy, scipy, matplotlib 

import signal, position1
import util
import numpy as np
import matplotlib.pyplot as pp

cal_id = 3   # Calibration ID, specifies steering vectors to use. 
dep_id = 105 # Deployment ID, specifies a transmitter. 

# siteID -> UTM position, known positions of sites for source
# localization. The real component is northing, the imaginary
# component is easting. 
sites = {2 : (4261604.51+574239.47j), # site2
         3 : (4261569.32+575013.86j), # site10
         4 : (4260706.17+573882.15j), # site13
         5 : (4260749.75+575321.92j), # site20
         6 : (4260856.82+574794.06j), # site21
         8 : (4261100.56+574000.17j)  # site39
         }
         
# UTM position, initial guess of position.
center = (4260500+574500j) 

zone = (10, 'S') # UTM zone.

# Read steering vectors from file.
db_con = util.get_db('reader')
sv = signal.SteeringVectors(db_con, cal_id)


def real_data():

  # Read signal data, about an hour's worth.
  sv = signal.SteeringVectors.read(3, 'sample/sv')
  sig = signal.Signal.read(sites.keys(), 'sample/sig')
 
  fn = 'two'

  t_step=15
  t_win=30
  positions = position1.WindowedPositionEstimator(dep_id, sites, center, sig, sv, 
                             t_step, t_win, method=signal.Signal.Bartlet)
  
  C = {}
  P = {}
  for pos in positions:
    site_ids = tuple(sorted(pos.splines.keys()))
    if len(site_ids) < 2: 
      continue

    if P.get(site_ids) is None:
      P[site_ids] = []
      C[site_ids] = []
    
    P[site_ids].append(pos.p)
    if pos.p is not None: 
      try: 
        E = position1.BootstrapCovariance(pos, sites).conf(0.95)
        C[site_ids].append(E)
        print 'Ok'
      except np.linalg.linalg.LinAlgError, position1.PosDefError: 
        C[site_ids].append(None)
        print 'bad!'
      except position1.BootstrapError:
        C[site_ids].append(None)
        print 'samples ... '
    else: 
      C[site_ids].append(None)

  p = np.complex(4260841.157, 574045.288889)

  for (site_ids, pos) in P.iteritems(): 
    
    pos = filter(lambda x: x!=None, pos)
    print site_ids, len(pos), np.mean(pos),

    count = 0; total = 0
    for E in C[site_ids]:
      if E is not None:
        total += 1
        if p in E: 
          count += 1
   
    if total == 0:
      print 'bad'
    else: print "%0.1f" % (100 * (float(count) / total))

    X = np.imag(pos)
    Y = np.real(pos)
    
    fig = pp.gcf()
    ax = fig.add_subplot(111)
    ax.axis('equal')
    ax.set_xlabel('easting (m)')
    ax.set_ylabel('northing (m)')
    pp.scatter(X, Y, alpha=1, facecolors='b', edgecolors='none')
    pp.plot(p.imag, p.real, color='w', marker='o')
    pp.title("%s" % str(site_ids))
    pp.savefig("%s%s.png" % (fn, ''.join(map(lambda x: str(x), site_ids))))
    pp.clf()

def sim_data():

  # Simpulate signal given known position p.  
  p = center + complex(650,0)
  include = [2,4,6,8]

  sig_n = 0.002 # noise
  rho = signal.scale_tx_coeff(p, 1, sites, include)
  sv_splines = signal.compute_bearing_splines(sv)
  sig = signal.Simulator(p, sites, sv_splines, rho, sig_n, 10, include)
    
  (sig_n, sig_t) = sig.estimate_var()

  pos = position1.PositionEstimator(999, sites, center, 
                               sig, sv, method=signal.Signal.Bartlet)
  pos.plot('fella.png', sites, center, p)
 
  level=0.95
  position1.BootstrapCovariance(pos, sites).conf(level).display(p)
  position1.BootstrapCovariance2(pos, sites).conf(level).display(p)
  #position1.Covariance(pos, sites, p_known=p).conf(level).display(p)


# Testing, testing .... 
sim_data()
