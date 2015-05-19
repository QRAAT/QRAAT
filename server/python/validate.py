# Testing, testing ... 
'''
Observations so far: 

  1. Better to not normalize bearing spectrum. For the woodrat transmitters 
     (dep_id=61 and whatever is in sample/) it doesn't make a difference, but
     the distribution looks way better for the beacon when the spectra are not
     normalized.

  2. Distribution of estimates does indeed depend on geometry. Moreover, referring
     to the beacon data, the mean is different for different sets of sites, 
     suggesting the estimates are biased. The distribution appears normal in 
     some cases, but not in others. Perhaps as a result of interference? 

  3. The covariance is more likely to be positive definite with smaller sample 
     sizes. This is consistent with what I saw in simulation. t_win=15 is 
     probably the best tradeoff. 

  4. The results for coverage probability are inconclusive. I used the mean of the 
     estimates for computing the coverage probability, since the estimates are 
     biased; however, since the estimates aren't normal, the confidence region 
     is not likely to behave as advertised. A more controlled experiment with 
     line-of-sight to all receivers would be a better way to assesss the method. 

'''


import util
import position1, signal1
import numpy as np
import matplotlib.pyplot as pp
import pickle

position1.NORMALIZE_SPECTRUM=False
cal_id = 3
t_step = 15
t_win = 15
t_chunk = 3600 / 4 
conf_level=0.95

dep_id = 60
t_start = 1383098400.514320
t_end = 1383443999.351099
fn = 'beacon'

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
          cov = position1.BootstrapCovariance(pos, sites, max_resamples=500)
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


def plot(pos, p_known, site_ids, fn):
    
    fig = pp.gcf()
    ax = fig.add_subplot(111)
    ax.axis('equal')
    ax.set_xlabel('easting (m)')
    ax.set_ylabel('northing (m)')

    X = np.imag(pos)
    Y = np.real(pos)
    pp.scatter(X, Y, alpha=0.2, facecolors='b', edgecolors='none', s=5)

    pp.plot(p_known.imag, p_known.real, color='w', marker='o', ms=3)
    
    pp.title("%s" % str(site_ids))
    pp.savefig("%s%s.png" % (fn, ''.join(map(lambda x: str(x), site_ids))))
    pp.clf()
  


if __name__ == '__main__':  
  db_con = util.get_db('reader')
  
  # System params 
  sv = signal1.SteeringVectors(db_con, cal_id)
  sites = util.get_sites(db_con)
  (center, zone) = util.get_center(db_con)
  
  P, C = process(sv)
  pickle.dump((P, C), open(fn+'-data', 'w'))
  #(P, C) = pickle.load(open(fn+'-data', 'r'))

  print 't_win=%d' % t_win
  for site_ids in P.keys(): 

    print '----------------------------------------'

    if len(site_ids) < 2: 
      print "skpping", site_ids
      continue
    
    print site_ids
    p_mean = np.complex(0,0)
    total = good = 0
    for p in P[site_ids]: 
      total += 1
      if p is not None:
        p_mean += p
        good += 1
    p_mean /= good 

    print 'mean: (%0.3f, %0.3f)' % (p_mean.imag, p_mean.real)

    total = good = 0
    area = 0
    for i in range(len(P[site_ids])):
      if P[site_ids][i] is not None and C[site_ids][i] is not None:
        total += 1
        angle, axis0, axis1 = C[site_ids][i]
        E = position1.Ellipse(P[site_ids][i], angle, [axis0, axis1])
        if p_mean in E: 
          good += 1
        area += E.area()

    if total > 0:
      print 'area: %0.3f' % (area / total)
      print "coverage: %d out of %d (%0.3f)" % (good, total, float(good)/total)
  
    plot(P[site_ids], site34, site_ids, fn)
  
  #p_mean = np.mean(P[(1,3,6)])
  #for ell in C[(1,3,6)]: 
  #  if ell is not None:
  #    angle, axis0, axis1 = C[site_ids][i]
  #    E = position1.Ellipse(P[site_ids][i], angle, [axis0, axis1])
  #    E.plot('test.png', p_mean)
  #    raw_input() 

