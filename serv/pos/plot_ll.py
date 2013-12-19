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
# Copyright (C) 2013 Christopher Patton, Joe Webster
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

parser.add_option('--t-start', type='float', metavar='SEC', default=1376432040,#1376420800.0, 
                  help="Start time in secondes after the epoch (UNIX time).")

parser.add_option('--t-end', type='float', metavar='SEC', default=1376432160,#1376442000.0,#1376427800 yields 302 rows
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
    print >>sys.stderr, "position: error: no steering vectors for siteID=%d" % site_id[i]
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



def plot_ll(i, j):
  ''' Plot search space, return point of maximum likelihood. '''

  fig = pp.gcf()
  
  constraints = {}
  # Add up bearing likelihoods for each site. 
  for e in range(i, j): 
    if constraints.get(site_id[e]) == None:
      constraints[site_id[e]] = likelihoods[e,]
    else: 
      constraints[site_id[e]] += likelihoods[e,]

  for (s, ll) in constraints.iteritems(): 
    
    indexMax = np.argmax(ll) 
    x = map(lambda x0 : x0 % 360, 
             range(indexMax - 180, indexMax + 180))
    
    fig = pp.figure()
    ax = fig.add_subplot(1,1,1)
    ax.axis([0, 360, 0, ll[indexMax] + (0.15 * ll[indexMax])])

    ax.plot(range(0,360), [ll[x0] for x0 in x])
    ax.plot([180, 180], [0, ll[indexMax]], '-', color='0.10', 
      zorder=0, label='max likelihood')
    ax.text(185, (0.03 * ll[indexMax]), '%d$^\circ$' % indexMax)
    if indexMax > 30: 
      ax.text(x.index(0) + 5, (0.03 * ll[indexMax]), '0$^\circ$')
    if abs(indexMax - 90) > 30: 
      ax.text(x.index(90) + 5, (0.03 * ll[indexMax]), '90$^\circ$')
    if abs(indexMax - 180) > 30: 
      ax.text(x.index(180) + 5, (0.03 * ll[indexMax]), '180$^\circ$')
    if abs(indexMax - 270) > 30: 
      ax.text(x.index(270) + 5, (0.03 * ll[indexMax]), '270$^\circ$')
    
    pp.legend()
    pp.setp(ax.get_xticklabels(), visible=False)
    pp.xlabel("Bearing to SiteID=%d" % s)
    pp.ylabel("Likelihood")

    t = time.localtime((est_time[i] + est_time[j]) / 2)
    pp.title('%04d-%02d-%02d %02d%02d:%02d txID=%d' % (
       t.tm_year, t.tm_mon, t.tm_mday,
       t.tm_hour, t.tm_min, t.tm_sec,
       options.tx_id))
  
    pp.savefig('tx%d_%04d.%02d.%02d_%02d.%02d.%02d_%d.png' % (options.tx_id, 
      t.tm_year, t.tm_mon, t.tm_mday,
      t.tm_hour, t.tm_min, t.tm_sec, s))

    pp.clf()






#: The time step (in seconds) for the position estimation
#: calculation.
t_delta = options.t_delta

#: Time averaging window (in seconds). 
t_window = options.t_window

print "position: calculating position"

i = 0

try: 
  while i < est_ct - 1:

    # Find the index j corresponding to the end of the time window. 
    j = i + 1
    while j < est_ct - 1 and (est_time[j + 1] - est_time[i]) <= t_window: 
      j += 1
    
    t = time.localtime((est_time[i] + est_time[j]) / 2)
    w_sites = set(site_id[i:j])
    
    plot_ll(i, j)

    print '%04d-%02d-%02d %02d%02d:%02d %d' % (
     t.tm_year, t.tm_mon, t.tm_mday,
     t.tm_hour, t.tm_min, t.tm_sec,
     j - i)

    # Step index i forward t_delta seconds. 
    j = i + 1
    while i < est_ct - 1 and (est_time[i + 1] - est_time[j]) <= t_delta: 
      i += 1

except KeyboardInterrupt: pass

finally:
  pass
