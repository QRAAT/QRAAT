# continuous_covariance.py - Python encapsulation for .cov files. This file is part 
# of QRAAT, an automated animal tracking system based on GNU Radio. 
#
# Copyright (C) 2014 Todd Borrowman
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

import numpy as np
import struct, re

tag_regex = re.compile("([^/]*)_[0-9]*\.cov$")

header_fmt = "iiffi"
header_len = struct.calcsize(header_fmt)

def header_read(filename):
  with open(filename) as cov_file:
    read_fmt = "qi" + header_fmt
    read_len = struct.calcsize(read_fmt)
    header_str = cov_file.read(read_len)

  cov_header = struct.unpack(read_fmt, header_str)
  return (cov_header, read_len)

def header_create(num_ch, num_block_size, rate, center_freq, num_samples):
  cc_header = struct.pack(header_fmt, 
          int(num_ch),                       #number of channels
          int(num_block_size),                  #number of floats per sample
          float(rate),      #sampling rate
          float(center_freq),                #RF center frequency
          int(num_samples))                      #length of measurement in samples
  return (cc_header, header_len)


class continuous_covariance:

  def __init__(self, filename = None):

    if filename:
      m = tag_regex.search(filename)
      if m:
        self.tag_name = m.groups()[0]
        (header_data, read_len) = header_read(filename)
        self.unix_time = long(header_data[0]) + int(header_data[1])*0.000001#may truncate fractions of seconds
        self.num_ch = int(header_data[2])
        self.block_size = int(header_data[3])
        self.rate = float(header_data[4])
        self.center_freq = float(header_data[5])
        self.num_samples = int(header_data[6])
        with open(filename) as cov_file:
          cov_file.seek(read_len)
          self.raw_data = np.fromfile(cov_file,dtype=np.float32)
        self.cc_data = np.zeros((self.num_ch, self.num_ch, self.raw_data.shape[0]//self.block_size), dtype=np.complex)
        b_count = 0
        for r_count in range(self.num_ch):
          self.cc_data[r_count, r_count, :] = self.raw_data[b_count::self.block_size]
          b_count += 1
          for c_count in range(r_count + 1, self.num_ch):
            self.cc_data[r_count, c_count, :] = self.raw_data[b_count::self.block_size] + np.complex(0,1)*self.raw_data[b_count+1::self.block_size]
            self.cc_data[c_count, r_count, :] = self.cc_data[r_count, c_count, :].conj()
            b_count += 2
      else:
        raise IOError("Couldn't read tagname from file or not an cov file")


    else:
      self.unix_time = 0.0
      self.num_ch = 0
      self.block_size = 0
      self.rate = 0.0
      self.center_freq = 0.0
      self.num_samples = 0
      self.raw_data = np.zeros((0,))
      self.cc_data = np.zeros((0,))
      self.eigenvectors = np.zeros((0,))
      self.eigenvalues = np.zeros((0,))
      
  def eig(self):
    self.eigenvectors = np.zeros((self.cc_data.shape[2],self.num_ch),dtype=np.complex)
    self.eigenvalues = np.zeros((self.cc_data.shape[2],self.num_ch),dtype=float)
    for j in range(self.cc_data.shape[2]):
      (values, vectors) = np.linalg.eig(self.cc_data[:,:,j])
      index = np.argmax(np.abs(values))
      self.eigenvectors[j,:] = vectors[:,index]
      self.eigenvalues[j,:] = np.abs(values)

  def write_to_db(self, db_con, siteID = None):

    if self.num_ch == 4:
      cur = db_con.cursor()
      for j in range(self.eigenvectors.shape[0]):
        temp_time = self.unix_time + j/self.rate
        edsp = np.argmax(self.eigenvalues[j,:])
        if edsp == 0:
          ec = 0
          edsnr = 0
        else:
          total_sp = np.sum(self.eigenvalues[j,:])
          ec = edsp / total_sp
          edsnr = edsp / (total_sp - edsp)
        #TODO change table name in two places
        if siteID:
          cur.execute("INSERT INTO todd_test_est (deploymentID, siteID, timestamp, center, edsp, ed1r, ed1i, ed2r, ed2i, ed3r, ed3i, ed4r, ed4i, ec, edsnr) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);", [self.tag_name, siteID, temp_time, self.center_freq, edsp, self.eigenvectors[j,0].real, self.eigenvectors[j,0].imag, self.eigenvectors[j,1].real, self.eigenvectors[j,1].imag, self.eigenvectors[j,2].real, self.eigenvectors[j,2].imag, self.eigenvectors[j,3].real, self.eigenvectors[j,3].imag, ec, edsnr])
        else:
          cur.execute("INSERT INTO todd_test_est (deploymentID, timestamp, center, edsp, ed1r, ed1i, ed2r, ed2i, ed3r, ed3i, ed4r, ed4i, ec, edsnr) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);", [self.tag_name, temp_time, self.center_freq, edsp, self.eigenvectors[j,0].real, self.eigenvectors[j,0].imag, self.eigenvectors[j,1].real, self.eigenvectors[j,1].imag, self.eigenvectors[j,2].real, self.eigenvectors[j,2].imag, self.eigenvectors[j,3].real, self.eigenvectors[j,3].imag, ec, edsnr])
