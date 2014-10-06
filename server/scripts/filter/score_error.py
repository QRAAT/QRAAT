# score_error.py
#
# This is a tool for (hopefullY) emperically deriving a good value for 
# qraat.srv.filter.SCORE_ERROR for the time filter as a function of 
# the pulse interval variation. 
#
# Create a partition of "good" points. For the test data, known good 
# points of an eigenvalue decomposition signal power within a certain
# range, and false positives are outside of the range. The test data 
# is from September 2014 for depID=105 and siteID=8. Note that this 
# isn't generalizable. 

import qraat, qraat.srv
import MySQLdb as mdb
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as pp
import os, sys, time

dep_id = 105
site_id = 8

try: 
  start = time.time()
  print "score_error: start time:", time.asctime(time.localtime(start))

  db_con = qraat.srv.util.get_db('writer')
  cur = db_con.cursor()
 
  # Time window. 
  cur.execute('''SELECT min(timestamp), max(timestamp)
                   FROM est
                  WHERE deploymentID = %s 
                    AND siteID = %s''', (dep_id, site_id))
  (t_start, t_end) = cur.fetchone()

  # Interval statistics. 
  cur.execute('''SELECT timestamp, duration, pulse_interval, pulse_variation
                   FROM estinterval
                  WHERE deploymentID = %s 
                    AND siteID = %s
                    AND timestamp >= %s
                    AND timestamp + duration <= %s
                  ORDER BY timestamp''', (dep_id, site_id, t_start, t_end))

  intervals = []

  points = []  # (id, timestamp, power) 
  good = {}    # id -> {True, False}
  for (T, duration, pulse_interval, pulse_variation) in cur.fetchall(): 
    
    intervals.append((T, pulse_interval, pulse_variation))

    # Signal power for pulses in window. 
    cur.execute('''SELECT id, timestamp, edsp
                     FROM est
                    WHERE deploymentID = %s 
                      AND siteID = %s
                      AND timestamp >= %s
                      AND timestamp < %s
                    ORDER BY timestamp''', (dep_id, site_id, T, float(T) + duration))
    
    interval_points = []
    for (id, t, edsp) in cur.fetchall():
      interval_points.append((id, t, 10 * np.log10(edsp)))

    avg_power = np.mean(filter(lambda (pwr) : pwr > -20, 
                            map(lambda (row) : row[2], interval_points)))
    
    for row in interval_points: 
      if abs(row[2] - avg_power) < 0.33: good[row[0]] = True
      else:                              good[row[0]] = False

    points += interval_points 
  
  # Plot good vs bad points for sanity. 
  good_points = []; bad_points = []
  for (id, t, power) in points:
    if good[id]: good_points.append((t, power))
    else:        bad_points.append((t, power))

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
  pp.savefig('good_points.png')
  pp.clf()
    
  




except mdb.Error, e:
  print >>sys.stderr, "score_error: error: [%d] %s" % (e.args[0], e.args[1])
  sys.exit(1)

except qraat.error.QraatError, e:
  print >>sys.stderr, "score_error: error: %s." % e

finally: 
  print "score_error: finished in %.2f seconds." % (time.time() - start)
