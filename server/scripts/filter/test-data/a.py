# Rough partition of good/bad points 

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

  db_con = qraat.srv.util.get_db('writer')
  cur = db_con.cursor()
 
  # Interval statistics. 
  cur.execute('''SELECT timestamp, pulse_interval, pulse_variation
                   FROM estinterval
                  WHERE deploymentID = %s 
                    AND siteID = %s
                    AND timestamp >= %s
                    AND timestamp <= %s
                  ORDER BY timestamp''', (dep_id, site_id, t_start, t_end))

  intervals = list(cur.fetchall())

  # Partition good/bad points. 
  points = []  # (id, t, power) 
  good = {}    # id -> {True, False}

  for i in range(len(intervals)-1):
    
    # Signal power for pulses in window. 
    cur.execute('''SELECT id, timestamp, edsp
                     FROM est
                    WHERE deploymentID = %s 
                      AND siteID = %s
                      AND timestamp >= %s
                      AND timestamp < %s
                    ORDER BY timestamp''', (
          dep_id, site_id, intervals[i][0], intervals[i+1][0]))
    
    interval_points = []
    for (id, t, edsp) in cur.fetchall():
      interval_points.append((id, t, 10 * np.log10(edsp)))

    avg_power = np.mean(filter(lambda (pwr) : pwr > -35 and pwr < -29,
                            map(lambda (row) : row[2], interval_points)))
    
    for row in interval_points: 
      if abs(row[2] - avg_power) < 0.80: good[row[0]] = True
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
  pp.savefig('rough.png')
  pp.clf()

  # Output CSV
  fd = open('site%d.csv' % site_id, 'w')
  fd.write('est_id,t,power,good\n')
  for (id, t, power) in points: 
    fd.write('%d,%f,%0.2f,%d\n' % (id, t, power, 1 if good[id] else 0))
  fd.close()
  
  

except mdb.Error, e:
  print >>sys.stderr, "score_error: error: [%d] %s" % (e.args[0], e.args[1])
  sys.exit(1)

except qraat.error.QraatError, e:
  print >>sys.stderr, "score_error: error: %s." % e

finally: 
  print >>sys.stderr, "score_error: finished in %.2f seconds." % (time.time() - start)
