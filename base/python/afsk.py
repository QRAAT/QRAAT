# afsk.py - Python encapsulation for .afsk files. This file is part 
# of QRAAT, an automated animal tracking system based on GNU Radio. 
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

import numpy as np
import struct

header_fmt = "ffff"
header_len = struct.calcsize(header_fmt)

def header_read(filename):
  with open(filename) as afsk_file:
    read_fmt = "qi" + header_fmt
    read_len = struct.calcsize(read_fmt)
    header_str = afsk_file.read(read_len)

  afsk_header = struct.unpack(read_fmt, header_str)
  return (afsk_header, read_len)

def header_create(rate, center_freq, mark_freq, space_freq):
  afsk_header = struct.pack(header_fmt,
        float(afsk_actual_output_rate),    #sampling rate (Hz)
        float(center_freq),                #RF center frequency (Hz)
        float(mark_freq),                  #mark frequency (Hz)
        float(space_freq))                 #space frequency (Hz)

  return (afsk_header, header_len)

class decode_string:

  def __init__(self, start_sample, end_sample, bit_vector):
    self.start_sample = start_sample
    self.end_sample = end_sample
    self.binary = self.binary_conversion(bit_vector)
    (self.string, self.error) = self.string_conversion(bit_vector)

  def binary_conversion(self, bit_vector):
    index = 0
    byte_index = 0
    temp_byte = 0
    integer_list = []
    while index < len(bit_vector):
      temp_byte += 2**byte_index*bit_vector[index]
      byte_index += 1
      if byte_index == 8:
        integer_list.append(temp_byte)
        byte_index = 0
        temp_byte = 0
      index += 1
    if not byte_index == 0:
      integer_list.append(temp_byte)
    return bytearray(integer_list)

  def string_conversion(self, bit_vector):
    error_flag = False
    data_str = ''
    num_char = len(bit_vector)//10
    for j in range(num_char):
      if (bit_vector[j*10] == 0) and (bit_vector[j*10+9] == 1):
        char_val = 0;
        for k in range(8):
          char_val += (2**k) * bit_vector[j*10+k+1];
        data_str += chr(char_val)
      else:
        error_flag = True;
        break

    return (data_str, error_flag)


class afsk:

  def __init__(self, filename=None):

    if filename:
      (header_data, read_len) = header_read(filename)
      self.unix_time = long(header_data[0]) + int(header_data[1])*0.000001#may truncate fractions of seconds
      self.rate = float(header_data[2])
      self.center_freq = float(header_data[3])
      self.mark_freq = float(header_data[4])
      self.space_freq = float(header_data[5])
      with open(filename) as afsk_file:
        afsk_file.seek(read_len)
        data = np.fromfile(afsk_file,dtype=np.float32)
      self.mark_data = data[::2]
      self.space_data = data[1::2]
      #TODO get deploymentID from filename?

    else:
      self.unix_time = 0.0
      self.rate = 0.0
      self.center_freq = 0.0
      self.mark_freq = 0.0
      self.space_freq = 0.0
      self.mark_data = np.zeros((0),dtype=np.float32)
      self.space_data = np.zeros((0),dtype=np.float32)


  def decode(self):

    self.decoded_list = []

    power_threashold = 0.74#TODO determine dynamically
    step_size = 32000/self.rate; #number of samples (at 32k) between measurement windows

    one_single = 145.0/step_size;
    one_len = 103.0/step_size;
    zero_single = 47.0/step_size;
    zero_len = 92.5/step_size;

    data_sum = self.mark_data + self.space_data

    signal_indexes = np.where(data_sum > power_threashold)[0]
    signal_indexes = np.append(signal_indexes,self.mark_data.shape[0])
    diff_indexes = np.hstack((signal_indexes[0], np.diff(signal_indexes)))
    signal_ranges = []
    for j in range(diff_indexes.shape[0]):
      if diff_indexes[j] > 10:
        signal_ranges.append(signal_indexes[j] - diff_indexes[j] +1)
        signal_ranges.append(signal_indexes[j])


    sr = 0;
    while sr < len(signal_ranges)-1:

      if not ( ((signal_ranges[sr+1] - signal_ranges[sr]) > 10*one_single) and np.any(data_sum[signal_ranges[sr]+1:signal_ranges[sr+1]-1] > power_threashold) ):
        sr += 1;
        continue;
     
      m_range = (signal_ranges[sr], signal_ranges[sr+1]);

      b_stream = np.zeros(np.diff(m_range))
      b_stream[self.mark_data[m_range[0]:m_range[1]] > self.space_data[m_range[0]:m_range[1]]] = 1

      one_to_zero = np.where(np.diff(b_stream)==1)[0];
      zero_to_one = np.where(np.diff(b_stream)==-1)[0];

      bit_vector = [];
      for j in range(one_to_zero.shape[0]-1):
        symbol_len = one_to_zero[j] - zero_to_one[j];
        for k in range( int( round( (symbol_len - zero_single) / zero_len) ) + 1):
          bit_vector.append(0)
        symbol_len = zero_to_one[j+1] - one_to_zero[j]
        for k in range( int( round( (symbol_len - one_single) / one_len) ) + 1):
          bit_vector.append(1)

      j += 1
      symbol_len = one_to_zero[j] - zero_to_one[j]
      for k in range( int( round( (symbol_len - zero_single) / zero_len) ) + 1):
        bit_vector.append(0)

      #assume trailing 1s to fill out last word
      num_char = int( np.ceil(len(bit_vector)/10.0) )
      for j in range(num_char*10 - len(bit_vector)):
        bit_vector.append(1)

      self.decoded_list.append(decode_string(m_range[0], m_range[1], bit_vector))
      sr += 2

