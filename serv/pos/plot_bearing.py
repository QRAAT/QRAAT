#!/usr/bin/python
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
#
# TODO 
# - Probability calculatio is wrong ... gotta figure this out. 
# - Write class bearing, which will replace bearing_likelihoods. 


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

def plot_distribution(p, ll, t, s):

  fig = pp.gcf()

  indexMax = np.argmax(ll) 
  x = map(lambda x0 : x0 % 360, 
           range(indexMax - 180, indexMax + 180))
  
  fig = pp.figure()
  ax = fig.add_subplot(1,1,1)
  ax.axis([0, 360, 0, ll[indexMax] + (0.15 * ll[indexMax])])

  ax.fill_between(range(0,360), [ll[x0] for x0 in x], 0, color='b',
    alpha='0.20', label='Data window')

  ax.plot(range(0,360), [p[x0] for x0 in x], color='g')

  ax.plot([180, 180], [0, ll[indexMax]], '-', color='0.30', 
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

  pp.title('%04d-%02d-%02d %02d%02d:%02d txID=%d' % (
     t.tm_year, t.tm_mon, t.tm_mday,
     t.tm_hour, t.tm_min, t.tm_sec,
     options.tx_id))

  pp.savefig('tx%d_%04d.%02d.%02d_%02d.%02d.%02d_%d.png' % (options.tx_id, 
    t.tm_year, t.tm_mon, t.tm_mday,
    t.tm_hour, t.tm_min, t.tm_sec, s))

  pp.clf()



db_con = qraat.util.get_db('reader')
data = qraat.est2(db_con, options.t_start, options.t_end, options.tx_id)

# Hijacking this functionality to test est2. 
bl = qraat.position.bearing_likelihoods(db_con, options.cal_id)
bl.est_ids = bl.sig_id = data.id
bl.site_id = data.site_id
bl.est_time = data.timestamp
bl.signal  = data.ed
bl.calc_likelihoods()


def calc_prob_distribution(bl, est, t):
  
  p  = np.zeros(360)
  ll = np.zeros(360)

  # Noise covariance matrix.
  Sigma = est.nc[t]

  # Signal power covariance. 
  sigma = est.edsp[t] - np.trace(Sigma)
  
  # Observed signal. 
  V = est.ed[t]

  print "SIGMA", Sigma
  print "sigma", sigma
  print "V", V

  b = (np.pi ** est.N) 
  
  # Steering vectors.
  for (theta, G) in zip(bl.bearings[bl.site_id[t]], bl.steering_vectors[bl.site_id[t]]):
    
    # Signal covariance matrix. 
    R = (sigma * np.dot(G, np.conj(np.transpose(G)))) + Sigma

    a = np.dot(np.dot(np.conj(np.transpose(V)), np.linalg.inv(R)), V) 
          
    p[theta] = np.exp(-1 * a.real) / (b * np.linalg.det(R).real)
    
    left_half = np.dot(V, np.conj(np.transpose(G)))
    ll[theta] = (left_half * np.conj(left_half)).real

  print "P(theta) range:", min(p), max(p)
  return (p + 0.5, ll)
  


i = 0
(p, ll) = calc_prob_distribution(bl, data, i) 
plot_distribution( p, ll,     
                   time.localtime(bl.est_time[i]), 
                   bl.site_id[i] )

