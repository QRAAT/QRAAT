#!/usr/bin/env python2
# rmg_score_error

import qraat
import MySQLdb as mdb


dep_id = 105
site_id = 8

try: 
  start = time.time()
  print "score_error: start time:", time.asctime(time.localtime(start))

  db_con = qraat.util.get_db('reader')
  
  cur = db_con.cursor()











except mdb.Error, e:
  print >>sys.stderr, "score_error: error: [%d] %s" % (e.args[0], e.args[1])
  sys.exit(1)

except qraat.error.QraatError, e:
  print >>sys.stderr, "score_error: error: %s." % e

finally: 
  print "score_error: finished in %.2f seconds." % (time.time() - start)
