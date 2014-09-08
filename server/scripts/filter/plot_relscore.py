#!/usr/bin/python
# rmg_plot_relscore
# Template for writing scripts. This program is part of QRAAT, 
# an automated animal tracking system based on GNU Radio. 
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
import time, os, sys, commands
import MySQLdb as mdb
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
from optparse import OptionParser

# Check for running instances of this program. 
(status, output) = commands.getstatusoutput(
  'pgrep -c `basename %s`' % (sys.argv[0]))
if int(output) > 1: 
  print >>sys.stderr, "plot_relscore: error: attempted reentry, exiting"
  sys.exit(1)

parser = OptionParser()

parser.description = '''This does nothing.'''

(options, args) = parser.parse_args()

t_start = 1407448800.186593 
t_end   = 1407466794.772133 

try: 
  start = time.time()
  print "plot_relscore: start time:", time.asctime(time.localtime(start))

  db_con = qraat.util.get_db('reader')
  cur = db_con.cursor()

  cur.execute('''SELECT DISTINCT deploymentID, siteID 
                   FROM est JOIN estscore ON est.ID = estscore.estID
                  WHERE timestamp >= %s 
                    AND timestamp <= %s''', (t_start, t_end))

  for (dep_id, site_id) in cur.fetchall():
    cur.execute('''SELECT (score / (theoretical_score + 1))
                     FROM est JOIN estscore ON est.ID = estscore.estID
                    WHERE deploymentID = %d
                      AND siteID = %d 
                      AND timestamp >= %f
                      AND timestamp <= %f''' % (dep_id, site_id, t_start, t_end)) 

    X = []
    for x in cur.fetchall(): 
      X.append(float(x[0]))
    
    if len(X) > 10:
      print "plot_relscore: plotting (depID=%d, siteID=%d)" % (dep_id, site_id)

      fig = plt.figure(figsize=(5,4))
      ax = fig.add_subplot(111)

      N = 20
      # the histogram of the data
      n, bins, patches = ax.hist(X, N, facecolor='grey', alpha=0.75)
      bincenters = 0.5*(bins[1:]+bins[:-1])
      ax.set_xlabel('Score')
      ax.set_ylabel('Frequency')
      ax.set_xlim(min(X), max(X))
      #ax.set_ylim(0, 100000) # FIXME
      ax.grid(False)

      plt.savefig("dep%d_site%d.png" % (dep_id, site_id))
      
    else:
      print "plot_relscore: skipping empty set (depID=%d, siteID=%d)" % (dep_id, site_id)

  


except mdb.Error, e:
  print >>sys.stderr, "plot_relscore: error: [%d] %s" % (e.args[0], e.args[1])
  sys.exit(1)

except qraat.error.QraatError, e:
  print >>sys.stderr, "plot_relscore: error: %s." % e

finally: 
  print "plot_relscore: finished in %.2f seconds." % (time.time() - start)
