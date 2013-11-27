#!/usr/bin/python
# plot_search_space.py. This script is part of QRAAT, an automated 
# animal tracking system based on GNU Radio. 
#
# Wood rat data: 
# python plot_search_space.py --t-start=1381756000 --t-end=1381768575 --tx-id=52
#
# Mice: 
# python plot_search_space.py --t-start=0 --t-end=1381768575 --tx-id=35
#  Modified EST select to 'mice' instead of 'est'. 
#
# Copyright (C) 2013 Christopher Patton, Todd Borrowman
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

import matplotlib.pyplot as pp
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm
from matplotlib.ticker import LinearLocator, FormatStrFormatter

import MySQLdb as mdb
import numpy as np
import time, os, sys
import qraat
from optparse import OptionParser

parser = OptionParser()

parser.description = '''\
Plot the search space for position estimation. This program is 
part of QRAAT, an automated animal tracking system based on GNU Radio.   
'''

parser.add_option('--cal-id', type='int', metavar='INT', default=1,
                  help="Calibration ID, the serial identifier in the database "
                       "context identifying a calibration run. (Default is 1.)")

parser.add_option('--tx-id', type='int', metavar='INT', default=51,
                  help="Serial ID of the target transmitter in the database "
                       "context.")

parser.add_option('--t-delta', type='float', metavar='SEC', default=1.0,
                  help="Time step for each position calculation. (Default "
                       "is 1.0 seconds.) ")

parser.add_option('--t-window', type='float', metavar='SEC', default=30.0,
                  help="Time window to use for the position likelihood "
                       "calculation at each time step. (Default is 30.0 "
                       "seconds.)")

parser.add_option('--t-start', type='float', metavar='SEC', default=1376420800.0, 
                  help="Start time in secondes after the epoch (UNIX time).")

parser.add_option('--t-end', type='float', metavar='SEC', default=1376442000.0,#1376427800 yields 302 rows
                  help="End time in secondes after the epoch (UNIX time).")

(options, args) = parser.parse_args()

# Get database credentials. 
try: 
  db_config = qraat.csv("%s/db_auth" % os.environ['RMG_SERVER_DIR']).get(view='reader')

except KeyError: 
  print >>sys.stderr, "position: error: undefined environment variables. Try `source rmg_env.`" 
  sys.exit(1) 

except IOError, e: 
  print >>sys.stderr, "position: error: missing DB credential file '%s'." % e.filename
  sys.exit(1)

# Connect to the database. 
db_con = mdb.connect(db_config.host, 
                     db_config.user,
                     db_config.password,
                     db_config.name)
cur = db_con.cursor()

print "position: fetching site and cal data"

# Get site locations.
sites = qraat.csv(db_con=db_con, db_table='sitelist')

# Get steering vector data.
steering_vectors = {} # site.ID -> sv
bearings = {}         # site.ID -> bearing

for site in sites:
  cur.execute('''SELECT Bearing, 
                        sv1r, sv1i, sv2r, sv2i, 
                        sv3r, sv3i, sv4r, sv4i 
                   FROM Steering_Vectors 
                  WHERE SiteID=%d and Cal_InfoID=%d''' % (site.ID, options.cal_id))
  sv_data = np.array(cur.fetchall(),dtype=float)
  if sv_data.shape[0] > 0:
    steering_vectors[site.ID] = np.array(sv_data[:,1::2] + np.complex(0,1) * sv_data[:,2::2])
    bearings[site.ID] = np.array(sv_data[:,0])

print "position: fetching pulses for transmitter and time range"

# Get pulses in time range.  
cur.execute('''SELECT ID, siteid, timestamp,
                      ed1r, ed1i, ed2r, ed2i,
                      ed3r, ed3i, ed4r, ed4i
                 FROM est
                WHERE timestamp >= %s
                  AND timestamp <= %s
                  AND txid = %s
                ORDER BY timestamp''', (options.t_start, 
                                        options.t_end, 
                                        options.tx_id))

signal_data = np.array(cur.fetchall(), dtype=float)
est_ct = signal_data.shape[0]
if est_ct == 0:
  print >>sys.stderr, "position: fatal: no est records for selected time range."
  sys.exit(1)
else: print "position: processing %d records" % est_ct

sig_id =   np.array(signal_data[:,0], dtype=int)
site_id =  np.array(signal_data[:,1], dtype=int)
est_time = signal_data[:,2]
signal =   signal_data[:,3::2]+np.complex(0,-1)*signal_data[:,4::2]

print "position: calculating pulse bearing likelihoods"

# Calculate the likelihood of each bearing for each pulse. 
likelihoods = np.zeros((est_ct,360))
for i in range(est_ct):
  try: 
    sv =  steering_vectors[site_id[i]]
  except KeyError:
    print >>sys.stderr, "position: error: no steering vectors for site ID=%d" % site_id[i]
    sys.exit(1)

  sig = signal[i,np.newaxis,:]
  left_half = np.dot(sig, np.conj(np.transpose(sv)))
  bearing_likelihood = (left_half * np.conj(left_half)).real
  for j, value in enumerate(bearings[site_id[i]]):
    likelihoods[i, value] = bearing_likelihood[0, j]



# Format site locations as np.complex's. 
site_pos = np.zeros((len(sites),),np.complex)
site_pos_id = []
for j in range(len(sites)):
  site_pos[j] = np.complex(sites[j].northing, sites[j].easting)
  site_pos_id.append(sites[j].ID)



def plot_search_space(i, j, center, scale, half_span=15):
  ''' Plot search space, return point of maximum likelihood. '''
  
  #: Generate candidate points centered around ``center``. 
  grid = np.zeros((half_span*2+1, half_span*2+1),np.complex)
  for e in range(-half_span, half_span+1):
    for n in range(-half_span, half_span+1):
      grid[e + half_span, n + half_span] = center + np.complex(n * scale, e * scale)

  #: The third dimension of the search space: bearings from each 
  #: candidate point to each receiver site. 
  site_bearings = np.zeros(np.hstack((grid.shape,len(site_pos_id))))
  for sv_index, id_index in enumerate(site_pos_id):
    site_bearings[:,:,sv_index] = np.angle(
      grid - site_pos[site_pos_id.index(id_index)]) * 180 / np.pi

  #: Based on bearing likeli hoods for EST's in time range, calculate
  #: the log likelihood of each candidate point. 
  pos_likelihood = np.zeros(site_bearings.shape[0:2])
  for est_index in range(i, j): 
    sv_index = site_pos_id.index(site_id[est_index])
    pos_likelihood += np.interp(site_bearings[:,:,sv_index], 
                                range(-360, 360), 
                                np.hstack((likelihoods[est_index,:], 
                                likelihoods[est_index,:])) )
  pos = grid.flat[np.argmax(pos_likelihood)]

  t = time.localtime((est_time[i] + est_time[j]) / 2)
  
  fig = pp.gcf()
  p = pp.imshow(pos_likelihood.transpose(), 
      origin='lowerleft', 
      extent=(0, half_span * 2, 0, half_span * 2)) # search space

  pp.scatter(
    [((float(s.easting) - center.imag) / scale) + half_span for s in sites],
    [((float(s.northing) - center.real) / scale) + half_span for s in sites],
     s=15, facecolor='0.5', label='sites') # sites
 
  #pp.plot( # sites 
  #  [grid[s.easting,] for s in sites], 
  #  [grid[,s.northing] for s in sites], 'ro')
  
  pp.clim()   # clamp the color limits
  pp.legend()
  pp.title('%04d-%02d-%02d %02d%02d:%02d txID=%d' % (
       t.tm_year, t.tm_mon, t.tm_mday,
       t.tm_hour, t.tm_min, t.tm_sec,
       options.tx_id))
  
  pp.savefig('tx%d_%04d.%02d.%02d_%02d.%02d.%02d_%03dm.png' % (options.tx_id, 
     t.tm_year, t.tm_mon, t.tm_mday,
     t.tm_hour, t.tm_min, t.tm_sec, scale))
  pp.clf()

  return pos


#: Calculated positions (time, pos). 
pos_est = [] 

#: The time step (in seconds) for the position estimation
#: calculation.
t_delta = options.t_delta

#: Time averaging window (in seconds). 
t_window = options.t_window

#: Center of Quail Ridge reserve (northing, easting). This is the first
#: "candidate point" used to construct the search space grid. 
center = np.complex(4260500, 574500) 

print "position: calculating position"

i = 0

try: 
  while i < est_ct - 1:

    # Find the index j corresponding to the end of the time window. 
    j = i + 1
    while j < est_ct - 1 and (est_time[j + 1] - est_time[i]) <= t_window: 
      j += 1
    
    #scale = 100
    #pos = center
    #while scale >= 1: 
    #  pos = plot_search_space(i, j, pos, scale)
    #  scale /= 10

    t = time.localtime((est_time[i] + est_time[j]) / 2)
    w_sites = set(site_id[i:j])

    if len(w_sites) > 1: 
      pos = plot_search_space(i, j, center, 10, 150)
      print '%04d-%02d-%02d %02d%02d:%02d %-8d %.2fN %.2fE %s' % (
       t.tm_year, t.tm_mon, t.tm_mday,
       t.tm_hour, t.tm_min, t.tm_sec,
       j - i, pos.real, pos.imag, set(site_id[i:j]))

    else: 
      print '%04d-%02d-%02d %02d%02d:%02d %-8d %s not enough data' % (
       t.tm_year, t.tm_mon, t.tm_mday,
       t.tm_hour, t.tm_min, t.tm_sec,
       j - i, set(site_id[i:j]))

    # Step index i forward t_delta seconds. 
    j = i + 1
    while i < est_ct - 1 and (est_time[i + 1] - est_time[j]) <= t_delta: 
      i += 1

except KeyboardInterrupt: pass

finally:
  pass
