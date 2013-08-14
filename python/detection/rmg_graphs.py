# rmg_graphs.py 
# defines the GNU Radio graphs for the software defined detection 
# backend. (rewrite? TODO) This file is part of QRAAT, an automated
# animal tracking system based on GNU Radio. 
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

"""
  This module defines the GNU Radio signal processing graphs for the b
  ackend detector array and filters. 
"""

from gnuradio import gr, blks2, uhd, gru
from rmg_swig import detect
import rmg_param

import sys, time

#: 1 to use pulse_shape_detector in pulse detector, 0 to not use it
#: **TODO:** this shouldn't be hardcoded here. It should be set 
#: in a top-level porgram.
USE_PSD = 1 


class usrp_top_block(gr.top_block):
    
        """ The USRP interface for GNU Radio. 
        
        :param fpga_frequency: (?) 
        :type fpga_frequency: int 
        :param decim_factor: decimation factor. explanation(?) 
        :type dcim_factor: int
        :param channels: number of input channels. 
        :type channels: int
        """ 

	def __init__(self, fpga_frequency = -10.7e6, decim_factor = 250, channels = 4):
		gr.top_block.__init__(self)

		self.channels = channels
		
		#Setup USRP
		self.u = uhd.usrp_source(device_addr="fpga=usrp1_fpga_4rx.rbf",stream_args=uhd.stream_args('fc32', channels=range(self.channels)))
		self.u.set_subdev_spec("A:A A:B B:A B:B")
		self.usrp_rate = self.u.get_clock_rate()
		self.usb_rate = self.usrp_rate / decim_factor

                self.u.set_samp_rate(self.usb_rate)

                print "USB Rate: ", self.usb_rate


		for j in range(self.channels):
	                self.u.set_center_freq(fpga_frequency,j)
                              
                
class software_backend(gr.hier_block2):
  
    """ The software filter and detector array.

      **TODO:** Describe the filtering steps and graph structure.
    
    :param channels: number of input channels from the USRP. 
    :type channels: int
    :param be_param: Backend parameters (?) 
    :type be_param: qraat.rmg.rmg_param.backend
    
    """ 
      
    def __init__(self, channels, be_param):

        gr.hier_block2.__init__(self, "software_backend",
                                gr.io_signature(4, 4, gr.sizeof_gr_complex), # Input signature
                                gr.io_signature(0, 0, 0))             # Output signature

        band_rate = be_param.bw
        print "Number of Bands :", be_param.num_bands
	print "Band sampling rate :",band_rate

        if be_param.num_bands > 1:
            #calculate the filter for the polyphase filter


            taps = gr.firdes.low_pass(1.0, 
                                  band_rate*be_param.num_bands, 
                                  0.4*band_rate , 
                                  0.1*band_rate ,
                                  gr.firdes.WIN_HANN)
            print "Band filter has", len(taps), "taps"

            #build filterbanks for each RF channel
            self.bank = []

            for j in range(channels):
	        self.bank.append(blks2.analysis_filterbank(be_param.num_bands,taps))
                self.connect((self,j), self.bank[j])

        # create be_param.num_bands detectors with enable/disable
        self.det = []
        for j in range(be_param.num_bands):
            
            #using default parameters for now
            filter_length = 160
            new_det = detect(filter_length,
                             filter_length * 3,
                             channels,
                             str('./dtest' + str(j) + '_'), 
                             str(j), 
                             band_rate,
                             0, 
                             USE_PSD)

            self.det.append(new_det)

            for k in range(channels):
                if be_param.num_bands > 1:
		    self.connect((self.bank[k],j),(new_det,k))
                else:
                    self.connect((self,k),(new_det,k))

        self.current_bands = None
        #enable correct bands
        self.enable(be_param.tunings[0].bands)
           
    def enable(self, bands):
        """ Enable the detector array. 

          **TODO:** not sure what *bands* is, nor the purpose of this function. 
        """
        if not self.current_bands is None:
            self.disable()
        self.current_bands = bands
        for j in bands:
            print j
            if (j.tx_type == rmg_param.PULSE):
                self.det[j.band_num].rise_factor(j.rise)
                self.det[j.band_num].fall_factor(j.fall)
                self.det[j.band_num].alpha_factor(j.alpha)
                self.det[j.band_num].enable(j.filter_length, 
                                            j.filter_length*3, 
                                            str(j.directory), 
                                            str(j.name), 
                                            j.cf, 
                                            USE_PSD)

            elif (j.tx_type == rmg_param.CONT):
                self.det[j.band_num].enable_cont(str(j.directory + '/' + j.name + '_' + time.strftime('%Y%m%d%H%M%S', time.gmtime()) + '.tdat'))


    def disable(self):
        """ Disable the detector array. """ 
        
        if not self.current_bands is None:
            for j in self.current_bands:
                self.det[j.band_num].disable()
        self.current_be_param = None

    def reset(self):
        """ Disable and enable the detector array. """ 

        be_param = self.current_be_param
        self.disable()
        self.enable(be_param)


# defines a noisey source for testing without usrp. 
class no_usrp_top_block(gr.top_block):
	def __init__(self, fpga_frequency = -10.7e6, decim_factor = 250, channels = 4, variance = 0.0):
		gr.top_block.__init__(self)
                noise_src = gr.noise_source_c(gr.GR_GAUSSIAN, variance, int(time.time()))
                throttle  = gr.throttle(gr.sizeof_gr_complex, 64e6/float(decim_factor)*channels)
                self.u = gr.deinterleave(gr.sizeof_gr_complex)
                self.connect(noise_src,throttle,self.u)
