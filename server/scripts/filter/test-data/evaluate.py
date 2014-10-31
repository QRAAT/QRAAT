# Evaluate the performance of (est threshold, score error function) pairs 
# for various trade off policies. 

import qraat, qraat.srv
import time, os, sys, commands
import MySQLdb as mdb
from optparse import OptionParser
import numpy as np

dep_id  = 105
t_start = 1410721127
t_end   = 1410807696

### Best-fits of various trade-off policies ###################################

# Trade off policy -- Cp=1,Cn=2
#exp = [ (0.1, "np.poly1d([-0.00042, 0.00479, -0.02087, 0.04558, -0.0529, 0.03625, 0.0412])"),
#        (0.2, "lambda(x) : (-0.0054 / (x + 0.0545)) + 0.1956") ] 

# Trade off policy -- Cp=1,Cn=1
#exp = [ (0.1, "lambda(x) : (-0.1525 / (x + 5.6903)) + 0.0563"), 
#        (0.2, "np.poly1d([0.00047, -0.0049, 0.01564, -0.00576, -0.04566, 0.07071, 0.06276])") ]

# Trade off policy -- Cp=3,Cn=2
#exp = [ (0.1, "lambda(x) : (-0.0160 / (x + 1.4445)) + 0.0337"),
#        (0.2, "np.poly1d([-0.00017, 0.00198, -0.00982, 0.02755, -0.04531, 0.04562, 0.0477])") ]

# Trade off policy -- Cp=2,Cn=1
#exp = [ (0.1, "lambda(x) : (-0.0019 / (x + 0.2561)) + 0.0258"),
#        (0.2, "lambda(x) : (-0.6324 / (x + 7.7640)) + 0.1255") ]

# Trade off policy -- Cp=3,Cn=1 
#exp = [ (0.1, "np.poly1d([-0.00039, 0.00467, -0.02141, 0.04718, -0.05185, 0.02651, 0.01509])"), 
#        (0.2, "lambda(x) : (-0.0451 / (x + 1.7954)) + 0.0581") ] 

# Trade off policy -- Cp=5,Cn=1
#exp = [ (0.1, "lambda(x) : (-0.0006 / (x + 0.0916)) + 0.0153"),
#        (0.2, "lambda(x) : (-0.2024 / (x + 6.7923)) + 0.0575"), 
#        (0.3, "lambda(x) : (-0.2884 / (x + 2.3559)) + 0.1864") ]

# Trade off policy -- Cp=10,Cn=1
#exp = [ (0.1, "lambda(x) : 0.01"),
#        (0.2, "lambda(x) : (-0.0072 / (x + 0.6637)) + 0.0272"),
#        (0.3, "lambda(x) : (-4.3487 / (x + 19.4387)) + 0.2651") ]


### Evalute performance of fit curve ##########################################

# Trade off policy -- Cp=2,Cn=1
Y = np.array([ 0.04,   0.04,   0.045,  0.045,  0.045,  0.045,  0.045,  0.045,  0.045,  0.045,
               0.05,   0.05,   0.05,   0.05,   0.05,   0.05,   0.055,  0.055,  0.055,  0.055,
               0.055,  0.055,  0.055,  0.055,  0.055,  0.055,  0.055,  0.055,  0.055,  0.055,
               0.055,  0.055,  0.055,  0.055,  0.055,  0.055,  0.055,  0.055,  0.055,  0.055,
               0.055,  0.06,   0.06,   0.06,   0.06,   0.06,   0.06,   0.06,   0.06,   0.06,   0.06,
               0.06,   0.06,   0.06,   0.06,   0.06,   0.06,   0.06,   0.06,   0.06,   0.06,   0.06,
               0.06,   0.06,   0.06,   0.06,   0.065,  0.065,  0.065,  0.065,  0.065,  0.065,
               0.07,   0.07,   0.07,   0.07,   0.07,   0.07,   0.07,   0.07,   0.07,   0.07,   0.07,
               0.07,   0.07,   0.07,   0.07,   0.07,   0.07,   0.07,   0.07,   0.07,   0.07,   0.07,
               0.07,   0.07,   0.07,   0.07,   0.07,   0.07])

def opt(x):
  i = int(x / 0.04)
  if i < len(Y): 
    return Y[i]
  else: 
    return 0.1255

exp = [ (0.2, "lambda(x) : opt(x)"),
        (0.2, "lambda(x) : (-0.6324 / (x + 7.7640)) + 0.1255"),
        (0.2, "np.poly1d([0.00025, -0.00308, 0.01313, -0.02164, 0.00583, 0.01996, 0.0408])"),
        (0.2, "lambda(x) : 0.1255"),
        (0.2, "lambda(x) : 0.025") ]

# Trade off policy -- Cp=1,Cn=2
#Y = np.array([ 0.1,    0.125,  0.15,   0.185,  0.17,   0.185,  0.17,   0.185,  0.185,  0.185,
#               0.155,  0.155,  0.175,  0.175,  0.195,  0.19,   0.195,  0.195,  0.195,  0.195,
#               0.195,  0.195,  0.195,  0.195,  0.195,  0.195,  0.195,  0.195,  0.195,  0.195,
#               0.195,  0.195,  0.195,  0.195,  0.195,  0.195,  0.195,  0.195,  0.195,  0.195,
#               0.195,  0.195,  0.195,  0.195,  0.195,  0.195,  0.195,  0.195,  0.195,  0.195,
#               0.195,  0.195,  0.195,  0.195,  0.195,  0.195,  0.195,  0.195,  0.195,  0.195,
#               0.195,  0.195,  0.195,  0.195,  0.195,  0.195,  0.195,  0.19,   0.195,  0.195,
#               0.195,  0.195,  0.19,   0.19,   0.19,   0.19,   0.19,   0.19,   0.19,   0.19,   0.19,
#               0.19,   0.19,   0.19,   0.19,   0.19,   0.19,   0.19,   0.19,   0.19,   0.19,   0.19,
#               0.19,   0.19,   0.19,   0.19,   0.19,   0.19,   0.19,   0.19 ])
#
#def opt(x):
#  i = int(x / 0.04)
#  if i < len(Y): 
#    return Y[i]
#  else: 
#    return 0.1956
#
#exp = [ (0.2, "lambda(x) : opt(x)"),
#        (0.2, "lambda(x) : (-0.0054 / (x + 0.0545)) + 0.1956"),
#        (0.2, "np.poly1d([-0.00159, 0.02117, -0.11046, 0.28551, -0.3839, 0.25636, 0.12648])"),
#        (0.2, "lambda(x) : 0.1956"),
#        (0.2, "lambda(x) : 0.038") ] 


try: 
  start = time.time()
  print "evaluate: start time:", time.asctime(time.localtime(start))
  db_con = qraat.srv.util.get_db('writer')

  # Partition of good / bad points. 
  print "evaluate: loading test data ... "
  points = qraat.csv.csv('test-data.csv')
  good = {} 
  for p in points: 
    good[int(p.est_id)] = True if int(p.good) is 1 else False

  for (EST_SCORE_THRESHOLD, score_err_str) in exp: 
    
    # Run filter. 
    print "evaluate: running filter (%0.2f) ... " % EST_SCORE_THRESHOLD
    qraat.srv.signal.SCORE_ERROR = eval(score_err_str)
    (total, _) = qraat.srv.signal.Filter(db_con, dep_id, t_start, t_end)
    
    # Generate report. 
    cur = db_con.cursor()
    cur.execute('''SELECT estID, score / theoretical_score
                     FROM estscore JOIN est ON est.ID = estscore.estID
                    WHERE deploymentID = %s 
                      AND timestamp >= %s
                      AND timestamp < %s''', (dep_id, t_start, t_end))

    false_pos = false_neg = 0
    good_count = bad_count = 0
    for (id, rel_score) in cur.fetchall():
      if good.get(id) == None: 
        #print 'Uh oh!', id
        continue
    
      if good[id] and rel_score > EST_SCORE_THRESHOLD:        pass # Ok
      elif not good[id] and rel_score <= EST_SCORE_THRESHOLD: pass # Ok
      elif not good[id] and rel_score > EST_SCORE_THRESHOLD:  false_pos += 1 # False positive
      elif good[id] and rel_score <= EST_SCORE_THRESHOLD:     false_neg += 1 # False negative
      if good[id]: good_count += 1
      else: bad_count += 1
    
    print 
    print "Score error . . . . %s" % score_err_str
    print "Score threshold . . %0.2f" % EST_SCORE_THRESHOLD
    print 
    print "Good points . . . . %d" % good_count
    print "False negatives . . %d" % false_neg
    print "   Rate . . . . . . %0.4f" % (float(false_neg) / good_count)
    print 
    print "Bad points  . . . . %d" % bad_count
    print "False positives . . %d" % false_pos
    print "   Rate . . . . . . %0.4f" % (float(false_pos) / bad_count)
    print


except mdb.Error, e:
  print >>sys.stderr, "evaluate: error: [%d] %s" % (e.args[0], e.args[1])
  sys.exit(1)

except qraat.error.QraatError, e:
  print >>sys.stderr, "evaluate: error: %s." % e

finally: 
  print "evaluate: finished in %.2f seconds." % (time.time() - start)
