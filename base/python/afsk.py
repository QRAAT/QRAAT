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
import struct, re

tag_regex = re.compile("([^/]*)_[0-9]*\.afsk$")

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
        float(rate),    #sampling rate (Hz)
        float(center_freq),                #RF center frequency (Hz)
        float(mark_freq),                  #mark frequency (Hz)
        float(space_freq))                 #space frequency (Hz)

  return (afsk_header, header_len)

class decode_string:

  def __init__(self, start_sample, end_sample, bit_vector):
    self.start_sample = start_sample
    self.end_sample = end_sample
    self.raw_hex_str = self.binary_conversion(bit_vector)
    (self.string, self.error) = self.string_conversion(bit_vector)

  def binary_conversion(self, bit_vector):
    index = 0
    byte_index = 0
    temp_byte = 0
    integer_list = []
    binary_str = ''
    while index < len(bit_vector):
      temp_byte += 2**byte_index*bit_vector[index]
      byte_index += 1
      if byte_index == 8:
        binary_str += '{0:02x}'.format(temp_byte)
        #integer_list.append(temp_byte)
        byte_index = 0
        temp_byte = 0
      index += 1
    if not byte_index == 0:
      #integer_list.append(temp_byte)
      binary_str += '{0:02x}'.format(temp_byte)
    #return bytearray(integer_list)
    return binary_str

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
      m = tag_regex.search(filename)
      if m:
        self.tag_name = m.groups()[0]
        (header_data, read_len) = header_read(filename)
        self.unix_time = long(header_data[0]) + int(header_data[1])*0.000001#may truncate fractions of seconds
        self.rate = float(header_data[2])
        self.center_freq = float(header_data[3])
        self.mark_freq = float(header_data[4])
        self.space_freq = float(header_data[5])
        with open(filename) as afsk_file:
          afsk_file.seek(read_len)
          data = np.fromfile(afsk_file,dtype=np.float32)
        self.audio_data = data
      else:
        raise IOError("Couldn't read tagname from file or not an afsk file")


    else:
      self.unix_time = 0.0
      self.rate = 0.0
      self.center_freq = 0.0
      self.mark_freq = 0.0
      self.space_freq = 0.0
      self.audio_data = np.zeros((0,),dtype=np.float32)


  def decode(self):

    num_space_cycles = 3
    num_mark_cycles = 4
    num_space_samples = self.rate/self.space_freq
    num_mark_samples = self.rate/self.mark_freq
    cycle_threshold = (num_space_samples+num_mark_samples)/2.0

    cycle_counter = 0
    zero_crossings = []
    for j in range(self.audio_data.shape[0]-1):
      if self.audio_data[j] <=0 and self.audio_data[j+1] > 0:
        zero_crossings.append(cycle_counter)
        cycle_counter = 0
      else:
        cycle_counter += 1

    b_stream = (np.array(zero_crossings) < cycle_threshold)*1

    one_to_zero = np.where(np.diff(b_stream)==1)[0];
    zero_to_one = np.where(np.diff(b_stream)==-1)[0];

    min_length = np.min((one_to_zero.shape[0],zero_to_one.shape[0]))

    bit_vector = []

    if (min_length > 0):
      for j in range(min_length-1):
        symbol_len = one_to_zero[j] - zero_to_one[j];
        for k in range( int( round( symbol_len / float(num_space_cycles)))):
          bit_vector.append(0)
        symbol_len = zero_to_one[j+1] - one_to_zero[j]
        for k in range( int( round( symbol_len / float(num_mark_cycles)))):
          bit_vector.append(1)
      symbol_len = one_to_zero[min_length-1] - zero_to_one[min_length-1]
      for k in range( int( round( symbol_len / float(num_space_cycles)))):
        bit_vector.append(0)

    #assume trailing 1s to fill out last word
    num_char = int( np.ceil(len(bit_vector)/10.0) )
    for j in range(num_char*10 - len(bit_vector)):
      bit_vector.append(1)

    self.decoded = decode_string(0, self.audio_data.shape[0], bit_vector)


  def write_to_db(self, db_con, siteID = 'NULL'):
    if not hasattr(self, 'decoded'):
      self.decode()
    cur = db_con.cursor()
    calc_start_time = self.unix_time + self.decoded.start_sample/self.rate
    calc_stop_time = self.unix_time + self.decoded.end_sample/self.rate
    cur.execute("INSERT INTO afsk (deploymentID, siteID, start_timestamp, stop_timestamp, message, binary_data, error) VALUES (%s, %s, %s, %s, %s, x%s, %s);", [self.tag_name, siteID, calc_start_time, calc_stop_time, self.decoded.string, self.decoded.raw_hex_str, self.decoded.error])

