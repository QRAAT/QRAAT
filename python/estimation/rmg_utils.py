import numpy as np
import est_dict as ed
import gpx_handler
import antenna_pattern
import struct
import os


def find_site_pos(waypoint_filename, waypoint_name):

    gw = gpx_handler.gpx_waypoints(waypoint_filename)
    rmg_loc_ll = gw.get_waypoint(waypoint_name)
    rmg_loc_utm = gpx_handler.convert_ll_to_utm(rmg_loc_ll)
    return rmg_loc_utm

class gps_data:
  def __init__(self, gpx_filename, rmg_loc_utm = None):

    self.time = []
    self.easting = []
    self.northing = []
    self.dist = []
    self.elevation = []
    self.track_count = 0
    if gpx_filename.__class__ == ''.__class__:
        filenames = [gpx_filename]
    else:
        filenames = []
        filenames.extend(gpx_filename)
    for f in filenames:
        gf = gpx_handler.gpx_track(f)
        gf.read_tracks()
        for j in gf.track_points:
            self.time.append([])
            self.easting.append([])
            self.northing.append([])
            self.elevation.append([])
            for k in j:
                gps_loc_utm = gpx_handler.convert_ll_to_utm(k[1:3])
                self.time[self.track_count].append(k[0])
                self.easting[self.track_count].append(gps_loc_utm[0])
                self.northing[self.track_count].append(gps_loc_utm[1])
                self.elevation[self.track_count].append(k[3])
            self.track_count+=1
    if not rmg_loc_utm is None:
        (self.dist, self.bearing) = self.get_bearing(rmg_loc_utm)

  def get_bearing(self, rmg_loc_utm):

    bearing = []
    dist = []
    for j in range(len(self.easting)):
        bearing.append([])
        dist.append([])
        for k in range(len(self.easting[j])):
            temp = gpx_handler.calc_bearing_utm(rmg_loc_utm,(self.easting[j][k],self.northing[j][k]))
            dist[j].append(temp[0])
            bearing[j].append(temp[1])
    return (dist, bearing)

class rmg_data:
  def __init__(self, est_directory):
    self.time = np.empty((0,))
    self.e_conf = np.empty((0,))
    self.f_sig = np.empty((0,4))
    self.f_pwr = np.empty((0,))
    self.e_sig = np.empty((0,4))
    self.e_pwr = np.empty((0,))
    self.f_bw10 = np.empty((0,))
    self.freq = np.empty((0,))

    est_filelist = os.listdir(est_directory)
    for j in est_filelist:
        if j[-4:] == '.est':
            est = ed.est_dict(est_directory + j)
            cal_tag = est[est.tags()[0]]
            self.time = np.hstack((self.time,cal_tag.epoch_time))
            self.e_conf = np.hstack((self.e_conf,cal_tag.confidence))
            self.f_sig = np.vstack((self.f_sig,cal_tag.f_sig))
            self.f_pwr = np.hstack((self.f_pwr,cal_tag.f_pwr))
            self.e_sig = np.vstack((self.e_sig,cal_tag.e_sig))
            self.e_pwr = np.hstack((self.e_pwr,cal_tag.e_pwr))
            self.f_bw10 = np.hstack((self.f_bw10,cal_tag.f_bw10))
            self.freq = np.hstack((self.freq,cal_tag.freq))

  def bw_filter(self, threashold = 1000):
    true_pulses_filter = self.f_bw10 < threashold
    self.time = self.time[true_pulses_filter]
    self.e_conf = self.e_conf[true_pulses_filter]
    self.f_sig = self.f_sig[true_pulses_filter,:]
    self.f_pwr = self.f_pwr[true_pulses_filter]
    self.e_sig = self.e_sig[true_pulses_filter,:]
    self.e_pwr = self.e_pwr[true_pulses_filter]
    self.f_bw10 = self.f_bw10[true_pulses_filter]
    self.freq = self.freq[true_pulses_filter]


  def gps_filter(self, gps_data, rmg_loc_utm):
    self.bw_filter()
    frmg_time = np.empty((0,))
    fe_conf = np.empty((0,))
    ff_sig = np.empty((0,4))
    ff_pwr = np.empty((0,))
    fe_sig = np.empty((0,4))
    fe_pwr = np.empty((0,))
    ff_bw10 = np.empty((0,))
    ffreq = np.empty((0,))

    frmg_northing = np.empty((0,))
    frmg_easting = np.empty((0,))
    frmg_elevation = np.empty((0,))
    for j in range(len(gps_data.time)):
        left_limit = self.time > gps_data.time[j][0]
        right_limit = self.time < gps_data.time[j][-1]
        valid_dets = left_limit*right_limit
        if valid_dets.any():
            frmg_easting = np.hstack((frmg_easting, np.interp(self.time[valid_dets], gps_data.time[j], gps_data.easting[j])))
            frmg_northing = np.hstack((frmg_northing, np.interp(self.time[valid_dets], gps_data.time[j], gps_data.northing[j])))
            frmg_elevation = np.hstack((frmg_elevation, np.interp(self.time[valid_dets], gps_data.time[j], gps_data.elevation[j])))

            frmg_time = np.hstack((frmg_time,self.time[valid_dets]))
            fe_conf = np.hstack((fe_conf,self.e_conf[valid_dets]))
            ff_sig = np.vstack((ff_sig,self.f_sig[valid_dets]))
            ff_pwr = np.hstack((ff_pwr,self.f_pwr[valid_dets]))
            fe_sig = np.vstack((fe_sig,self.e_sig[valid_dets]))
            fe_pwr = np.hstack((fe_pwr,self.e_pwr[valid_dets]))
            ff_bw10 = np.hstack((ff_bw10,self.f_bw10[valid_dets]))
            ffreq = np.hstack((ffreq,self.freq[valid_dets]))

    deasting = frmg_easting - rmg_loc_utm[0]
    dnorthing = frmg_northing - rmg_loc_utm[1]
    self.bearing = np.arctan2(deasting,dnorthing)*180.0/np.pi
    self.dist = np.sqrt(deasting*deasting + dnorthing*dnorthing)

    self.time = frmg_time
    self.e_conf = fe_conf
    self.f_sig = ff_sig
    self.f_pwr = ff_pwr
    self.e_sig = fe_sig
    self.e_pwr = fe_pwr
    self.f_bw10 = ff_bw10
    self.freq = ffreq
    self.easting = frmg_easting
    self.northing = frmg_northing
    self.elevation = frmg_elevation

  def cal_filter(self, threashold = 50):

    if hasattr(self,'dist'):
        indexes = self.dist > threashold
        self.bearing = self.bearing[indexes]
        self.dist = self.dist[indexes]
        self.time = self.time[indexes]
        self.e_conf = self.e_conf[indexes]
        self.f_sig = self.f_sig[indexes,:]
        self.f_pwr = self.f_pwr[indexes]
        self.e_sig = self.e_sig[indexes,:]
        self.e_pwr = self.e_pwr[indexes]
        self.f_bw10 = self.f_bw10[indexes]
        self.freq = self.freq[indexes]
        self.easting = self.easting[indexes]
        self.northing = self.northing[indexes]
        self.elevation = self.elevation[indexes]
    else:
        print "Need to run \'gps_filter\' before \'cal_filter\'"

class bearing_data:

    def __init__(self, rmg, pat, type_str = 'f'):

        self.angles = pat.angles
        self.num_angles = len(self.angles)
        self.time = rmg.time
        self.num_records = len(self.time)
        self.bearing_prob = np.zeros((self.num_records,self.num_angles))
        self.estimates = np.empty((self.num_records,))
        if type_str == 'f':
            sig = rmg.f_sig
        elif type_str == 'e':
            sig = rmg.e_sig
        else:
            print "Invalid signal type <{0}>, using default <f>".format(type_str)
        for j in range(self.num_records):
            (self.bearing_prob[j,:], self.estimates[j]) = pat.likelihood_estimation(sig[j,:])
        

def generate_pat(signal, bearings, pat_filename, sector_size = 5, ant_phase_center = 0, angles = range(360)):
#function trys to generate a cal at one degree intervals from 0 to 359
    cal_bearings = bearings
    while (cal_bearings < 0).any():
        cal_bearings = cal_bearings + 360*(cal_bearings < 0)
    while (cal_bearings > 360).any():
        cal_bearings = cal_bearings - 360*(cal_bearings > 360)
    #Use antenna 1 as phase center
    norm_f_sig = np.zeros(signal.shape,np.complex)
    for j in range(signal.shape[0]):
        norm_f_sig[j,:] = signal[j,:]*np.exp(np.complex(0,-np.angle(signal[j,ant_phase_center])))

    #average norm_f_sig over sector_size
    mean_pat = np.zeros((len(angles),norm_f_sig.shape[1]),np.complex)
    for j in angles:
      if j - sector_size/2.0 < 0:
        sector_index = (cal_bearings < (j + sector_size/2.0)) + (cal_bearings > (j + 360 - sector_size/2.0))
      elif j + sector_size/2.0 > 360:
        sector_index = (cal_bearings < (j - 360 + sector_size/2.0)) + (cal_bearings > (j - sector_size/2.0))
      else:
        sector_index = (cal_bearings < (j + sector_size/2.0)) * (cal_bearings > (j - sector_size/2.0))
      if sector_index.any():
          mean_pat[j,:] = np.mean(norm_f_sig[sector_index,:],0)

    #normalize result
    nm_pat = np.zeros(mean_pat.shape,np.complex)
    nonzero_indexes = []
    for j in angles:
        temp_sum = np.sum(mean_pat[j,:]*mean_pat[j,:].conj())
        if temp_sum > 0:
            nm_pat[j,:] = mean_pat[j,:] / np.sqrt(temp_sum)
            nonzero_indexes.append(j)
        else:
            nm_pat[j,:] = mean_pat[j,:]

    #write to .pat file
    with open(pat_filename,'w') as pfile:
      pfile.write(struct.pack('i',nm_pat.shape[1]))
      pfile.write(struct.pack('i',len(nonzero_indexes)))
      for j in nonzero_indexes:
        pfile.write(struct.pack('f',j))
        for k in range(nm_pat.shape[1]):
          pfile.write(struct.pack('f',nm_pat[j,k].real))
          pfile.write(struct.pack('f',nm_pat[j,k].imag))

def calibrate_f(gpx_filename, rmg_loc_utm, est_directory, pat_filename):

    gps = gps_data(gpx_filename, rmg_loc_utm)
    rmg = rmg_data(est_directory)
    rmg.gps_filter(gps, rmg_loc_utm)
    rmg.cal_filter()
    generate_pat(rmg.f_sig, rmg.bearing, pat_filename)

def calibrate_e(gpx_filename, rmg_loc_utm, est_directory, pat_filename):

    gps = gps_data(gpx_filename, rmg_loc_utm)
    rmg = rmg_data(est_directory)
    rmg.gps_filter(gps, rmg_loc_utm)
    rmg.cal_filter()
    generate_pat(rmg.e_sig, rmg.bearing, pat_filename)

def estimate_f(rmg, pat_filename):

    rmg.bw_filter()
    pat = antenna_pattern.antenna_pattern(pat_filename)
    estimate = np.empty((0,))
    for sig in rmg.f_sig:
        estimate = np.hstack((estimate,pat.bearing_estimation(sig)))
    return estimate

def estimate_e(rmg, pat_filename):

    rmg.bw_filter()
    pat = antenna_pattern.antenna_pattern(pat_filename)
    estimate = np.empty((0,))
    for sig in rmg.e_sig:
        estimate = np.hstack((estimate,pat.bearing_estimation(sig)))
    return estimate

