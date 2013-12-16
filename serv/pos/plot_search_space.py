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

parser.add_option('--t-start', type='float', metavar='SEC', default=1376420800.0, 
                  help="Start time in secondes after the epoch (UNIX time).")

parser.add_option('--t-end', type='float', metavar='SEC', default=1376427800,#1376442000.0,#1376427800 yields 302 rows
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


class halfplane: 
  ''' A two-dimensional linear inequality. 

    Compute the slope and y-intercept of the line defined by point ``p`` 
    and bearing ``theta``. Format of ``p`` is np.complex(real=northing, 
    imag=easting). Also, ``pos`` is set to True if the vector theta goes 
    in a positive direction along the x-axis. 
  ''' 
  
  #: The types of plane constrains:
  #: greater than, less than, greater than
  #: or equal to, less than or equal to. 
  plane_t = qraat.enum('GT', 'LT', 'GE', 'LE')
  plane_string = { plane_t.GT : '>', 
                   plane_t.LT : '<', 
                   plane_t.GE : '>=', 
                   plane_t.LE : '<=' }

  def __init__ (self, p, theta):

    self.x_p = p.imag
    self.y_p = p.real
    self.m = np.tan(np.pi * theta / 180) 
    self.plane = None

    if (0 <= theta and theta <= 90) or (270 <= theta and theta <= 360):
      self.pos = True
    else: self.pos = False 

    if (0 <= theta and theta <= 180):
      self.y_pos = True
    else: self.y_pos = False

  def __repr__ (self): 
    s = 'y %s %.02f(x - %.02f) + %.02f' % (self.plane_string[self.plane], 
                                           self.m, self.x_p, self.y_p)
    return '%-37s' % s

  def __call__ (self, x): 
    return self.m * (x - self.x_p) + self.y_p

  def inverse(self, y): 
    return ((y - self.y_p) + (self.m * self.x_p)) / self.m

  @classmethod
  def from_bearings(cls, p, theta_i, theta_j):
    # TODO get plane constraints right.
    Ti = cls(p, theta_i)
    Ti.plane = cls.plane_t.GT
    Tj = cls(p, theta_j) 
    Tj.plane = cls.plane_t.GT
    return (Ti, Tj)    





def get_constraints(i, j, threshold=1.0): 
  ''' Get linear constraints on search space. '''
  constraints = {}

  # Add up bearing likelihoods for each site. 
  for e in range(i, j): 
    if constraints.get(site_id[e]) == None:
      constraints[site_id[e]] = likelihoods[e,]
    else: 
      constraints[site_id[e]] += likelihoods[e,]

  # Get bearing ranges of log likelihoods above threshold. 
  # TODO this could be done more statistically soundly. 
  #   How to decide if a dip between two curves is wide and 
  #   deep enough to treat the two curves as separate bearing
  #   arcs or as one? 
  r = {}
  for (e, ll) in constraints.iteritems():
    r[e] = []
    above = False
    for j in range(ll.shape[0]):
      if ll[j] >= threshold and not above: 
        i = j
        above = True
    
      elif ll[j] < threshold and above: 
        r[e].append((i, j-1))
        above = False 

    if above: # Fix wrap around  
      r[e][0] = (i, r[e][0][1])

    #print e, r[e]
    #print ll
    #print ' ---------- '

  constraints = {}
  for (e, ranges) in r.iteritems():
    constraints[e] = []
    p = site_pos[site_pos_id.index(e)]
    for (theta_i, theta_j) in ranges: 
      constraints[e].append(
        halfplane.from_bearings(p, theta_i, theta_j)) 

  return constraints




def calculate_search_space(i, j, center, scale, half_span=15):
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
  
  return (grid.flat[np.argmax(pos_likelihood)], pos_likelihood)

def plot_search_space(pos_likelihood, i, j, center, scale, half_span=15):
  ''' Plot search space, return point of maximum likelihood. '''

  fig = pp.gcf()
  
  # Search space
  p = pp.imshow(pos_likelihood.transpose(), 
      origin='lower',
      extent=(0, half_span * 2, 0, half_span * 2))

  # Transform to plot's coordinate system.
  e = lambda(x) : ((x - center.imag) / scale) + half_span
  n = lambda(y) : ((y - center.real) / scale) + half_span 
  
  x_left =  center.imag - (half_span * scale)
  x_right = center.imag + (half_span * scale)

  # Constraints
  for (s, constraints) in get_constraints(i, j, 6).iteritems():
    for constraint in constraints: 
      for L in constraint: 
        if L.pos:  # --->
          x_range = (L.x_p, x_right)
        else:      # <---
          x_range = (x_left, L.x_p)
        
        # Reflect line over 'y = x' and transform to 
        # image's coordinate space. 
        x = [n(L(x_range[0])) - n(L.y_p) + e(L.x_p), 
             n(L(x_range[1])) - n(L.y_p) + e(L.x_p)]

        y = [e(x_range[0]) - e(L.x_p) + n(L.y_p), 
             e(x_range[1]) - e(L.x_p) + n(L.y_p)]
        
        # Plot constraints. 
        pp.plot(x, y, 'k-')
    
  # Sites
  pp.scatter(
    [e(float(s.easting)) for s in sites],
    [n(float(s.northing)) for s in sites],
     s=15, facecolor='0.5', label='sites', zorder=10)
  
  pp.clim()   # clamp the color limits
  pp.legend()
  pp.axis([0, half_span * 2, 0, half_span * 2])
  
  t = time.localtime((est_time[i] + est_time[j]) / 2)
  pp.title('%04d-%02d-%02d %02d%02d:%02d txID=%d' % (
       t.tm_year, t.tm_mon, t.tm_mday,
       t.tm_hour, t.tm_min, t.tm_sec,
       options.tx_id))
  
  pp.savefig('tx%d_%04d.%02d.%02d_%02d.%02d.%02d_%03dm.png' % (options.tx_id, 
     t.tm_year, t.tm_mon, t.tm_mday,
     t.tm_hour, t.tm_min, t.tm_sec, scale))
  pp.clf()






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
      (pos, pos_likelihood) = calculate_search_space(i, j, center, 10, 150)
      plot_search_space(pos_likelihood, i, j, center, 10, 150)
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
