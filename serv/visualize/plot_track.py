# plot_track.py. 
#
# Copyright (C) 2014 Christopher Patton
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
import matplotlib.pyplot as pp
import matplotlib.image as mpimg
import numpy as np
import time
from optparse import OptionParser

parser = OptionParser()

parser.description = '''\
Plot tracks. This program is 
part of QRAAT, an automated animal tracking system based on GNU Radio.   
'''

parser.add_option('--tx-id', type='int', metavar='INT', default=51,
                  help="Serial ID of the target transmitter in the database "
                       "context.")

parser.add_option('--t-start', type='float', metavar='SEC', default=0.0, 
                  help="Start time in secondes after the epoch (UNIX time).")

parser.add_option('--t-end', type='float', metavar='SEC', default=float("+inf"),
                  help="End time in secondes after the epoch (UNIX time).")

(options, args) = parser.parse_args()


db_con = qraat.util.get_db('reader')

M = lambda(t) : 10 
C = 1
overlay = True

# A possible way to calculate good tracks. Compute the tracks
# with some a priori maximum speed that's on the high side. 
if options.t_start == 0.0 and options.t_end == float("+inf"): 
  track = qraat.trackall(db_con, options.tx_id, M, C)
else:
  track = qraat.track(db_con, options.t_start, options.t_end, options.tx_id, M, C)

# We then calculate statistics on the transition speeds in the 
# critical path. Plotting the tracks might reveal spurious points
# that we want to filter out. 
(mean, std) = track.speed()
print "speed        (mu=%.4f, sigma=%.4f)" % (mean, std)

# Recompute the tracks, using the mean + one standard deviation as
# the maximum speed. 
track.recompute(lambda(t) : mean + std, C)

if overlay: 

  # FIXME Where/how to install this file? 
  bg = mpimg.imread('/home/christopher/continuum/work/QRAAT/QRAAT/serv/visualize/qr-overlay.png') 

  e0 = 572599.5 - 150
  e1 = 577331.4 - 150

  n0 = 4259439.5 + 110 + 60 - 20 - 500 
  n1 = 4259483.7 + 210 + 85 -  20 - 500 

  E = lambda(x) : float(bg.shape[1]) * (x - e0) /  (e1 - e0)
  N = lambda(y) : bg.shape[0] - (y - n0) / float(bg.shape[0]) * (n1 - n0)


  sites = qraat.csv(db_con=db_con, db_table='sitelist')

  fig = pp.figure()
  ax = fig.add_subplot(1,1,1)

  #pp.text(E(track[0][0].imag) + 10, N(track[0][0].real) + 10, "Start", color='gray', size='smaller')
  #pp.text(E(track[-1][0].imag) + 10, N(track[-1][0].real) + 10, "End", color='gray', size='smaller')

  # Plot tracks. 
  pp.scatter( 
   map(lambda (P, t): E(P.imag), track), 
   map(lambda (P, t): N(P.real), track), alpha=0.2, s=2, c='k', 
     label='Transmitter tracks')

  # Plot sites. 
  pp.plot(
   [E(float(s.easting)) for s in sites], 
   [N(float(s.northing)) for s in sites], 'ro', 
      label='QRAAT receiver sites')

  t = time.localtime(track[0][1])
  s = time.localtime(track[-1][1])
  pp.title('%04d-%02d-%02d  %02d:%02d - %04d-%02d-%02d  %02d:%02d  txID=%d' % (
       t.tm_year, t.tm_mon, t.tm_mday,
       t.tm_hour, t.tm_min,
       s.tm_year, s.tm_mon, s.tm_mday,
       s.tm_hour, s.tm_min,
       options.tx_id), size='smaller')

  pp.grid(b=True, which='both', color='gray', linestyle='-')

  pp.imshow(bg)
  pp.legend( prop={'size':'smaller'} )

  ax.set_xticks([ int(E(x)) for x in range(int(e0), int(e1), 500)])
  ax.set_xticklabels([])
  ax.set_xlabel("Easting (0.5 km step)", size='smaller')

  ax.set_yticks([ int(N(y)) for y in range(int(n0), int(n1+5000), 500)])
  ax.set_yticklabels([])
  ax.set_ylabel("Northing (0.5 km step)", size='smaller')

  #pp.savefig('tx%d_%04d.%02d.%02d_%02d.%02d.%02d.png' % (options.tx_id, 
  #   t.tm_year, t.tm_mon, t.tm_mday,
  #   t.tm_hour, t.tm_min, t.tm_sec))

  pp.savefig('tx%d.png' % options.tx_id)

else: 
  
  # Plot locations. 
  pp.plot( 
   map(lambda (P, t): P.imag, track), 
   map(lambda (P, t): P.real, track), '.', alpha=0.3)

  pp.savefig('tx%d.png' % options.tx_id)

