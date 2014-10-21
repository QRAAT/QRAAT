# Plot good/bad partition from CSV file.

import qraat, qraat.srv
import MySQLdb as mdb
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as pp
import os, sys, time
import pickle

dep_id  = 105
site_id = 1
t_start = 1410721127
t_end   = 1410807696

try: 
  start = time.time()
  print >>sys.stderr, "score_error: start time:", time.asctime(time.localtime(start))


  points = qraat.csv.csv('site%d.csv' % site_id)

  # Fix for site 3. 
  #t2 = 1410761939+1000;            y2 = -17.6; 
  #t0 = 1410745421-1000;            y0 = -20.2
  #t1 = (t0 + t2) / 2 - 2500;       y1 = -18.3
  #m0 = float(y1 - y0) / (t1 - t0); c0 = y1 - (m0 * t1)
  #m1 = float(y2 - y1) / (t2 - t1); c1 = y2 - (m1 * t2)
  #Y0 = lambda(t) : (m0 * t) + c0;  T0 = np.array([t0, t1])
  #Y1 = lambda(t) : (m1 * t) + c1;  T1 = np.array([t1, t2])
  
  # Output CSV
  #fd = open('fella%d.csv' % site_id, 'w')
  #fd.write('est_id,t,power,good\n')

  # Plot good vs bad points for sanity. 
  good_points = []; bad_points = []
  for (id, t, power, good) in points:
    id = int(id); t = float(t); power = float(power); good = int(good) 
    #if t0 <= t < t1 and abs(Y0(t) - power) < 0.40:  
    #  guy = 1; good_points.append((t, power))
    #elif t1 <= t < t2 and abs(Y1(t) - power) < 0.40:  
    #  guy = 1; good_points.append((t, power))
    if good==1: 
      guy = 1; good_points.append((t, power))
    else: 
      guy = 0; bad_points.append((t, power))
    #fd.write('%d,%f,%0.2f,%d\n' % (id, t, power, 1 if guy else 0))


  pp.plot([ t for (t,pwr) in good_points ], 
          [ pwr for (t,pwr) in good_points ], '.')
  pp.plot([ t for (t,pwr) in bad_points ],
          [ pwr for (t,pwr) in bad_points ], 'r.')
  #pp.plot(T0, Y0(T0), 'k-')
  #pp.plot(T1, Y1(T1), 'k-')

  pp.xlabel("Time (seconds)")
  pp.ylabel("edsp (dB)")
  pp.title("Time vs. Power, deploymentID={0:d}, siteID={1:.0f}, {2:d}<timestamp<{3:d}".format(
    dep_id, site_id, int(t_start), int(t_end)))
  pp.legend(['Good','Bad'])
  pp.grid(True)
  fig = pp.gcf()
  fig.set_size_inches(16,12)
  pp.savefig('good_points_site%d.png' % site_id)
  pp.clf()

  

except mdb.Error, e:
  print >>sys.stderr, "score_error: error: [%d] %s" % (e.args[0], e.args[1])
  sys.exit(1)

except qraat.error.QraatError, e:
  print >>sys.stderr, "score_error: error: %s." % e

finally: 
  print >>sys.stderr, "score_error: finished in %.2f seconds." % (time.time() - start)
