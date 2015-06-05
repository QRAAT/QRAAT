# record.py 
# Connect GNU Radio processing blocks into a graph. class record_baseband
# defines a graph for recording baseband covering all frequencies
# specified. This file is part of QRAAT, an automated animal tracking system 
# based on GNU Radio. 
#
# Copyright (C) 2012 Todd Borrowman, Christopher Patton
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


import run
import blocks

import time

class record_baseband(run.detector_array):

  def __init__(self,filename = "tx.csv",directory = "./det_files", num_bands = 1, serial_port = '/dev/ttyS0', no_usrp = None):
    run.detector_array.__init__(self, filename, directory, num_bands, serial_port, no_usrp)
    #run.detector_array.__init__(self, filename, directory, num_bands, serial_port, no_usrp)
    for j in range(run.CHANNELS):
      self.frontend.disconnect((self.frontend.u,j), (self.backend,j))
    self.backend = blocks.record_backend(run.CHANNELS, self.backend_param, self.directory)
    for j in range(run.CHANNELS):
      self.frontend.connect((self.frontend.u,j), (self.backend,j))

  def run(self,sleep_sec = 10):
    timestr = "Starting RMG at {0}\n".format(time.strftime('%Y-%m-%d %H:%M:%S'))
    with open(self.directory + '/status.txt','a') as status_file:
      status_file.write(timestr)
      status_file.write(str(self.backend_param) + '\n')

    for j in range(self.num_be):
      self.start()
      time.sleep(sleep_sec)
      self.next()
