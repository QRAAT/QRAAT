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
site_id = 3
t_start = 1410721127
t_end   = 1410807696

try: 
  start = time.time()
  print >>sys.stderr, "score_error: start time:", time.asctime(time.localtime(start))


  points = qraat.csv.csv('site%d.csv' % site_id)

  # Plot good vs bad points for sanity. 
  good_points = []; bad_points = []
  for (id, t, power, good) in points:
    id = int(id); t = float(t); power = float(power); good = int(good) 
    if good==1: good_points.append((t, power))
    else:       bad_points.append((t, power))

  pp.plot([ t for (t,pwr) in good_points ], 
          [ pwr for (t,pwr) in good_points ], '.')
  pp.plot([ t for (t,pwr) in bad_points ], 
          [ pwr for (t,pwr) in bad_points ], 'r.')
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
