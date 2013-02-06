# est_dict.py
# Dictionaryt structure for holding processed .det files. Output
# formats: .csv and .est. (deprecated? TODO) This file is part of QRAAT, 
# an automated animal tracking system based on GNU Radio. 
#
# Copyright (C) 2012 Todd Borrowman
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
import os,time
import numpy as np
import struct

#class to contain data lists for a particular tag
class est_tag:

    def __init__(self, add_tuple):
        
        (epoch_time, center_freq, e_sig, e_pwr, confidence, f_sig, f_pwr, f_bw3, f_bw10, freq, n_cov) = add_tuple
        self.epoch_time = [epoch_time]
        self.center_freq = [center_freq]
        #self.e_sig = e_sig.transpose()
        self.e_sig = [e_sig.transpose()[0,:]]
        self.e_pwr = [e_pwr]
        self.confidence = [confidence]
        #self.f_sig = f_sig.transpose()
        self.f_sig = [f_sig.transpose()[0,:]]
        self.f_pwr = [f_pwr]
        self.f_bw3 = [f_bw3]
        self.f_bw10 = [f_bw10]
        self.freq = [freq]
        self.n_cov = [n_cov]
        self.num = 1

    def add(self,add_tuple):

        (epoch_time, center_freq, e_sig, e_pwr, confidence, f_sig, f_pwr, f_bw3, f_bw10, freq, n_cov) = add_tuple
        self.epoch_time.append(epoch_time)
        self.center_freq.append(center_freq)
        #self.e_sig = np.vstack((self.e_sig,e_sig.transpose()))
        self.e_sig.append(e_sig.transpose()[0,:])
        self.e_pwr.append(e_pwr)
        self.confidence.append(confidence)
        #self.f_sig = np.vstack((self.f_sig,f_sig.transpose()))
        self.f_sig.append(f_sig.transpose()[0,:])
        self.f_pwr.append(f_pwr)
        self.f_bw3.append(f_bw3)
        self.f_bw10.append(f_bw10)
        self.freq.append(freq)
        self.n_cov.append(n_cov)
        self.num += 1

#dictionary class with entries for each tag
class est_dict(dict):

    def __init__(self, filename = ''):
        dict.__init__(self)
        if not filename == '':
            self.read_est(filename)

    #writes an .est file for each tag in dictionary
    def write_est(self,dirname = './'):

        if not dirname[-1] == '/':
            dirname += '/'
        for tag_name in self.tags():
            tag_item = self[tag_name]
            min_time = np.min(tag_item.epoch_time)
            min_time_str = time.strftime("%Y%m%d%H%M%S",time.gmtime(min_time))
            max_time = np.max(tag_item.epoch_time)
            max_time_str = time.strftime("%Y%m%d%H%M%S",time.gmtime(max_time))
            est_filename = tag_name + '-' + min_time_str + '-' + max_time_str + '.est'

            with open(dirname + est_filename,'w') as estfile:
                estfile.write(struct.pack('i',tag_item.num))
                for index in range(tag_item.num):
                    #estfile.write("det ")
                    estfile.write(struct.pack('i',len(tag_name)))
                    estfile.write(tag_name)
                    estfile.write(struct.pack('i', tag_item.epoch_time[index]//1))
                    estfile.write(struct.pack('i', (tag_item.epoch_time[index]%1)*1000000))
                    estfile.write(struct.pack('f',tag_item.center_freq[index]))
                    estfile.write(struct.pack('i',len(tag_item.e_sig[index])))
                    for sig in tag_item.e_sig[index]:
                        estfile.write(struct.pack('f',sig.real))
                        estfile.write(struct.pack('f',sig.imag))
                    #print tag_item.e_pwr"][index]
                    estfile.write(struct.pack('f',tag_item.e_pwr[index]))
                    estfile.write(struct.pack('f',tag_item.confidence[index]))
                    estfile.write(struct.pack('i',len(tag_item.f_sig[index])))
                    for sig in tag_item.f_sig[index]:
                        estfile.write(struct.pack('f',sig.real))
                        estfile.write(struct.pack('f',sig.imag))
                    estfile.write(struct.pack('f',tag_item.f_pwr[index]))
                    estfile.write(struct.pack('f',tag_item.f_bw3[index]))
                    estfile.write(struct.pack('f',tag_item.f_bw10[index]))
                    estfile.write(struct.pack('i',int(tag_item.freq[index])))
                    estfile.write(struct.pack('i',len(tag_item.n_cov[index])))
                    for sig in tag_item.n_cov[index].flat:
                        estfile.write(struct.pack('f',sig.real))
                        estfile.write(struct.pack('f',sig.imag))

    #writes .csv file for each tag in dictionary
    def write_csv(self, dirname = './'):
        import datetime
        if not dirname[-1] == '/':
            dirname += '/'
        for tag_name in self.tags():
            tag_item = self[tag_name]
            min_time = np.min(tag_item.epoch_time)
            min_time_str = time.strftime("%Y%m%d%H%M%S",time.gmtime(min_time))
            max_time = np.max(tag_item.epoch_time)
            max_time_str = time.strftime("%Y%m%d%H%M%S",time.gmtime(max_time))
            csv_filename = tag_name + '-' + min_time_str + '-' + max_time_str + '.csv'
            with open(dirname + csv_filename,'w') as csvfile:
                label_str = "Date/Time (UTC), Tag Frequency (Hz), Band Center Frequency (Hz), Signal Power, Noise Power, SNR (dB)\n"
                csvfile.write(label_str)
                for index in range(tag_item.num):
                    line_str = str(datetime.datetime.utcfromtimestamp(tag_item.epoch_time[index]))
                    line_str += ', {0:.0f}'.format(tag_item.freq[index])
                    line_str += ', {0:.0f}'.format(tag_item.center_freq[index])
                    e = tag_item.e_pwr[index]
                    line_str += ', {0:e}'.format(e)
                    sig = tag_item.e_sig[index][:,np.newaxis]
                    n = np.dot(sig.conj().transpose(),np.dot(tag_item.n_cov[index],sig))[0,0].real
                    line_str += ', {0:e}'.format(n)
                    line_str += ', {0:.3f}\n'.format(10*np.log10(e/n))
                    csvfile.write(line_str)

    #reads data from a est file into the dictionary
    def read_est(self, est_filename):
        if est_filename[-4:] == ".est":
            with open(est_filename) as estfile:
                (num,) = struct.unpack('i', estfile.read(4))
                for j in range(num):
                    (tag_name_len,) = struct.unpack('i',estfile.read(4))
                    tag_name = estfile.read(tag_name_len)
                    (time_sec, time_usec) = struct.unpack('ii', estfile.read(8))
                    epoch_time = time_sec + time_usec/1000000.0
                    (center_freq,) = struct.unpack('f', estfile.read(4))
                    (e_sig_len,) = struct.unpack('i', estfile.read(4))
                    e_sig = []
                    for k in range(e_sig_len):
                        (real_part, imaginary_part) = struct.unpack('ff',estfile.read(8))
                        e_sig.append([complex(real_part,imaginary_part)])
                    e_sig_array = np.array(e_sig)
                    e_pwr = struct.unpack('f', estfile.read(4))[0]
                    (confidence,) = struct.unpack('f',estfile.read(4))
                    (f_sig_len,) = struct.unpack('i', estfile.read(4))
                    f_sig = []
                    for k in range(f_sig_len):
                        (real_part, imaginary_part) = struct.unpack('ff',estfile.read(8))
                        f_sig.append([complex(real_part,imaginary_part)])
                    f_sig_array = np.array(f_sig)
                    f_pwr = struct.unpack('f', estfile.read(4))[0]
                    (f_bw3,) = struct.unpack('f',estfile.read(4))
                    (f_bw10,) = struct.unpack('f',estfile.read(4))
                    (freq,) = struct.unpack('i',estfile.read(4))
                    (n_cov_len,) = struct.unpack('i', estfile.read(4))
                    n_cov = []
                    for k in range(n_cov_len*n_cov_len):
                        (real_part, imaginary_part) = struct.unpack('ff',estfile.read(8))
                        n_cov.append([complex(real_part,imaginary_part)])
                    n_cov_array = np.array(n_cov).reshape((n_cov_len,n_cov_len))
                    add_tuple = (epoch_time, center_freq, e_sig_array, e_pwr, confidence,
                                 f_sig_array, f_pwr, f_bw3, f_bw10, freq, n_cov_array)
                    self._add(tag_name, add_tuple)
        else:
            raise IOError, "{0} is not an .est file".format(est_filename)

    #reads in all .det files in the given directory
    def read_dir(self,dirname):

        dir_list = os.listdir(dirname)
        dir_list.sort()
        if not dirname[-1] == '/':
            dirname += '/'
        for fstr in dir_list:
            if fstr[-4:] == '.det':
                det = det_file.det_file(dirname + fstr)
                if not det.null_file:
                    det.eig()
                    self.add_det(det)

    #adds given det_file object to dictionary
    def add_det(self, det):
        det.eig()
        det.f_signal()
        det.noise_cov()
        add_tuple = (det.time,
                det.center_freq,
                det.e_sig,
                det.e_pwr,
                det.e_conf,
                det.f_sig,
                det.f_pwr,
                det.f_bandwidth3,
                det.f_bandwidth10,
                det.freq,
                det.n_cov)
        self._add(det.tag_name, add_tuple)

    #private add function called by various read functions
    def _add(self, tag_name, add_tuple):

        if tag_name in self:
            self[tag_name].add(add_tuple)
        else:
            self[tag_name] = est_tag(add_tuple)

    #returns list of tags in dictionary
    def tags(self):
        return self.keys()

#main routine for execution with cmdline options
#est_dict.py det_directory_name est_directory_name
#used for testing, quick conversion of directories
if __name__=="__main__":
    import sys
    if len(sys.argv) > 2:
        det_dirname = sys.argv[1]
        est_dirname = sys.argv[2]
    #if det_dirname and est_dirname:
        est = est_dict()
        est.read_dir(det_dirname)
        est.write_est(est_dirname)
