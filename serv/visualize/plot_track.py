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
from optparse import OptionParser

parser = OptionParser()

parser.description = '''\
Plot tracks. This program is 
part of QRAAT, an automated animal tracking system based on GNU Radio.   
'''

parser.add_option('--tx-id', type='int', metavar='INT', default=51,
                  help="Serial ID of the target transmitter in the database "
                       "context.")

parser.add_option('--t-start', type='float', metavar='SEC', default=1376420800.0, 
                  help="Start time in secondes after the epoch (UNIX time).")

parser.add_option('--t-end', type='float', metavar='SEC', default=1376442000.0,
                  help="End time in secondes after the epoch (UNIX time).")

(options, args) = parser.parse_args()


db_con = qraat.util.get_db('reader')

# A possible way to calculate good tracks. Compute the tracks
# with some a priori maximum speed that's on the high side. 
track = qraat.track(db_con, options.t_start, options.t_end, options.tx_id, 10) 

# We then calculate statistics on the transition speeds in the 
# critical path. Plotting the tracks might reveal spurious points
# that we want to filter out. 
(mean, std) = track.speed()
print "(mu=%.4f, sigma=%.4f)" % (mean, std)

# Recompute the tracks, using the mean + one standard deviation as
# the maximum speed. 
track.recompute(mean + std)

# Plot sites.
sites = qraat.csv(db_con=db_con, db_table='sitelist')
pp.plot(
 [s.easting for s in sites], 
 [s.northing for s in sites], 'ro')

# Plot locations. 
pp.plot( 
 map(lambda (P, t): P.imag, track), 
 map(lambda (P, t): P.real, track), '.', alpha=0.3)

pp.show()



        
     


