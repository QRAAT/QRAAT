# score_error.py #
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
                    AND timestamp >= %s
                    AND timestamp <= %s
                  ORDER BY timestamp''', (dep_id, t_start, t_end))

  intervals = list(cur.fetchall())

  # Partition good/bad points.

  points = qraat.csv.csv('test-data.csv')
  good = {} 
  for p in points: 
    good[int(p.est_id)] = True if int(p.good) is 1 else False

  # Create a grid of (false positive, false_negative)'s. The x-axis is pulse interval 
  # variation and the y-axis is pulse error. 
  
  score_error_step = 0.005
  variation_step = 0.04
  Y = np.arange(0, 0.2, score_error_step)
  X = np.arange(0, 4, variation_step)
  prescores = [ [ [] for j in Y ] for i in X ] 

  y = len(Y)
  for score_error in reversed(Y): 
    
    y -= 1

    # Run signal filter.
    qraat.srv.signal.SCORE_ERROR = lambda(x) : score_error
    print >>sys.stderr, "score_error = %.3f" % qraat.srv.signal.SCORE_ERROR(0)
    (total, _) = qraat.srv.signal.Filter(db_con, dep_id, t_start, t_end)

    # Count the number of false positives and false negatives in each variation range. 
    x = 0
    for variation in X: 
      for i in range(len(intervals)-1): 
        if variation <= intervals[i][2] and intervals[i][2] < variation + variation_step:
          cur.execute('''SELECT estID, score / theoretical_score
                           FROM estscore JOIN est ON est.ID = estscore.estID
                          WHERE deploymentID = %s 
                            AND timestamp >= %s
                            AND timestamp < %s''', (
                  dep_id, intervals[i][0], intervals[i+1][0]))
          for (id, rel_score) in cur.fetchall():
            if good.get(id) == None: print 'Uh oh!', id
            else: prescores[x][y].append((good[id], rel_score))

      x += 1

  pickle.dump((X, Y, prescores), open('result', 'w')) # Dump result
  

except mdb.Error, e:
  print >>sys.stderr, "score_error: error: [%d] %s" % (e.args[0], e.args[1])
  sys.exit(1)

except qraat.error.QraatError, e:
  print >>sys.stderr, "score_error: error: %s." % e

finally: 
  print >>sys.stderr, "score_error: finished in %.2f seconds." % (time.time() - start)
