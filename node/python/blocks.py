# blocks.py 
# Defines the GNU Radio graphs for the software defined detection 
# backend. This file is part of QRAAT, an automated animal tracking 
# system based on GNU Radio. 
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
  This module defines the GNU Radio signal processing graphs for the 
  backend detector array and filters. 
"""

from gnuradio import gr, uhd
from gnuradio import filter as gr_filter
from gnuradio import analog as gr_analog
from gnuradio import blocks as gr_blocks
import qraat.rmg as rmg
import xml.dom.minidom

import sys, time, os

  ##XML helper functions##

class NoTagError(KeyError):

  def __init__(self, tagname):
    self.tagname = tagname

  def __str__(self):
    return "Tag Name: {} not found".format(self.tagname)

class MultipleTagError(KeyError):

  def __init__(self, tagname, number):
    self.tagname = tagname
    self.number = number

  def __str__(self):
    return "{} {} found".format(self.number,self.tagname)

#throws NoTagError if not in direct descendent
def get_one_element(dom,tagname):
  element_list = dom.getElementsByTagName(tagname)
  if len(element_list) == 0:
    raise NoTagError(tagname)
  elif len(element_list) > 1:
    copy_list = list(element_list)
    for e in copy_list:
      if not e in dom.childNodes:
        element_list.remove(e)
    if len(element_list) > 1:
      raise MultipleTagError(tagname, len(element_list))
    elif len(element_list) == 0:
      raise NoTagError(tagname)
  return element_list[0]

def get_one_value(dom,tagname):
  element = get_one_element(dom,tagname)
  children = element.childNodes
  val = ''
  if len(children) > 0:
    for j in children:
      if j.nodeType == j.TEXT_NODE:
        val += j.nodeValue
  return val


  ##BLOCKS##

class usrp_top_block(gr.top_block):
    
    """ The USRP interface for GNU Radio. 
        
        :param fpga_frequency: Intermediate frequency to which the 
                               FPGA should be tuned to. 
        :type fpga_frequency: float
        :param decim_factor: USRP decimation factor. 
        :type dcim_factor: int
        :param channels: Number of input channels. 
        :type channels: int
        """ 

    def __init__(self, fpga_frequency = -10.7e6, decim_factor = 250, channels = 4):
        gr.top_block.__init__(self)

        self.channels = channels

        #: The USRP source block. 
        self.u = uhd.usrp_source(device_addr="fpga=usrp1_fpga_4rx.rbf",
                                 stream_args=uhd.stream_args('fc32', 
                                     channels=range(self.channels)))
        self.u.set_subdev_spec("A:A A:B B:A B:B")

        # Set USB transfer rate to the bandwidth of the USRP. 
        self.usrp_rate = self.u.get_clock_rate()
        self.usb_rate = self.usrp_rate / decim_factor
        self.u.set_samp_rate(self.usb_rate)
        print "USB Rate: ", self.usb_rate

                # All input channels should be set to the FPGA frequency.  
        for j in range(self.channels):
            self.u.set_center_freq(fpga_frequency, j)
                              
               
class no_usrp_top_block(gr.top_block):
    """ A noisy signal source used for testing. 
              
          Replaces :class:`qraat. rmg.rmg_graphs.usrp_top_block`. 
        """

    def __init__(self, fpga_frequency = -10.7e6, channels = 4, variance = 0.0, sample_rate = 256000):
        gr.top_block.__init__(self)

        # Gaussian distributed signal source. 
        noise_src = gr_analog.noise_source_c(gr_analog.GR_GAUSSIAN, variance, int(time.time()))

        # Throttle signal to the same sampling rate as the USRP. 
        throttle  = gr_blocks.throttle(gr.sizeof_gr_complex, 
                                sample_rate * channels)
                
        #: Gaussian distributed signal source, deinterleaved to the number of channels. 
        self.u = gr_blocks.deinterleave(gr.sizeof_gr_complex)
        self.connect(noise_src,throttle,self.u)


#generic gnuradio hierarchal block for use as backend sink
class backend_block(gr.hier_block2):

  def __init__(self, name, number_of_channels):
    gr.hier_block2.__init__(self, name, gr.io_signature(number_of_channels, number_of_channels, gr.sizeof_gr_complex), gr.io_signature(0,0,gr.sizeof_gr_complex))
    self.number_of_channels = number_of_channels

#generic transmitter class
class transmitter(backend_block):

  def __init__(self,
               identification='',
               number_of_channels=0,
               band_center_frequency=0.0,
               tx_frequency=0.0, 
               bandwidth=1,
               directory='./'):
    if number_of_channels < 0:
      raise ValueError("Number of channels must be non-negative, not {}".format(number_of_channels))
    backend_block.__init__(self, 'transmitter_sink', number_of_channels)
    self.identification = str(identification)
    if ((band_center_frequency + bandwidth/2.0) > tx_frequency) and ((band_center_frequency - bandwidth/2.0) < tx_frequency):
      self.band_center_frequency = band_center_frequency
      self.tx_frequency = tx_frequency
      self.bandwidth = bandwidth
    else:
      raise ValueError("tx_frequency: {0:.6f} MHz not in band (band_center_frequency: {1:.6f} MHz +/- bandwidth/2: {2:.6f} MHz)".format(tx_frequency/1000000.0, band_center_frequency/1000000.0, bandwidth/2000000.0)) 
    self.directory = str(directory).rstrip('/')#directory string doesn't have trailing /
    interleaver = gr_blocks.interleave(gr.sizeof_gr_complex)
    sink = gr_blocks.null_sink(gr.sizeof_gr_complex)#, directory + identification + '.tdat')
    for k in range(number_of_channels):
      self.connect((self, k), (interleaver, k))
    self.connect(interleaver, sink)

  def __str__(self):
    s = "Generic Transmitter Block (null_sink)\n"
    s += "\tID: {}\n".format(self.identification)
    s += "\tBand Center Frequency: {}\n".format(self.band_center_frequency)
    s += "\tBandwidth: {}\n".format(self.bandwidth)
    s += "\tTransmitter Frequency: {}\n".format(self.tx_frequency)
    s += "\tDirectory: {}\n".format(self.directory)
    return s

  @classmethod
  def from_xml(cls, tx_node, number_of_channels=4, directory='./', bandwidth = 1, band_center_frequency = 0):
    identification = tx_node.getAttribute('ID')#as string
    tx_frequency = float(get_one_value(tx_node, 'tx_frequency'))
    try:
      tx_type = get_one_value(tx_node, 'type').strip()
    except NoTagError:
      myself = cls(identification, number_of_channels, band_center_frequency, tx_frequency, bandwidth, directory)
    else:
      if tx_type == "pulse":
        myself = pulse_transmitter.from_xml(tx_node, number_of_channels, directory, bandwidth, band_center_frequency)
      else:  
        raise ValueError("Unknown transmitter type: {}".format(tx_type))
    return myself

#pulse transmitter class
class pulse_transmitter(transmitter):

  def __init__(self,
               identification='',
               number_of_channels=0,
               band_center_frequency=0.0,
               tx_frequency=0.0, 
               bandwidth=1, 
               directory='./',
               filter_length=1,
               rise=1.1,
               alpha=10,
               save_length = None):
    transmitter.__init__(self, identification, number_of_channels, band_center_frequency, tx_frequency, bandwidth, directory)
    self.filter_length = filter_length
    self.rise = rise
    self.alpha = alpha
    if save_length is None:
      self.save_length = self.filter_length*3
    else:
      self.save_length = save_length
    self.directory += '/det_files'
    self.block = rmg.blocks.pulse_sink_c(self.number_of_channels)
    self.block.enable(self.filter_length, 
                      self.save_length, 
                      self.band_center_frequency,
                      self.bandwidth,
                      self.directory,
                      self.identification,
                      self.rise,
                      self.alpha)
    for j in range(self.number_of_channels):
      self.connect((self, j), (self.block, j))

  def __str__(self):
    s = "Pulse Transmitter Block (null_sink)\n"
    s += "\tID: {}\n".format(self.identification)
    s += "\tBand Center Frequency: {}\n".format(self.band_center_frequency)
    s += "\tBandwidth: {}\n".format(self.bandwidth)
    s += "\tTransmitter Frequency: {}\n".format(self.tx_frequency)
    s += "\tDirectory: {}\n".format(self.directory)
    s += "\tFilter Length: {}\n".format(self.filter_length)
    s += "\tSave Length: {}\n".format(self.save_length)
    s += "\tRise: {}\n".format(self.rise)
    s += "\tAlpha: {}\n".format(self.alpha)
    return s

  @classmethod
  def from_xml(cls, tx_node, number_of_channels=4, directory='./', bandwidth = 1, band_center_frequency = 0):
    identification = tx_node.getAttribute('ID')#as string
    tx_frequency = float(get_one_value(tx_node, 'tx_frequency'))
    tx_type = get_one_value(tx_node, 'type').strip()
    if not tx_type == 'pulse':
      raise TypeError("Not a pulse transmitter")
    det_directory = directory.rstrip('/') + '/det_files'
    filter_length = int(get_one_value(tx_node, 'filter_length'))
    rise = float(get_one_value(tx_node, 'rise'))
    alpha = float(get_one_value(tx_node, 'alpha'))
    try:
      save_length = int(get_one_value(tx_node, 'save_length'))
    except NoTagError:
      save_length = None
    return cls(identification,
                    number_of_channels,
                    band_center_frequency,
                    tx_frequency, 
                    bandwidth, 
                    det_directory,
                    filter_length,
                    rise,
                    alpha,
                    save_length)


class channelizer(backend_block):

  def __init__(self,
               number_of_channels=0,
               number_of_bands=2,
               bandwidth=1,
               cutoff_frequency=None,
               transistion_band=None):
    if number_of_channels < 0:
      raise ValueError("Number of channels must be non-negative, not {}".format(number_of_channels))
    backend_block.__init__(self, 'channelizer', number_of_channels)
    self.number_of_bands = number_of_bands
    self.bandwidth = bandwidth #bandwidth of individual band
    self.total_bandwidth = self.bandwidth*self.number_of_bands
    if cutoff_frequency is None:
      self.cutoff_frequency = self.bandwidth/2.0*0.9
    else:
      self.cutoff_frequency = cutoff_frequency
    if transistion_band is None:
      self.transistion_band = self.bandwidth/2.0-self.cutoff_frequency
    else:
      self.transistion_band = transition_band
    self.child_list = []
    self.channel_map = []
    self.connected_block_list = []
    self.pfb_blocks = []
    self.s2ss_blocks = []
    if number_of_channels > 0:
      self.low_pass_filter = gr_filter.firdes.low_pass(1.0,
                                                self.total_bandwidth,
                                                self.cutoff_frequency,
                                                self.transistion_band,
                                                 gr_filter.firdes.WIN_HANN)
      for k in range(self.number_of_channels):
        #using channelizer from gnuradio 3.7.6 spec
        self.pfb_blocks.append(gr_filter.pfb.channelizer_ccf(self.number_of_bands, self.low_pass_filter))
        self.connect((self,k), self.pfb_blocks[k])

  def __str__(self):
    s = "{} Band Channelizer\n".format(self.number_of_bands)
    s += "\tInput Bandwidth: {} Hz\n".format(self.total_bandwidth)
    s += "\tOutput Bandwidth: {} Hz\n".format(self.bandwidth)
    s += "\tCutoff Frequency: {} Hz\n".format(self.cutoff_frequency)
    s += "\tTransition Bandwidth: {} Hz\n".format(self.transistion_band)
    s += "\tNumber of Filter Taps: {}\n".format(len(self.low_pass_filter))
    s += "{} Occupied Bands\n".format(len(set(self.channel_map)))
    for j in range(len(self.child_list)):
      s += "Band {} - \n".format(self.channel_list[j])
      s += self.child_list[j]
    return s

  @classmethod
  def from_xml(cls, channelizer_node, number_of_channels=0, directory='./'):
    num_bands = int(get_one_value(channelizer_node,'num_bands'))
    bandwidth = float(get_one_value(channelizer_node,'bandwidth'))
    try:
      cutoff_frequency = float(get_one_value(channelizer_node,'cutoff_frequency'))
    except NoTagError:
      cutoff_frequency = None
    try:
      transistion_band = float(get_one_value(channelizer_node,'transition_band'))
    except NoTagError:
      transistion_band = None
    myself = cls(number_of_channels, num_bands, bandwidth, cutoff_frequency, transistion_band)
    channel_map = []
    child_list = []
    for node in channelizer_node.childNodes:
      if node.nodeType == node.ELEMENT_NODE and node.tagName == 'band':
        band_number = int(node.getAttribute('number'))
        band_center_frequency = float(get_one_value(node,'band_center_frequency'))
        for n in node.childNodes:
          if n.nodeType == n.ELEMENT_NODE and n.tagName == 'transmitter':
            tx = transmitter.from_xml(node, number_of_channels, directory, bandwidth, band_center_frequency)
            child_list.append(tx)
            channel_map.append(band_number)
          if n.nodeType == n.ELEMENT_NODE and n.tagName == 'channelizer':
            child_channelizer = channelizer.from_xml(node, number_of_channels, directory)
            child_list.append(child_channelizer)
            channel_map.append(band_number)
    myself.connect_list(child_list, channel_map)
    return myself

  #connects given list to channelizer
  #child_list is a list of config objects that are backend_blocks
  def connect_list(self, child_list, channel_map=[]):
    self.child_list = child_list
    self.channel_map = channel_map
    if self.child_list:
      if self.channel_map:
        if not len(self.child_list) == len(self.channel_map):
          raise IndexError("child_list: len={0:d} and channel_map: len={1:d} are not the same length".format(len(self.child_list),len(self.channel_map)))
      else:
        print "No channel_map.  Assuming children are connected in order."
        self.channel_map = range(len(self.child_list))
    else:
      print "No children to connect"
      return
    self.connected_block_list = []
    for j in range(len(self.child_list)):
      for k in range(self.number_of_channels):
        self.connect((self.pfb_blocks[k],self.channel_map[j]),(self.child_list[j],k))
    for band in set(range(self.number_of_bands))-set(self.channel_map):
      for k in range(self.number_of_channels):
        self.connect((self.pfb_blocks[k],band), gr_blocks.null_sink(gr.sizeof_gr_complex))

class tuning(backend_block):

  def __init__(self, identification='', number_of_channels=0, center_freq=0.0, pll_freq=0): 
    if number_of_channels < 0:
      raise ValueError("Number of channels must be non-negative, not {}".format(number_of_channels))
    backend_block.__init__(self, 'tuning', number_of_channels)
    self.identification = identification
    self.center_freq = center_freq
    self.pll_freq = pll_freq
    self.child_list = []

  def __str__(self):
    s = "Tuning {}\n".format(self.identification)
    s += "\nCenter_frequency: {}\n".format(self.center_freq)
    s += "\nFirst LO frequency: {}\n".format(self.pll_freq)
    for child in self.child_list:
      s += self.child_list
    return s

  @classmethod
  def from_xml(cls, tuning_node, number_of_channels,directory):
    identification = tuning_node.getAttribute('ID')
    center_freq = float(get_one_value(tuning_node,'center_frequency'))
    pll_freq = int(get_one_value(tuning_node,'pll_frequency'))
    myself = cls(identification, number_of_channels, center_freq, pll_freq)
    for child_node in tuning_node.childNodes:
      if child_node.nodeType == child_node.ELEMENT_NODE:
        if child_node.tagName == 'transmitter':
          tx = transmitter.from_xml(child_node, number_of_channels, directory, bandwidth)
          myself.child_list.append(tx)
          for j in range(number_of_channels):
            myself.connect((myself,j), (tx, j))
        if child_node.tagName == 'channelizer':
          child_channelizer = channelizer.from_xml(child_node, number_of_channels, directory)
          myself.child_list.append(child_channelizer)
          for j in range(number_of_channels):
            myself.connect((myself, j), (child_channelizer,j))
    return myself

class timing():

  def __init__(self):
    self.period_total = 0
    self.timing_list = []

  def __str__(self):
    s = "Total time: {} seconds\n".format(self.period_total)
    for t in self.timing_list:
      s+= "Tuning:\t{}\tDuration:\t{}\n".format(t[0],t[1])
    return s

  @classmethod
  def from_xml(cls, timing_node, tuning_ids):
    myself = cls()
    myself.process_nodes(timing_node, tuning_ids)
    return myself

  def process_nodes(self, timing_node, tuning_ids):
    for node in timing_node.childNodes:
      if node.nodeType == node.ELEMENT_NODE:
        if node.tagName == 'period':
          self.add_period(node, tuning_ids)
        elif node.tagName == 'loop':
          self.add_loop(node, tuning_ids)


  def add_period(self, period_node, tuning_ids):
    tuning_id = period_node.getAttribute("tuning_ID")
    if not tuning_id in tuning_ids:
      raise KeyError("No tuning in tunings with ID = {}".format(tuning_id))
    for n in period_node.childNodes:
      if n.nodeType == n.TEXT_NODE:
        period_value = int(n.nodeValue)
        if self.timing_list and tuning_id == self.timing_list[-1][0]:
          self.timing_list[-1] = (tuning_id, period_value + self.timing_list[-1][1], self.timing_list[-1][2], period_value + self.timing_list[-1][3])
          self.period_total += period_value
        else:
          self.timing_list.append((tuning_id,period_value,self.period_total, self.period_total+period_value))
          self.period_total += period_value
        continue
    
  def add_loop(self, loop_node, tuning_ids):
    loops = int(loop_node.getAttribute("times"))
    for count in range(loops):
      self.process_nodes(loop_node, tuning_ids)

  def get_tuning(self, current_time):
    remainder = current_time % self.period_total
    period_start = (current_time // self.period_total)*self.period_total
    for t in self.timing_list:
      if remainder < t[3] - 1 and remainder > t[2] - 1:#don't return a tuning with less than a second of time
        return t[0], period_start + t[3]

class software_backend():#TODO add errors and error handling maybe?  Enable or saved state?

  def __init__(self, xml_filename, directory):

    self.dom = xml.dom.minidom.parse(xml_filename)
    self.tx_list = get_one_element(self.dom,'tx_list')
    self.directory = directory

    #self.directory = get_one_value(self.tx_list,'directory').strip().rstrip('/')
    self.usrp_channels = int(get_one_value(self.tx_list,'number_USRP_channels'))
    self.fpga_freq = float(get_one_value(self.tx_list,'FPGA_frequency'))
    self.usrp_rate = float(get_one_value(self.tx_list,'USRP_sampling_rate'))
    self.fpga_decim = int(get_one_value(self.tx_list,'FPGA_decimation'))
    self.usb_rate = float(get_one_value(self.tx_list,'USB_sampling_rate'))

    if self.fpga_freq > 0:
      self.high_lo = False
    else:
      self.high_lo = True

    tuning_node_list = get_one_element(self.tx_list,'tunings').getElementsByTagName('tuning')
    self.tunings = dict()
    for t in tuning_node_list:
      new_tuning = tuning.from_xml(t, self.usrp_channels, self.directory)
      self.tunings[new_tuning.identification]=new_tuning
    self.timing = timing.from_xml(get_one_element(self.tx_list,'timing'),self.tunings.keys())

  def __str__(self):
    s = "Receiver Settings\n"
    s += "USRP Channels: {}\n".format(self.usrp_channels)
    s += "USRP LO Frequency: {} Hz\n".format(self.fpga_freq)
    s += "USRP Sampling Rate: {} Hz\n".format(self.usrp_rate)
    s += "FPGA Decimation Factor: {}\n".format(self.fpga_decim)
    s += "USB Sample Rate: {} Hz\n".format(self.usb_rate)
    if self.high_lo:
      s += "Using High 1st LO\n"
    else:
      s += "Using Low 1st LO\n"
    s += "{} Backend Tunings\n\n".format(len(self.tunings))
    for t in self.tunings:
      s += t
      s +="\n"
    return s

#import params
class record_backend(gr.hier_block2):#TODO update this
  
    """ record baseband for given LO settings

    :param channels: Number of input channels from the USRP. 
    :type channels: int
    :param be_param: Backend RF parameters.
    :type be_param: qraat.rmg.params.backend
    """ 
    
    def __init__(self, channels, be_param, directory = "./det_files"):

        gr.hier_block2.__init__(self, "record_backend",
                                gr.io_signature(4, 4, gr.sizeof_gr_complex), # Input signature
                                gr.io_signature(0, 0, 0))                    # Output signature

        self.band_rate = be_param.bw*be_param.num_bands
        print "Number of Bands: 1"
        print "Band sampling rate: ",self.band_rate

        self.directory = directory

        filename = os.path.join(self.directory, "placeholder.tdat")

        interleaver = gr_blocks.interleave(gr.sizeof_gr_complex)
        self.file_sink = gr_blocks.file_sink(gr.sizeof_gr_complex, filename)
        self.file_sink.close()
        # Connect filter outputs to each detector.             
        for k in range(channels):
            self.connect((self,k),(interleaver,k))

        self.connect(interleaver, self.file_sink)

        #: Band set of current tuning. 
        self.current_bands = None
   
    def enable(self, bands=None):
        if bands:
          self.center_frequency = bands[0].cf
        print "Enabling frequency {} at {}".format(self.frequency, time.strftime("%Y%m%d%H%M%Z"))
        self.file_sink.open(os.path.join(self.directory, "{0:.0f}kHz_{1}.tdat".format(self.center_frequency/1000.0,time.strftime("%Y%m%d%H%M%Z"))))

    def disable(self):
        self.file_sink.close()

    def reset(self):
        self.disable()
        self.enable()

