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




def get_constraints(bl, i, j, half_span=15): 
  ''' Get linear constraints on search space. '''
  ll_sum = {}

  # Add up bearing likelihoods for each site. 
  for k in range(i, j): 
    if ll_sum.get(bl.site_id[k]) == None:
      ll_sum[bl.site_id[k]] = bl.likelihoods[k,]
    else: 
      ll_sum[bl.site_id[k]] += bl.likelihoods[k,]

  r = {}
  for (site_id, ll) in ll_sum.iteritems():
    theta_max = np.argmax(ll)
    r[site_id] = ((theta_max - half_span) % 360, (theta_max + half_span) % 360)
  
  constraints = {}
  for (site_id, (theta_i, theta_j)) in r.iteritems():
    constraints[site_id] = qraat.position.halfplane.from_bearings(
                                bl.sites.get(ID=site_id).pos, theta_i, theta_j)

  for site_id in r.keys():
    print r[site_id], constraints[site_id]
    
  return constraints




def calculate_search_space(bl, i, j, center, scale, half_span=15):
  ''' Plot search space, return point of maximum likelihood. '''
    
  #: Generate candidate points centered around ``center``.
  grid = np.zeros((half_span*2+1, half_span*2+1),np.complex)
  for e in range(-half_span,half_span+1):
    for n in range(-half_span,half_span+1):
      grid[e + half_span, n + half_span] = center + np.complex(n * scale, e * scale)

  #: The third dimension of the search space: bearings from each
  #: candidate point to each receiver site.
  site_bearings = {}
  for site in bl.sites:
    #site_bearings[:,:,sv_index] = np.angle(grid - site.pos) * 180 / np.pi
    site_bearings[site.ID] = np.angle(grid - site.pos) * 180 / np.pi
  #site_bearings = np.zeros(np.hstack((grid.shape,len(bl.sites))))

  #: Based on bearing bl.likelihoods for EST's in time range, calculate
  #: the log likelihood of each candidate point.
  pos_likelihood = np.zeros(site_bearings[bl.sites[0].ID].shape[0:2])
  for est_index in range(i, j):
    sv_index = bl.site_id[est_index]
    try:
      pos_likelihood += np.interp(site_bearings[sv_index],
                                range(-360, 360),
                                np.hstack((bl.likelihoods[est_index,:],
                                bl.likelihoods[est_index,:])) )
      # SEAN: Would use bl.likelihood_deps right here if I was using them
    except KeyError:
      pass # Skip sites in the site list where we don't collect data. 
           # TODO perhaps there should be a row in qraat.sitelist that 
           # designates sites as qraat nodes. ~ Chris 1/2/14 

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
  for (site_id, (L_i, L_j)) in get_constraints(bl, i, j).iteritems():
        
        L = L_i
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

        L = L_j
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
    [e(float(s.easting)) for s in bl.sites],
    [n(float(s.northing)) for s in bl.sites],
     s=15, facecolor='0.5', label='sites', zorder=10)
  
  pp.clim()   # clamp the color limits
  pp.legend()
  pp.axis([0, half_span * 2, 0, half_span * 2])
  
  t = time.localtime((bl.time[i] + bl.time[j]) / 2)
  pp.title('%04d-%02d-%02d %02d%02d:%02d txID=%d' % (
       t.tm_year, t.tm_mon, t.tm_mday,
       t.tm_hour, t.tm_min, t.tm_sec,
       options.tx_id))
  
  pp.savefig('tx%d_%04d.%02d.%02d_%02d.%02d.%02d_%03dm.png' % (options.tx_id, 
     t.tm_year, t.tm_mon, t.tm_mday,
     t.tm_hour, t.tm_min, t.tm_sec, scale))
  pp.clf()




db_con = qraat.util.get_db('reader')

print "plot_seach_space: getting steering vectors"
sv = qraat.position.steering_vectors(db_con, options.cal_id)

print "plot_seach_space: getting est data"
est = qraat.est2(db_con, 
                 options.t_start, 
                 options.t_end, 
                 options.tx_id)

print "plot_seach_space: calculating bearing likelihoods (%d records)" % len(est)
bl = qraat.position.bearing(sv, est)

#: The time step (in seconds) for the position estimation
#: calculation.
t_delta = options.t_delta

#: Time averaging window (in seconds). 
t_window = options.t_window

print "plot_search_space: plotting"

i = 0

try: 
  while i < len(bl) - 1:

    # Find the index j corresponding to the end of the time window. 
    j = i + 1
    while j < len(bl) - 1 and (bl.time[j + 1] - bl.time[i]) <= t_window: 
      j += 1
    
    #scale = 100
    #pos = center
    #while scale >= 1: 
    #  pos = plot_search_space(i, j, pos, scale)
    #  scale /= 10

    t = time.localtime((bl.time[i] + bl.time[j]) / 2)
    w_sites = set(bl.site_id[i:j])

    if len(w_sites) > 1: 
      (pos, pos_likelihood) = calculate_search_space(bl, i, j, qraat.position.center, 10, 150)
      plot_search_space(pos_likelihood, i, j, qraat.position.center, 10, 150)
      print '%04d-%02d-%02d %02d%02d:%02d %-8d %.2fN %.2fE %s' % (
       t.tm_year, t.tm_mon, t.tm_mday,
       t.tm_hour, t.tm_min, t.tm_sec,
       j - i, pos.real, pos.imag, set(bl.site_id[i:j]))

    else: 
      print '%04d-%02d-%02d %02d%02d:%02d %-8d %s not enough data' % (
       t.tm_year, t.tm_mon, t.tm_mday,
       t.tm_hour, t.tm_min, t.tm_sec,
       j - i, set(bl.site_id[i:j]))

    # Step index i forward t_delta seconds. 
    j = i + 1
    while i < len(bl) - 1 and (bl.time[i + 1] - bl.time[j]) <= t_delta: 
      i += 1

except KeyboardInterrupt: pass

finally:
  pass
