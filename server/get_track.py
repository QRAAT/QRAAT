#!/usr/bin/python
import sys, time
import qraat, qraat.srv
import MySQLdb as mdb

try: 
  start = time.time()
  print "template: start time:", time.asctime(time.localtime(start))

  db_con = qraat.util.get_db('reader')
 
                                        # trackID, t_start, t_end
  track = qraat.srv.track.Track(db_con, 0, 1376420800, 1376442000) 
 
  for pos in track:
    print pos

except mdb.Error, e:
  print >>sys.stderr, "template: error: [%d] %s" % (e.args[0], e.args[1])
  sys.exit(1)

except qraat.error.QraatError, e:
  print >>sys.stderr, "template: error: %s." % e

finally: 
  print "template: finished in %.2f seconds." % (time.time() - start)
