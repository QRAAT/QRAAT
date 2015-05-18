# Testing, testing ... 
'''
Observations so far: 

  1. Better to not normalize bearing spectrum. For the woodrat transmitters 
     (dep_id=61 and whatever is in sample/) it doesn't make a difference, but
     the distribution looks way better for the beacon when the spectra are not
     normalized.

  2. BootstrapCovariance performance is better with small sample windows! What
     about alternate subsampling method for smaller sample sizes? 

'''


import util
import position1, signal1
import numpy as np
import matplotlib.pyplot as pp
import pickle

position1.NORMALIZE_SPECTRUM=False
cal_id = 3
t_step = 60
t_win = 5
t_chunk = 3600 / 4 
conf_level=0.95

dep_id = 60
t_start = 1383098400.514320 + (t_chunk * 49) 
#t_end = t_start + (3600)
t_end = 1383443999.351099
fn = 'nonorm'

#dep_id = 61
#t_start = 1396725598.548015
#t_end = 1396732325.777558
#fn = 'walking'

# Location of site34. 
site34 = np.complex(4260910.87, 574296.45)


def process(sv):  

  ct = 1; good = 0; total = 0
  P = {} # site_id's --> position estimate
  C = {} # site_id's --> confidence region estimate
  for t in np.arange(t_start, t_end+t_chunk, t_chunk):
      
    print "chunk", ct; ct+=1

    # Signal data
    sig = signal1.Signal(db_con, dep_id, t, t+t_chunk)
    if sig.t_start == float("+inf"):
      continue

    # Compute positions
    positions = position1.WindowedPositionEstimator(dep_id, sites, center, sig, sv, 
                             t_step, t_win, method=signal1.Signal.Bartlet)
   
    for pos in positions:

      print pos.splines.keys(), 
      site_ids = tuple(set(pos.splines.keys()))
      if P.get(site_ids) is None:
        P[site_ids] = []
        C[site_ids] = []
      
      #pos.plot('fella', sites, center, p_known=site34)
      #assert False

      P[site_ids].append(pos.p)
      
      if pos.p is not None:
        try: 
          cov = position1.BootstrapCovariance(pos, sites, max_resamples=200)
          E = cov.conf(conf_level)
          C[site_ids].append((E.angle, E.axes[0], E.axes[1]))
          print "Ok"
          good += 1
        except np.linalg.linalg.LinAlgError: 
          C[site_ids].append(None)
          print "non positive indefinite"
        except position1.PosDefError: 
          C[site_ids].append(None)
          print "non positive indefinite (PosDefError)"
        except position1.BootstrapError:
          C[site_ids].append(None)
          print "samples ..." 
      else: C[site_ids].append(None)
      total += 1

  print 'good', good, "out of", total, "(t_win=%d, norm=%s)" % (
                              t_win, position1.NORMALIZE_SPECTRUM)
  return (P, C)


if __name__ == '__main__':  
  db_con = util.get_db('reader')
  
  # System params 
  sv = signal1.SteeringVectors(db_con, cal_id)
  sites = util.get_sites(db_con)
  (center, zone) = util.get_center(db_con)
  
  P, C = process(sv)
  pickle.dump((P, C), open(fn+'-data', 'w'))

  for (site_ids, pos) in P.iteritems(): 

    if len(site_ids) == 1: 
      print "skpping", site_ids
      continue
    print site_ids, 'mean', np.mean(pos), len(pos)
  
    fig = pp.gcf()
    ax = fig.add_subplot(111)
    ax.axis('equal')
    ax.set_xlabel('easting (m)')
    ax.set_ylabel('northing (m)')

    X = np.imag(pos)
    Y = np.real(pos)
    pp.scatter(X, Y, alpha=0.2, facecolors='b', edgecolors='none', s=5)

    pp.plot(site34.imag, site34.real, color='w', marker='o', ms=3)
    
    pp.title("%s" % str(site_ids))
    pp.savefig("%s%s.png" % (fn, ''.join(map(lambda x: str(x), site_ids))))
    pp.clf()

