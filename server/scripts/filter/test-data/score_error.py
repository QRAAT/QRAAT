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
#
# Run the filter script at least once so that we have the estinterval
# stuff calculated. 

import qraat, qraat.srv
import MySQLdb as mdb
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as pp
import os, sys, time
import pickle

dep_id  = 105
site_id = 8
t_start = 1410721127
t_end   = 1410807696

EST_SCORE_THRESHOLD = float(sys.argv[1]) # float(os.environ["RMG_POS_EST_THRESHOLD"]) 
                                         # greater than
print "Score threshold:",  EST_SCORE_THRESHOLD

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

  # Create a grid of (false positive, false_negative)'s. The x-axis is pulse interval 
  # variation and the y-axis is pulse error. 
  
  score_error_step = 0.005
  variation_step = 0.04
  Y = np.arange(0, 0.2, score_error_step)
  X = np.arange(0, 6, variation_step)
  pos = []; neg = []; 

  for score_error in reversed(Y): 
    
    pos.append([]); neg.append([])

    # Run signal filter.
    qraat.srv.signal.SCORE_ERROR = lambda(x) : score_error
    print >>sys.stderr, "score_error = %.3f" % qraat.srv.signal.SCORE_ERROR(0)
    (total, _) = qraat.srv.signal.Filter(db_con, dep_id, site_id, t_start, t_end)

    # Count the number of false positives and false negatives in each variation range. 
    false_pos = false_neg = 0
    for variation in X: 

      for i in range(len(intervals)-1): 
        
        if variation <= intervals[i][2] and intervals[i][2] < variation + variation_step:
            
          cur.execute('''SELECT estID, score, theoretical_score
                           FROM estscore JOIN est ON est.ID = estscore.estID
                          WHERE deploymentID = %s 
                            AND siteID = %s
                            AND timestamp >= %s
                            AND timestamp < %s''', (
                  dep_id, site_id, intervals[i][0], intervals[i+1][0]))
  
          for (id, score, theoretical_score) in cur.fetchall(): 
            rel_score = float(score) / theoretical_score
            
            if good[id] and rel_score > EST_SCORE_THRESHOLD:        pass # Ok 
            elif not good[id] and rel_score <= EST_SCORE_THRESHOLD: pass # Ok
            elif not good[id] and rel_score > EST_SCORE_THRESHOLD:  false_pos += 1 # False positive
            elif good[id] and rel_score <= EST_SCORE_THRESHOLD:     false_neg += 1 # False negative

      pos[-1].append(false_pos); neg[-1].append(false_neg)
      
  pickle.dump((X, Y, np.array(pos), np.array(neg)), 
                 open('result%0.1f' % EST_SCORE_THRESHOLD, 'w')) # Dump result
  

except mdb.Error, e:
  print >>sys.stderr, "score_error: error: [%d] %s" % (e.args[0], e.args[1])
  sys.exit(1)

except qraat.error.QraatError, e:
  print >>sys.stderr, "score_error: error: %s." % e

finally: 
  print >>sys.stderr, "score_error: finished in %.2f seconds." % (time.time() - start)
