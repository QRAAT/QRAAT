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
import qraat, qraat.srv
from optparse import OptionParser

parser = OptionParser()

parser.description = '''\
Plot the search space for position estimation. This program is 
part of QRAAT, an automated animal tracking system based on GNU Radio.   
'''

parser.add_option('--cal-id', type='int', metavar='INT', default=3,
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


parser.add_option('--band-filter', action='store_true', default=False,  
                  help="Apply band filter to signal data. DEPRECATE.") # FIXME deprecatue

(options, args) = parser.parse_args()


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
      pass 

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
#  for (site_id, (L_i, L_j)) in bl.calc_constraints(i, j).iteritems():
#        
#        L = L_i
#        if L.pos:  # --->
#          x_range = (L.x_p, x_right)
#        else:      # <---
#          x_range = (x_left, L.x_p)
#        
#        # Reflect line over 'y = x' and transform to 
#        # image's coordinate space. 
#        x = [n(L(x_range[0])) - n(L.y_p) + e(L.x_p), 
#             n(L(x_range[1])) - n(L.y_p) + e(L.x_p)]
#
#        y = [e(x_range[0]) - e(L.x_p) + n(L.y_p), 
#             e(x_range[1]) - e(L.x_p) + n(L.y_p)]
#        
#        # Plot constraints. 
#        pp.plot(x, y, 'k-')

  # TODO plot constrained search space

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

print "plot_search_space: fetching site data."
sv = qraat.srv.position.steering_vectors(db_con, options.cal_id)

print "plot_search_space: fetching signal data."
sig = qraat.srv.position.signal(db_con, 
                            options.t_start, 
                            options.t_end, 
                            options.tx_id,
                            options.band_filter)

print "plot_search_space: calculating bearing likelihoods (%d records)." % len(sig)
bl = qraat.srv.position.bearing(sv, sig)

#: The time step (in seconds) for the position estimation
#: calculation.
t_delta = options.t_delta

#: Time averaging window (in seconds). 
t_window = options.t_window

print "plot_search_space: plotting."

try: 

  for (t, index_list) in qraat.position.calc_windows(bl, t_window, t_delta):

    (i, j) = (index_list[0], index_list[-1])

    #scale = 100
    #pos = center
    #while scale >= 1: 
    #  pos = plot_search_space(i, j, pos, scale)
    #  scale /= 10

    t = time.localtime((bl.time[i] + bl.time[j]) / 2)
    w_sites = set(bl.site_id[i:j])

    if len(w_sites) > 1: 
      (pos, pos_likelihood) = calculate_search_space(bl, i, j, qraat.srv.position.center, 10, 150)
      plot_search_space(pos_likelihood, i, j, qraat.srv.position.center, 10, 150) # FIXME !!!
      print '%04d-%02d-%02d %02d%02d:%02d %-8d %.2fN %.2fE %s' % (
       t.tm_year, t.tm_mon, t.tm_mday,
       t.tm_hour, t.tm_min, t.tm_sec,
       j - i, pos.real, pos.imag, set(bl.site_id[i:j]))

    else: 
      print '%04d-%02d-%02d %02d%02d:%02d %-8d %s not enough data' % (
       t.tm_year, t.tm_mon, t.tm_mday,
       t.tm_hour, t.tm_min, t.tm_sec,
       j - i, set(bl.site_id[i:j]))

except KeyboardInterrupt: pass

finally:
  pass
