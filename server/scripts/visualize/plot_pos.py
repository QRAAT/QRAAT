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

import qraat, qraat.srv
import matplotlib.pyplot as pp
import matplotlib.image as mpimg
import numpy as np
import time, sys
from optparse import OptionParser

parser = OptionParser()

parser.description = '''\
Plot tracks. This program is 
part of QRAAT, an automated animal tracking system based on GNU Radio.   
'''

parser.add_option('--dep-id', type='int', metavar='INT', default=51,
                  help="Serial ID of the target transmitter in the database "
                       "context.")

parser.add_option('--t-start', type='float', metavar='SEC', default=1376420800, 
                  help="Start time in secondes after the epoch (UNIX time).")

parser.add_option('--t-end', type='float', metavar='SEC', default=1376442000,
                  help="End time in secondes after the epoch (UNIX time).")

(options, args) = parser.parse_args()

overlay = True

db_con = qraat.srv.util.get_db('reader')

cur = db_con.cursor()
  

T = options.t_start
T_step =  60 * 60 * 24 * 1 / 6 # four hour chunks. 

while T < options.t_end:  
  cur.execute('''SELECT northing, easting, timestamp, likelihood
                   FROM position
                  WHERE (%f <= timestamp) 
                    AND (timestamp <= %f)
                    AND deploymentID = %d
                  ORDER BY timestamp ASC''' % (T - T_step, T + T_step, options.dep_id))
  
  T += T_step
  track = []
  for pos in cur.fetchall():
    track.append((np.complex(pos[0], pos[1]), float(pos[2])))

  if len(track) == 0: 
    print >>sys.stderr, "plot_pos: skipping empty window."
    continue

  cur.execute('SELECT northing, easting FROM qraat.location WHERE name="site34"')
  (n, e) = cur.fetchone()
  beacon = np.complex(n, e)
  a = open('dist.txt', 'w') 
  a.write('distance\n')
  for (pos, t) in track:
    a.write('%f\n' % np.abs(pos - beacon))
  a.close()


  if overlay: 

    # FIXME Where/how to install this file? 
    bg = mpimg.imread('qr-overlay.png') 

    e0 = 572599.5 - 150
    e1 = 577331.4 - 150

    n0 = 4259439.5 + 110 + 60 - 20 - 500 
    n1 = 4259483.7 + 210 + 85 -  20 - 500 

    E = lambda(x) : float(bg.shape[1]) * (x - e0) /  (e1 - e0)
    N = lambda(y) : bg.shape[0] - (y - n0) / float(bg.shape[0]) * (n1 - n0)


    sites = qraat.csv.csv(db_con=db_con, db_table='site')
    
    fig = pp.figure()
    ax = fig.add_subplot(1,1,1)

    #pp.text(E(track[0][0].imag) + 10, N(track[0][0].real) + 10, "Start", color='gray', size='smaller')
    #pp.text(E(track[-1][0].imag) + 10, N(track[-1][0].real) + 10, "End", color='gray', size='smaller')

    # Plot tracks. 
    pp.scatter( 
     map(lambda (P, t): E(P.imag), track), 
     map(lambda (P, t): N(P.real), track), alpha=0.2, s=2, c='k', 
       label='Transmitter positions')

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
         options.dep_id), size='smaller')

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

    pp.savefig('tx%d_%04d-%02d-%02d_%02d%02d.png' % (options.dep_id, t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min))

  else: 
    
    # Plot locations. 
    pp.plot( 
     map(lambda (P, t): P.imag, track), 
     map(lambda (P, t): P.real, track), '.', alpha=0.3)

    pp.savefig('tx%d.png' % options.tx_id)
  
