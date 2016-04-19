# run.py 
# Connect GNU Radio processing blocks into a graph. class detector_array
# defines an array of these graphs for detecting pulses on all frequencies
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

import blocks
from pic_interface import pic_interface
import os, time
import qraat.error


class detector_array:
  """
    A GR signal processing graph comprised of blocks in in :mod:`qraat.rmg.blocks`. 
    The graph is made up of the USRP source, a polyphase filter bank, and the pulse 
    detector bank. This class handles time-multiplexing between transmitter tuning
    groups (see :class:`qraat.rmg.params.tuning`).

  :param filename: XML-formatted transmitter configuration file. 
  :type filename: string
  :param directory: Target directory for .det files produced by the detector array. 
  :type directory: string
  :param serial_port: serial interface for PIC controller, given as a file name.
  :type serial_port: string
  :param no_usrp_flag: Use :class:`qraat.rmg.blocks.no_usrp_top_block` instead of the USRP source block. 
  :type no_usrp_flag: bool
  :param log_file: full path and filename to write log to
  :type log_file: string
  """ 

  def __init__(self,filename = "tx.xml",directory = "./detector_output/", serial_port = '/dev/ttyS0', no_usrp = None, log_file = None):

    self.log_file = log_file
    self.log("Initializing RMG at {0}\n".format(time.strftime('%Y-%m-%d %H:%M:%S')))
    paramstr = "\tTransmitter File: {0}\n\tDirectory: {1}\n\tSerial Port: {2}\n\tSource: ".format(filename, directory, serial_port)
    if no_usrp != None:
        paramstr += "Null\n\n"
    else:
        paramstr += "USRP\n\n"
    self.log(paramstr)
    if not os.path.exists(directory):
        os.makedirs(directory)
    self.NO_USRP = no_usrp
    self.high_lo = True
    self.filename = filename
    self.directory = directory
    if self.directory[-1] == "/":
      self.directory = self.directory[:-1]
    self.__create_graph()

  ## private graph initialization routines ##

  def __create_graph(self):
    self.__create_backend()
    self.__create_frontend()

  def __create_frontend(self):
    if self.NO_USRP == None:
      self.frontend = blocks.usrp_top_block(self.backend.fpga_freq, self.backend.fpga_decim, self.backend.usrp_channels)
      self.sc = pic_interface(serial_port)
      if self.backend.high_lo:
        self.sc.use_high_lo()
      else:
        self.sc.use_low_lo()
    else:
      self.frontend = blocks.no_usrp_top_block(self.backend.fpga_freq,  self.backend.usrp_channels, self.NO_USRP, self.backend.usb_rate)
      self.sc = None
      self.log("Using Null Frontend, Serial Communication Disabled\n")

  def __create_backend(self):
    self.backend = blocks.software_backend(self.filename, self.directory)
    self.connected_tuning = None
    self.log("Timing Block ")
    self.log(str(self.backend.timing))
    self.log("\n")



  ## public runnables ##

  def log(self, log_string):
    if self.log_file:
      with open(self.log_file, 'a') as lf:
        lf.write(log_string)

  def tune_pll(self, freq):
    if not self.sc is None:
      self.sc.tune(freq)
      if not self.sc.check(freq):
        self.log("Pic frequency error, retry\n")
        self.sc.tune(freq)
        if not self.sc.check(freq):
          self.log("Pic frequency error, Reseting PIC\n")
          self.sc.reset_pic()
          self.sc.tune(freq)
          if not self.sc.check(freq):
            self.log("Pic frequency error\n")
            self.log(self.sc.status_string())
            raise qraat.error.PLL_LockError()

  def connect(self, tuning_id):
    self.connected_tuning = self.backend.tunings[tuning_id]
    for c in range(self.backend.usrp_channels):
      self.frontend.connect((self.frontend.u,c), (self.connected_tuning,c))

  def disconnect(self):
    if self.connected_tuning:
      for c in range(self.backend.usrp_channels):
        self.frontend.disconnect((self.frontend.u,c), (self.connected_tuning, c))
    self.connected_tuning = None

  def run(self):
    self.log("Starting RMG main loop at {0}\n".format(time.strftime('%Y-%m-%d %H:%M:%S')))
    if len(self.backend.tunings) == 0:
      self.log("No backend tunings\nStopping at {}\n".format(time.strftime('%Y-%m-%d %H:%M:%S')))
    elif len(self.backend.tunings) == 1:
      tuning_id = self.backend.tunings.keys[0]
      self.log("Only one backend tuning, Running tuning {}".format(tuning_id))
      self.connect(tuning_id)
      self.frontend.run() #blocking call
    else:
      while(1):#run loop
        current_time = time.time()
        tuning_id, stop_time = self.backend.timing.get_tuning(current_time)
        self.connect(tuning_id)
        self.log("{}: Running tuning {} until {}\n".format(current_time, tuning_id, stop_time)) 
        self.frontend.start()
        time.sleep(stop_time - time.time())
        self.frontend.stop()
        self.frontend.wait()
        self.disconnect()

  def run_once(self):
    self.log("Starting RMG once through at {0}\n".format(time.strftime('%Y-%m-%d %H:%M:%S')))
    for t in self.backend.timing.timing_list:
      self.connect(t[0])
      self.log("Runing tuning {} for {} seconds\n".format(t[0],t[1]))
      self.frontend.start()
      time.sleep(t[1])
      self.frontend.stop()
      self.frontend.wait()
      self.disconnect()
    self.log("Finished at {0}\n\n".format(time.strftime('%Y-%m-%d %H:%M:%S')))


if __name__ == '__main__':
    dir_finder = detector_array(filename="./test_tx.xml", no_usrp=0.01, log_file="./log_file")
    dir_finder.run_once()
