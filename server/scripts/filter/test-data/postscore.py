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
t_start = 1410721127
t_end   = 1410807696

EST_SCORE_THRESHOLD = float(sys.argv[1]) # float(os.environ["RMG_POS_EST_THRESHOLD"]) 
                                         # greater than


try: 
  start = time.time()
  print >>sys.stderr, "score_error: start time:", time.asctime(time.localtime(start))

  print "score_error: loading file ... "
  (X, Y, prescores) = pickle.load(open('result'))

  for EST_SCORE_THRESHOLD in map(lambda (x) : float(x), sys.argv[1:]):
    pos = []; neg = []; 
    print "score_error: counting false positives / negatives (%0.2f) ... " % EST_SCORE_THRESHOLD
    
    for y in reversed(range(len(Y))): 
      
      pos.append([]); neg.append([])

      # Count the number of false positives and false negatives in each variation range. 
      false_pos = false_neg = 0
      good_count = bad_count = 0
      for x in range(len(X)):
        for (good, rel_score) in prescores[x][y]:
          if good and rel_score > EST_SCORE_THRESHOLD:        pass # Ok
          elif not good and rel_score <= EST_SCORE_THRESHOLD: pass # Ok
          elif not good and rel_score > EST_SCORE_THRESHOLD:  false_pos += 1 # False positive
          elif good and rel_score <= EST_SCORE_THRESHOLD:     false_neg += 1 # False negative
     
          if good: good_count += 1
          else: bad_count += 1
          
        pos[-1].append(float(false_pos) / bad_count)
        neg[-1].append(float(false_neg) / good_count)
        
    pickle.dump((X, Y, np.array(pos), np.array(neg)), 
                   open('result%0.2f' % EST_SCORE_THRESHOLD, 'w')) # Dump result
  

except mdb.Error, e:
  print >>sys.stderr, "score_error: error: [%d] %s" % (e.args[0], e.args[1])
  sys.exit(1)

except qraat.error.QraatError, e:
  print >>sys.stderr, "score_error: error: %s." % e

finally: 
  print >>sys.stderr, "score_error: finished in %.2f seconds." % (time.time() - start)
