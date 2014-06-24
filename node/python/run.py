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

import blocks, params
from pic_interface import pic_interface
import os, time

FPGA_FREQ = 10.7e6
CHANNELS = 4

class detector_array:
    """
      A GR signal processing graph comprised of blocks in in :mod:`qraat.rmg.blocks`. 
      The graph is made up of the USRP source, a polyphase filter bank, and the pulse 
      detector bank. This class handles time-multiplexing between transmitter tuning
      groups (see :class:`qraat.rmg.params.tuning`).

    :param filename: CSV-formatted transmitter configuration file. 
    :type filename: string
    :param directory: Target directory for .det files produced by the detector array. 
    :type directory: string
    :param num_bands: The number of bands to divide the receiver's bandwidth into. (Typically we use
       32 bands. The USRP bandwidth is 256 Khz, meaning each band is 8 Khz wide.) 
    :type num_bands: int
    :param serial_port: serial interface for PIC controller, given as a file name.
    :type serial_port: string
    :param no_usrp_flag: Use :class:`qraat.rmg.blocks.no_usrp_top_block` instead of the USRP source block. 
    :type no_usrp_flag: bool
    """ 

    def __init__(self,filename = "tx.csv",directory = "./det_files", num_bands = 1, serial_port = '/dev/ttyS0', no_usrp = None):
        
        print "Writing RMG status information to " + directory + '/status.txt'
        if not os.path.exists(directory):
            print 'Making directory: {0}'.format(directory)
            os.makedirs(directory)
        timestr = "\nInitializing RMG at {0}\n".format(time.strftime('%Y-%m-%d %H:%M:%S'))
        paramstr = "\tTransmitter File: {0}\n\tDirectory: {1}\n\tNumber of Bands: {2}\n\tSerial Port: {3}\n\tSource: ".format(filename, directory, num_bands, serial_port)
        if no_usrp != None:
            paramstr += "Null\n\n"
        else:
            paramstr += "USRP\n\n"
        with open(directory + '/status.txt','a') as status_file:
            status_file.write(timestr)
            status_file.write(paramstr)

        self.NO_USRP = no_usrp
        self.high_lo = True
        self.decim = 250
        self.filename = filename
        self.directory = directory
        if self.directory[-1] == "/":
          self.directory = self.directory[:-1]
        self.num_bands = num_bands
        self.backend_param = None
        self.frontend = None
        self.backend = None
        self.num_be = 0
        self.connected_be = 0
        if no_usrp != None:
            self.sc = None
            print "Serial Communication Disabled"
        else:
            self.sc = pic_interface(serial_port)

        self.__create_graph()
  
    ## private graph initialization routines ##

    def __create_graph(self):
        self.__load_param()
        self.__create_frontend()
        self.__create_backend()
        
        for j in range(CHANNELS):
	        self.frontend.connect((self.frontend.u,j), (self.backend,j))

        if not self.sc is None:
            self.sc.tune(self.backend_param.tunings[self.connected_be].lo1)
            check_tuple = self.sc.check(self.backend_param.tunings[self.connected_be].lo1)
            if not (check_tuple[0] and check_tuple[1] and check_tuple[2]):
                print "Pic frequency error"
                print "Reseting PIC"
                self.sc.reset_pic()
                self.sc.tune(self.backend_param[self.connected_be].lo1)
                check_tuple = self.sc.check(self.backend_param.tunings[self.connected_be].lo1)
                if not (check_tuple[0] and check_tuple[1] and check_tuple[2]):
                     print "Pic frequency error"
                     self.sc.freq_check()
                     raise ValueError, "Error setting frequency on RMG"

    def __load_param(self):
    #
    # Load a CSV formatted list of transmitters and calculate 
    # the USRP tuning parameters.  Chris ~18 Sep 2012
    #
        
        self.backend_param = params.backend(self.filename, self.num_bands)
        self.high_lo       = self.backend_param.high_lo
        self.decim         = self.backend_param.decim

        self.num_be = len(self.backend_param.tunings)
        if self.sc != None:
            if self.high_lo:
                self.sc.use_high_lo()
            else:
                self.sc.use_low_lo()

  
    def __create_frontend(self):
        if self.high_lo:
            lo3 = FPGA_FREQ
        else:
            lo3 = -FPGA_FREQ
        if self.NO_USRP == None:
            self.frontend = blocks.usrp_top_block(lo3, int(self.decim), CHANNELS)
        else:
            self.frontend = blocks.no_usrp_top_block(lo3, int(self.decim), CHANNELS, self.NO_USRP)
            print "Using Null Frontend"

    def __create_backend(self):

        self.backend = blocks.software_backend(CHANNELS, self.backend_param, self.directory)
     
    ## public runnables ##

    def next(self):
        print time.strftime('%Y-%m-%d %H:%M:%S')
        self.backend.disable()
        self.connected_be += 1
        if self.connected_be == self.num_be:
            self.connected_be = 0
        if self.sc != None:
            self.sc.tune(self.backend_param.tunings[self.connected_be].lo1)
        self.backend.enable(self.backend_param.tunings[self.connected_be].bands)
    
    def start(self):
        self.frontend.start()

    def run(self,sleep_sec = 10):
        timestr = "Starting RMG at {0}\n".format(time.strftime('%Y-%m-%d %H:%M:%S'))
        with open(self.directory + '/status.txt','a') as status_file:
            status_file.write(timestr)
            status_file.write(str(self.backend_param) + '\n')

        if self.num_be > 1:
            self.start()
            #
            # WARNIING: Keyboard Interrupt here is not caught! 
            #
            while(1):
                try:
                    time.sleep(sleep_sec)
                    self.next()
                except KeyboardInterrupt:
                    timestr = "Stopping RMG for Keyboard Interrupt at {0}\n\n".format(time.strftime('%Y-%m-%d %H:%M:%S'))
                    with open(self.directory + '/status.txt','a') as status_file:
                        status_file.write(timestr)

                    if self.sc != None:
                        del self.sc
                    break
                except:
                    timestr = "Stopping RMG for Exception at {0}\n\n".format(time.strftime('%Y-%m-%d %H:%M:%S'))
                    with open(self.directory + '/status.txt','a') as status_file:
                        status_file.write(timestr)
                    print "Exception "
                    raise
        else:
                try:
                    self.frontend.run()

                except KeyboardInterrupt:
                    timestr = "Stopping RMG for Keyboard Interrupt at {0}\n\n".format(time.strftime('%Y-%m-%d %H:%M:%S'))
                    with open(self.directory + '/status.txt','a') as status_file:
                        status_file.write(timestr)

                    if self.sc != None:
                        del self.sc




if __name__ == '__main__':
    dir_finder = detector_array()
    dir_finder.run()
