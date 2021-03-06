#!/usr/bin/env python2
# plot_ll.py. This script is part of QRAAT, an automated 
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
import qraat.srv
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

parser.add_option('--t-start', type='float', metavar='SEC', default=1376432040,#1376420800.0, 
                  help="Start time in secondes after the epoch (UNIX time).")

parser.add_option('--t-end', type='float', metavar='SEC', default=1376432160,#1376442000.0,#1376427800 yields 302 rows
                  help="End time in secondes after the epoch (UNIX time).")

(options, args) = parser.parse_args()

def maxima(ll, K): # TODO 
  return [np.argmax(ll)]

def plot_ll(bl, i, j):
  ''' Plot search space, return point of maximum likelihood. '''

  fig = pp.gcf()
  
  constraints = {}
  # Add up bearing likelihoods for each site. 
  for e in range(i, j): 
    if constraints.get(bl.site_id[e]) == None:
      constraints[bl.site_id[e]] = bl.likelihoods[e,]
    else: 
      constraints[bl.site_id[e]] += bl.likelihoods[e,]

  for (s, ll) in constraints.iteritems(): 

    indexMax = np.argmax(ll)
    x = map(lambda x0 : x0 % 360, 
             range(indexMax - 180, indexMax + 180))
    
    fig = pp.figure()
    ax = fig.add_subplot(1,1,1)
    ax.axis([0, 360, 0, ll[indexMax] + (0.15 * ll[indexMax])])

    ax.fill_between(range(0,360), [ll[x0] for x0 in x], 0, color='b', 
      alpha='0.20', label='Data window')

    print "SiteID =", s
    for i in maxima(ll, K=1):
      ax.plot([180, 180], [0, ll[i]], '-', color='0.30', 
        label='Max likelihood')

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

    t = time.localtime((bl.time[i] + bl.time[j]) / 2)
    pp.title('%04d-%02d-%02d %02d%02d:%02d txID=%d' % (
       t.tm_year, t.tm_mon, t.tm_mday,
       t.tm_hour, t.tm_min, t.tm_sec,
       options.tx_id))
  
    pp.savefig('tx%d_%04d.%02d.%02d_%02d.%02d.%02d_%d.png' % (options.tx_id, 
      t.tm_year, t.tm_mon, t.tm_mday,
      t.tm_hour, t.tm_min, t.tm_sec, s))

    pp.clf()



db_con = qraat.srv.util.get_db('reader')

print "plot_ll: fetching site data."
sv = qraat.srv.position.steering_vectors(db_con, options.cal_id)

print "plot_ll: fetching signal data."
sig = qraat.srv.position.signal(db_con, 
                            options.t_start, 
                            options.t_end,
                            options.tx_id)

print "plot_ll: calculating bearing likelihood distributions (%d records)." % len(sig)
bl = qraat.srv.position.bearing(sv, sig)

#: The time step (in seconds) for the position estimation
#: calculation.
t_delta = options.t_delta

#: Time averaging window (in seconds). 
t_window = options.t_window

try: 

  for (t, index_list) in qraat.srv.position.calc_windows(bl, t_window, t_delta):
    (i, j) = (index_list[0], index_list[-1])

    t = time.localtime((bl.time[i] + bl.time[j]) / 2)
    w_sites = set(bl.site_id[i:j])
    
    plot_ll(bl, i, j)

    print '%04d-%02d-%02d %02d%02d:%02d %d' % (
     t.tm_year, t.tm_mon, t.tm_mday,
     t.tm_hour, t.tm_min, t.tm_sec,
     j - i)

except KeyboardInterrupt: pass

finally:
  pass
