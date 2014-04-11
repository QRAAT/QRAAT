#!/usr/bin/python
# stat_pos.py - Calculate velocity and acceleration of raw positions. 
#
# Copyright (C) 2013 Christopher Patton
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import qraat
import time, os, sys, commands, re 
import MySQLdb as mdb
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as pp
from optparse import OptionParser

# Check for running instances of this program. 
(status, output) = commands.getstatusoutput(
  'pgrep -c `basename %s`' % (sys.argv[0]))
if int(output) > 1: 
  print >>sys.stderr, "stat_pos: error: attempted reentry, exiting"
  sys.exit(1)

parser = OptionParser()

parser.description = ''' '''
parser.add_option('--t-start', type='str', metavar='YYYY-MM-DD', default='2013-08-13') 
parser.add_option('--t-end', type='str', metavar='YYYY-MM-DD', default='2013-08-14') 
parser.add_option('--tx-id', type='int', metavar='ID', default=51) 
(options, args) = parser.parse_args()

try: 
  start = time.time()
  print "stat_pos: start time:", time.asctime(time.localtime(start))

  db_con = qraat.util.get_db('reader')
  
  try: 
    t_start = time.mktime(time.strptime(options.t_start, "%Y-%m-%d"))
    t_end = time.mktime(time.strptime(options.t_end, "%Y-%m-%d"))
  except ValueError:
    print >>sys.stderr, "star_pos: error: malformed date string." 
    sys.exit(1)

  positions = qraat.trackraw(db_con, t_start, t_end, options.tx_id)
  (V, A) = positions.stats()

  (mean, stddev) = positions.speed()
  m = 10
  n, bins, patches = pp.hist(V, 75, range=[0,m], normed=1, histtype='stepfilled')
  pp.setp(patches, 'facecolor', 'b', 'alpha', 0.20)
  pp.title('%s to %s txID=%d' % (options.t_start, options.t_end, options.tx_id))
  pp.xlabel("M / sec")
  pp.ylabel("Probability density")
  pp.text(0.7 * m, 0.8 * max(n), 
    ('Target speed\n'
     '  $\mu=%d$\n'
     '  $\sigma=%d$\n'
     '  range (%d, %d)') % (mean, stddev, min(V), max(V)))
  pp.savefig('tx%d_%s_velocity.png' % (options.tx_id, options.t_start))
  
  pp.clf()
  (mean, stddev) = positions.acceleration()
  m = 20
  n, bins, patches = pp.hist(A, 75, range=[0,m], normed=1, histtype='stepfilled')
  pp.setp(patches, 'facecolor', 'b', 'alpha', 0.20)
  pp.title('%s to %s txID=%d' % (options.t_start, options.t_end, options.tx_id))
  pp.xlabel("M / sec$^2$")
  pp.ylabel("Probability density")
  pp.text(0.7 * m, 0.8 * max(n), 
    ('Target acceleration\n'
     '  $\mu=%d$\n'
     '  $\sigma=%d$\n'
     '  range (%d, %d)') % (mean, stddev, min(A), max(A)))
  pp.savefig('tx%d_%s_accel.png' % (options.tx_id, options.t_start))
  
  print len(positions.track)
  pp.clf()
  pp.plot( 
   map(lambda (P, t): P.imag, positions.track), 
   map(lambda (P, t): P.real, positions.track), '.', alpha=0.3)
  pp.savefig('plot.png')

except mdb.Error, e:
  print >>sys.stderr, "stat_pos: error: [%d] %s" % (e.args[0], e.args[1])
  sys.exit(1)

except qraat.QraatError, e:
  print >>sys.stderr, "stat_pos: error: %s." % e
 
finally: 
  print "stat_pos: finished in %.2f seconds." % (time.time() - start)
