# est_data.py
# Structure for holding processed .det files. Output
# formats: .csv and .est. This file is part of QRAAT, 
# an automated animal tracking system based on GNU Radio. 
#
# Copyright (C) 2013 Todd Borrowman
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

import det_file
import os,time,errno
import numpy as np
import struct

#class to contain data lists for the det info in numpy arrays
class data_arrays():

    def __init__(self, num_channels, size = 0):

        self.num_channels = num_channels
        self.num_records = size
        self.tag_number = np.ones((size,), np.int)*-1
        self.epoch_time = np.empty((size,))
        self.center_freq = np.empty((size,))
        self.e_sig = np.empty((size, num_channels), np.complex)
        self.e_pwr = np.empty((size,))
        self.confidence = np.empty((size,))
        self.f_sig = np.empty((size, num_channels), np.complex)
        self.f_pwr = np.empty((size,))
        self.f_bw3 = np.empty((size,))
        self.f_bw10 = np.empty((size,))
        self.freq = np.empty((size,))
        self.n_cov = np.empty((size, num_channels, num_channels), np.complex)

    def append(self, data):

        self.num_records += data.num_records
        self.tag_number = np.hstack((self.tag_number, data.tag_number))
        self.epoch_time = np.hstack((self.epoch_time, data.epoch_time))
        self.center_freq = np.hstack((self.center_freq, data.center_freq))
        self.e_sig = np.vstack((self.e_sig, data.e_sig))
        self.e_pwr = np.hstack((self.e_pwr, data.e_pwr))
        self.confidence = np.hstack((self.confidence, data.confidence))
        self.f_sig = np.vstack((self.f_sig, data.f_sig))
        self.f_pwr = np.hstack((self.f_pwr, data.f_pwr))
        self.f_bw3 = np.hstack((self.f_bw3, data.f_bw3))
        self.f_bw10 = np.hstack((self.f_bw10, data.f_bw10))
        self.freq = np.hstack((self.freq, data.freq))
        self.n_cov = np.vstack((self.n_cov, data.n_cov))

    def filter_by_tag_number(self, number):

        tag_filter = self.tag_number == number
        new_data = self.filter_by_bool(tag_filter)
        return new_data

    def filter_by_bool(self, tag_filter):
        new_data = data_arrays(self.num_channels,np.sum(tag_filter))
        new_data.tag_number = self.tag_number[tag_filter]
        new_data.epoch_time = self.epoch_time[tag_filter]
        new_data.center_freq = self.center_freq[tag_filter]
        new_data.e_sig = self.e_sig[tag_filter,:]
        new_data.e_pwr = self.e_pwr[tag_filter]
        new_data.confidence = self.confidence[tag_filter]
        new_data.f_sig = self.f_sig[tag_filter,:]
        new_data.f_pwr = self.f_pwr[tag_filter]
        new_data.f_bw3 = self.f_bw3[tag_filter]
        new_data.f_bw10 = self.f_bw10[tag_filter]
        new_data.freq = self.freq[tag_filter]
        new_data.n_cov = self.n_cov[tag_filter,:,:]
        return new_data

    def add_det(self, det, tag_index, index):
        if index >= self.num_records:
            raise IndexError('Index: {0} exceeded number of records: {1}'.format(index, self.num_records))
        det.eig()
        det.f_signal()
        det.noise_cov()
        self.tag_number[index] = tag_index
        self.epoch_time[index] = det.time
        self.center_freq[index] = det.center_freq
        self.e_sig[index,:] = det.e_sig.transpose()
        self.e_pwr[index] = det.e_pwr
        self.confidence[index] = det.e_conf
        self.f_sig[index,:] = det.f_sig.transpose()
        self.f_pwr[index] = det.f_pwr
        self.f_bw3[index] = det.f_bandwidth3
        self.f_bw10[index] = det.f_bandwidth10
        self.freq[index] = det.freq
        self.n_cov[index,:,:] = det.n_cov

    def filter_non_filled(self):
        tag_filter = ((self.tag_number == -1) == False)
        return self.filter_by_bool(tag_filter)

    def filter_by_bw10(self, threshold = 1000):
        tag_filter = self.f_bw10 < threshold
        return self.filter_by_bool(tag_filter)


#est file class
class est_data():

    def __init__(self, filename = '', num_channels = 4):
        
        self.tag_names = []
        self.num_tags = 0
        self.num_channels = num_channels
        self.data = data_arrays(self.num_channels, 0)
        if not filename == '':
            self.read_est(filename)


    #writes an .est file for each tag
    def write_est(self,dirname = './'):

        if not dirname[-1] == '/':
            dirname += '/'
        try:
            os.makedirs(dirname)
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(dirname):
                pass
            else: raise
        for tag_index, tag_name in enumerate(self.tag_names):
            filtered_data = self.data.filter_by_tag_number(tag_index)
            #min_time = np.min(filtered_data.epoch_time)
            #min_time_str = time.strftime("%Y%m%d%H%M%S",time.gmtime(min_time))
            #max_time = np.max(filtered_data.epoch_time)
            #max_time_str = time.strftime("%Y%m%d%H%M%S",time.gmtime(max_time))
            #est_filename = tag_name + '-' + min_time_str + '-' + max_time_str + '.est'
            est_filename = tag_name + '.est'
            stat_filename = tag_name + '.stat'

            with open(dirname + est_filename,'w') as estfile:
                estfile.write(struct.pack('i',filtered_data.num_records))
                for index in range(filtered_data.num_records):
                    #estfile.write("det ")
                    estfile.write(struct.pack('i',len(tag_name)))
                    estfile.write(tag_name)
                    estfile.write(struct.pack('i', filtered_data.epoch_time[index]//1))
                    estfile.write(struct.pack('i', (filtered_data.epoch_time[index]%1)*1000000))
                    estfile.write(struct.pack('f',filtered_data.center_freq[index]))
                    estfile.write(struct.pack('i',self.num_channels))
                    for sig in filtered_data.e_sig[index, :]:
                        estfile.write(struct.pack('f',sig.real))
                        estfile.write(struct.pack('f',sig.imag))
                    #print tag_item.e_pwr"][index]
                    estfile.write(struct.pack('f',filtered_data.e_pwr[index]))
                    estfile.write(struct.pack('f',filtered_data.confidence[index]))
                    estfile.write(struct.pack('i',self.num_channels))
                    for sig in filtered_data.f_sig[index,:]:
                        estfile.write(struct.pack('f',sig.real))
                        estfile.write(struct.pack('f',sig.imag))
                    estfile.write(struct.pack('f',filtered_data.f_pwr[index]))
                    estfile.write(struct.pack('f',filtered_data.f_bw3[index]))
                    estfile.write(struct.pack('f',filtered_data.f_bw10[index]))
                    estfile.write(struct.pack('i',int(filtered_data.freq[index])))
                    estfile.write(struct.pack('i',self.num_channels))
                    for sig in filtered_data.n_cov[index,:,:].flat:
                        estfile.write(struct.pack('f',sig.real))
                        estfile.write(struct.pack('f',sig.imag))

            with open(dirname + stat_filename, 'w') as stat_file:
                stat_file.write('Name: {0}\n'.format(tag_name))
                stat_file.write('Number of files: {0}\n'.format(filtered_data.num_records))
                good_data = filtered_data.filter_by_bw10()
                stat_file.write('Number of good pulses: {0}\n'.format(good_data.num_records))
                if good_data.num_records > 0:
                    max_time = np.max(good_data.epoch_time)
                    max_time_str = time.strftime("%Y-%m-%d %H:%M:%S",time.gmtime(max_time))
                    stat_file.write('Last time seen: {0}\n'.format(max_time_str))
                    stat_file.write('Avg. Frequency: {0}\n'.format(np.mean(good_data.freq)))
                    stat_file.write('Avg. Signal Level: {0} dB\n'.format(10*np.log10(np.mean(good_data.f_pwr))))
                    stat_file.write('Std. Dev. Signal Level: {0}\n'.format(np.std(good_data.f_pwr)))

    #writes .csv file for each tag
    def write_csv(self, dirname = './'):

        if not dirname[-1] == '/':
            dirname += '/'
        try:
            os.makedirs(dirname)
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(dirname):
                pass
            else: raise
        for tag_index, tag_name in enumerate(self.tag_names):
            filtered_data = self.data.filter_by_tag_number(tag_index)
            csv_filename = tag_name + '.csv'
            with open(dirname + csv_filename,'w') as csvfile:
                label_str = "Date/Time (UTC), Unix Timestamp (s), Tag Frequency (Hz), Band Center Frequency (Hz), Fourier Decomposition Signal Power, "
                for ch_iter in range(self.num_channels):
                    label_str += "Fourier Decomposition Signal on Channel {0:d} - real part, Fourier Decomposition Signal on Channel {0:d} - imaginary part, ".format(ch_iter + 1)
                label_str += "3dB Bandwidth, 10dB Bandwidth, Eigenvalue Decomposition Signal Power, "
                for ch_iter in range(self.num_channels):
                    label_str += "Eigenvalue Decomposition Signal on Channel {0:d} - real part, Eigenvalue Decomposition Signal on Channel {0:d} - imaginary part, ".format(ch_iter + 1)
                label_str += "Eigenvalue Confidence, Total Noise Power, "
                for ch_iter1 in range(self.num_channels):
                    for ch_iter2 in range(self.num_channels):
                        label_str += "Noise Covariance {0:d}{1:d} - real part, Noise Covariance {0:d}{1:d} - imaginary part, ".format(ch_iter1 + 1, ch_iter2 + 1)
                label_str += "Fourier Decomposition SNR (dB), Eigenvalue Decomposition SNR (dB)\n"
                csvfile.write(label_str)
                for index in range(filtered_data.num_records):
                    line_str = time.strftime("%Y-%m-%d %H:%M:%S",time.gmtime(filtered_data.epoch_time[index]))
                    line_str += ', {0:.6f}'.format(filtered_data.epoch_time[index])
                    line_str += ', {0:.0f}'.format(filtered_data.freq[index])
                    line_str += ', {0:.0f}'.format(filtered_data.center_freq[index])
                    f = filtered_data.f_pwr[index]
                    line_str += ', {0:e}'.format(f)
                    for ch_iter in range(self.num_channels):
                        line_str += ', {0:e}, {1:e}'.format(filtered_data.f_sig[index,ch_iter].real,filtered_data.f_sig[index,ch_iter].imag)
                    line_str += ', {0:.0f}'.format(filtered_data.f_bw3[index])
                    line_str += ', {0:.0f}'.format(filtered_data.f_bw10[index])
                    e = filtered_data.e_pwr[index]
                    line_str += ', {0:e}'.format(e)
                    for ch_iter in range(self.num_channels):
                        line_str += ', {0:e}, {1:e}'.format(filtered_data.e_sig[index,ch_iter].real,filtered_data.e_sig[index,ch_iter].imag)
                    line_str += ', {0:0.5f}'.format(filtered_data.confidence[index])
                    n = np.trace(filtered_data.n_cov[index,:,:]).real
                    line_str += ', {0:e}'.format(n)
                    for ch_iter1 in range(self.num_channels):
                        for ch_iter2 in range(self.num_channels):
                            line_str += ', {0:e}, {1:e}'.format(filtered_data.n_cov[index,ch_iter1,ch_iter2].real, filtered_data.n_cov[index,ch_iter1,ch_iter2].imag)
                    line_str += ', {0:.3f}'.format(10*np.log10(f/n))
                    line_str += ', {0:.3f}\n'.format(10*np.log10(e/n))
                    csvfile.write(line_str)



    #reads data from a est file
    def read_est(self, est_filename):

        if est_filename[-4:] == ".est":
            with open(est_filename) as estfile:
                (num_entries,) = struct.unpack('i', estfile.read(4))
                #build empty arrays
                temp_data = data_arrays(self.num_channels, num_entries)
                #fill arrays
                for j in range(num_entries):
                    (tag_name_len,) = struct.unpack('i',estfile.read(4))
                    tag_name = estfile.read(tag_name_len)
                    try:
                        tag_index  = self.tag_names.index(tag_name)
                    except ValueError:
                        self.tag_names.append(tag_name)
                        tag_index = self.num_tags
                        self.num_tags += 1
                    temp_data.tag_number[j] = tag_index

                    (time_sec, time_usec) = struct.unpack('ii', estfile.read(8))
                    temp_data.epoch_time[j] = time_sec + time_usec/1000000.0

                    (temp_data.center_freq[j],) = struct.unpack('f', estfile.read(4))

                    (e_sig_len,) = struct.unpack('i', estfile.read(4))
                    if not e_sig_len == self.num_channels:
                        raise ValueError('e_sig_len doesn\'t equal num_channels')
                    for k in range(e_sig_len):
                        (real_part, imaginary_part) = struct.unpack('ff',estfile.read(8))
                        temp_data.e_sig[j,k] = complex(real_part,imaginary_part)

                    (temp_data.e_pwr[j],) = struct.unpack('f', estfile.read(4))

                    (temp_data.confidence[j],) = struct.unpack('f',estfile.read(4))

                    (f_sig_len,) = struct.unpack('i', estfile.read(4))
                    if not f_sig_len == self.num_channels:
                        raise ValueError('f_sig_len doesn\'t equal num_channels')
                    for k in range(f_sig_len):
                        (real_part, imaginary_part) = struct.unpack('ff',estfile.read(8))
                        temp_data.f_sig[j,k] = complex(real_part,imaginary_part)

                    (temp_data.f_pwr[j],) = struct.unpack('f', estfile.read(4))

                    (temp_data.f_bw3[j],) = struct.unpack('f',estfile.read(4))

                    (temp_data.f_bw10[j],) = struct.unpack('f',estfile.read(4))

                    (temp_data.freq[j],) = struct.unpack('i',estfile.read(4))

                    (n_cov_len,) = struct.unpack('i', estfile.read(4))
                    if not n_cov_len == self.num_channels:
                        raise ValueError('n_cov_len doesn\'t equal num_channels')
                    for k in range(n_cov_len):
                        for m in range(n_cov_len):
                            (real_part, imaginary_part) = struct.unpack('ff',estfile.read(8))
                            temp_data.n_cov[j,k,m] = complex(real_part,imaginary_part)

                self.data.append(temp_data)
        else:
            raise IOError, "{0} is not an .est file".format(est_filename)

    #reads in all .det files in the given directory
    def read_dir(self,dirname):

        dir_list = os.listdir(dirname)
        print "{0} files found at {1}".format(len(dir_list), dirname)
        if len(dir_list) > 0:
            dir_list.sort()
            if not dirname[-1] == '/':
                dirname += '/'
            new_data = data_arrays(self.num_channels, len(dir_list))
            count = 0
            for fstr in dir_list:
                if fstr[-4:] == '.det':
                    det = det_file.det_file(dirname + fstr)
                    if not det.null_file:
                        tag_name = det.tag_name
                        try:
                            tag_index  = self.tag_names.index(tag_name)
                        except ValueError:
                            self.tag_names.append(tag_name)
                            tag_index = self.num_tags
                            self.num_tags += 1
                        new_data.add_det(det, tag_index, count)
                        count += 1
            
            self.data.append(new_data.filter_non_filled())

    #adds given det_file object
    def add_det(self, det):

        if not det.null_file:
            det.eig()
            det.f_signal()
            det.noise_cov()
            new_data = data_arrays(self.num_channels, 1)
            tag_name = det.tag_name
            try:
                tag_index  = self.tag_names.index(tag_name)
            except ValueError:
                self.tag_names.append(tag_name)
                tag_index = self.num_tags
                self.num_tags += 1
            new_data.add_det(det, tag_index, 0)
            self.data.append(new_data)


#main routine for execution with cmdline options
#est_dict.py det_directory_name est_directory_name
#used for testing, quick conversion of directories
if __name__=="__main__":
    import sys
    if len(sys.argv) > 2:
        det_dirname = sys.argv[1]
        est_dirname = sys.argv[2]
    #if det_dirname and est_dirname:
        est = est_data()
        est.read_dir(det_dirname)
        est.write_est(est_dirname)
