#!/usr/bin/python2
import MySQLdb
import numpy as np
import time
import argparse
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as pp
import qraat.srv.util
import os

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--directory", type=str, help="directory to store plots in", default="./score_plots")
parser.add_argument("-i", "--deploymentID", type=int, help="deploymentID to plot", default=105)
parser.add_argument("-t", "--start_timestamp", type=int, help="timestamp (in seconds past epoch) to start plot from", default=1411498800)
parser.add_argument("-u", "--duration", type=int, help="time span to plot, in seconds", default=24*60*60)
args = parser.parse_args()

plot_dir = args.directory
start_time = args.start_timestamp
stop_time = start_time+args.duration
deploymentID = args.deploymentID

if not os.path.isdir(plot_dir):
  print "directory, {0}, not found; creating directory".format(plot_dir)
  os.makedirs(plot_dir)
db = qraat.srv.util.get_db('reader')
cursor = db.cursor()

num_records = cursor.execute("select timestamp, edsp, fdsp, edsnr, fdsnr, ec, tnp, center, siteID, score, theoretical_score from est left join estscore on est.ID = estscore.estID where deploymentID=%s and timestamp > %s and timestamp < %s", (deploymentID, start_time, stop_time))
data = np.array(cursor.fetchall(),dtype = float)

num_intervals = cursor.execute("select timestamp, pulse_interval, duration, siteID, pulse_variation from estinterval where deploymentID = %s and timestamp > %s and timestamp < %s", (deploymentID, start_time, stop_time))
interval_data = np.array(cursor.fetchall(),dtype = float)

db.close()

est_score_threshold = float(os.environ['RMG_POS_EST_THRESHOLD'])

print "deploymentID: {0}\ntimestamps: {1} - {2}, {3} - {4}".format(deploymentID, start_time, stop_time, time.strftime("%x %X",time.localtime(start_time)), time.strftime("%x %X",time.localtime(stop_time)))
print "{} records found in est table".format(num_records)
print "{} records not scored".format(np.sum(np.isnan(data[:,9])))
print "{} records with theoretical_score == 0".format(np.sum(data[:,10] == 0))
print "{} records scored < 0".format(np.sum(data[:,9] < 0))
print "{} records scored == 0".format(np.sum(data[:,9] == 0))
print "{} records scored > 0".format(np.sum(data[:,9] > 0))
print "{} intervals found in estinterval table".format(num_intervals)
print "EST score threshold: %0.2f" % est_score_threshold


site_set = set(data[:,8])
for siteID in site_set:
  mask = (data[:,8] == siteID)
  filter_mask = (data[mask,9] / data[mask,10]) > est_score_threshold
  #power filtered
  pp.plot(data[mask,0],10*np.log10(data[mask,1]),'.')
  pp.plot(data[mask,0][filter_mask],10*np.log10(data[mask,1][filter_mask]),'r.')
  pp.xlabel("Time (seconds)")
  pp.ylabel("edsp (dB)")
  pp.title("Time vs. Power, deploymentID={0:d}, siteID={1:.0f}, {2:d}<timestamp<{3:d}".format(deploymentID,siteID,start_time,stop_time))
  pp.legend(['All','Pass Filter'])
  pp.grid(True)
  fig = pp.gcf()
  fig.set_size_inches(16,12)
  pp.savefig("{0}/depID{1:d}_site{2:.0f}_passfilter.png".format(plot_dir,deploymentID,siteID))
  pp.clf()
  #power un-filtered
  pp.plot(data[mask,0],10*np.log10(data[mask,1]),'.')
  pp.plot(data[mask,0][np.invert(filter_mask)],10*np.log10(data[mask,1][np.invert(filter_mask)]),'y.')
  pp.xlabel("Time (seconds)")
  pp.ylabel("edsp (dB)")
  pp.title("Time vs. Power, deploymentID={0:d}, siteID={1:.0f}, {2:d}<timestamp<{3:d}".format(deploymentID,siteID,start_time,stop_time))
  pp.legend(['All','Fail Filter'])
  pp.grid(True)
  fig = pp.gcf()
  fig.set_size_inches(16,12)
  pp.savefig("{0}/depID{1:d}_site{2:.0f}_failfilter.png".format(plot_dir,deploymentID,siteID))
  pp.clf()
  #score
  filter_mask = np.isnan(data[mask,9])+(data[mask,10] == 0)
  pp.plot(data[mask,0][np.invert(filter_mask)],data[mask,9][np.invert(filter_mask)]/data[mask,10][np.invert(filter_mask)],'.')
  pp.plot(data[mask,0][filter_mask],np.zeros((np.sum(filter_mask),)),'g.')
  pp.xlabel("Time (seconds)")
  pp.ylabel("score / theoretical_score")
  pp.title("Time vs. Score, deploymentID={0:d}, siteID={1:.0f}, {2:d}<timestamp<{3:d}".format(deploymentID,siteID,start_time,stop_time))
  pp.legend(["Scored", "Not Scored (set to zero)"])
  pp.grid(True)
  fig = pp.gcf()
  fig.set_size_inches(16,12)
  pp.savefig("{0}/depID{1:d}_site{2:.0f}_score.png".format(plot_dir,deploymentID,siteID))
  pp.clf()
  #interval
  intmask = (interval_data[:,3] == siteID)
  pp.plot(interval_data[intmask,0], interval_data[intmask,1],'.')
  pp.plot(interval_data[intmask,0], interval_data[intmask,4],'r.')
  pp.ylim([0,10])
  pp.xlabel("Time (seconds)")
  pp.ylabel("Pulse Interval (seconds)")
  pp.yticks(np.arange(0,4.4,0.4))
  pp.grid(True)
  pp.title("Time vs. Interval, deploymentID={0:d}, siteID={1:.0f}, {2:d}<timestamp<{3:d}".format(deploymentID,siteID,start_time,stop_time))
  pp.legend(["Pulse interval (mode)", "Variation (second moment)"])
  fig = pp.gcf()
  fig.set_size_inches(16,12)
  pp.savefig("{0}/depID{1:d}_site{2:.0f}_interval.png".format(plot_dir,deploymentID,siteID))
  pp.clf()


