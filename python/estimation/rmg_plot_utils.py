import antenna_pattern as ap
import numpy as np
import matplotlib.pyplot as pp
import matplotlib.dates as md
import datetime as dt
import pytz
import rmg_utils

def abs_antenna_pattern(pat_filename, title = ""):

    pat = ap.antenna_pattern(pat_filename)
    for j in range(pat.num_ch):
        pp.plot(pat.angles, np.abs(pat.pat[:,j]))
    pp.xlabel("Bearing (Degrees)")
    pp.ylabel("Amplitude")
    pp.ylim([0,1.0])
    if title == "":
        title = pat_filename
    pp.title(title)
    pp.show()

def angle_antenna_pattern(pat_filename, title = ""):

    pat = ap.antenna_pattern(pat_filename)
    for j in range(pat.num_ch):
        pp.plot(pat.angles, np.angle(pat.pat[:,j]))
    pp.xlabel("Bearing (Degrees)")
    pp.ylabel("Phase (Radians)")
    pp.ylim([-np.pi, np.pi])
    if title == "":
        title = pat_filename
    pp.title(title)
    pp.show()

def gps_position(gpx_filename, rmg_loc, title = ""):

    gps = rmg_utils.gps_data(gpx_filename, rmg_loc)
    pp.plot(np.hstack(gps.easting), np.hstack(gps.northing))
    pp.xlabel("Easting (Meters)")
    pp.ylabel("Northing (Meters)")
    if title == "":
        title = gpx_filename
    pp.title(title)
    pp.show()

def gps_bearings(gpx_filename, rmg_loc, title = "", tz = pytz.timezone('US/Pacific')):
    
    gps = rmg_utils.gps_data(gpx_filename, rmg_loc)
    times = np.hstack(gps.time)
    gps_dates=[dt.datetime.fromtimestamp(ts, tz) for ts in times]
    gps_datenums=md.date2num(gps_dates)
    pp.plot_date(gps_datenums,np.hstack(gps.bearing),'-',tz)
    pp.xlabel("Time (GPS localtime)")
    pp.ylabel("Bearing (Degrees)")
    if title == "":
        title = gpx_filename
    pp.title(title)
    pp.show()

def rmg_bearing_estimation_f(est_directory, pat_filename, title = "", tz = pytz.timezone('US/Pacific')):

    rmg = rmg_utils.rmg_data(est_directory)
    rmg.bw_filter()
    bearings = rmg_utils.estimate_f(rmg, pat_filename)
    rmg_dates=[dt.datetime.fromtimestamp(ts,tz) for ts in rmg.time]
    rmg_datenums=md.date2num(rmg_dates)
    pp.plot_date(rmg_datenums,bearings,'.',tz)
    pp.xlabel("Time (GPS localtime)")
    pp.ylabel("Bearing (Degrees)")
    if title == "":
        title = est_directory + '\n' + pat_filename
    pp.title(title)
    pp.show()

def rmg_bearing_estimation_e(est_directory, pat_filename, title = "", tz = pytz.timezone('US/Pacific')):

    rmg = rmg_utils.rmg_data(est_directory)
    rmg.bw_filter()
    bearings = rmg_utils.estimate_e(rmg, pat_filename)
    rmg_dates=[dt.datetime.fromtimestamp(ts,tz) for ts in rmg.time]
    rmg_datenums=md.date2num(rmg_dates)
    pp.plot_date(rmg_datenums,bearings,'.',tz)
    pp.xlabel("Time (GPS localtime)")
    pp.ylabel("Bearing (Degrees)")
    if title == "":
        title = est_directory + '\n' + pat_filename
    pp.title(title)
    pp.show()

