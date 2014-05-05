# params.py
# Parameter classes for software defined detector backend. This file 
# is part of QRAAT, an automated animal tracking system based on GNU Radio. 
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
  The classes in this module encapsulate the various RF parameters 
  for the RMG receiver and calculate the tuning groups for the software
  detector arrays. We give a brief overview of both the analog and 
  digital filtering, and the constraints these steps impose on the 
  software-defined radio down stream.  

  The following analog filters are applied to each input channel: 
   (1) Amplify by +22 dB. 
   (2) Mix with tunable oscillator (the PLL), 
       controlled by :mod:`qraat.rmg.pic_interface`, down to 70 Mhz. 
       (``cf = pll_cf - if1_cf``).
   (3) Saw filter at 70 Mhz (:data:`backend.if1_cf`), +/- 250 Khz 
       (:data:`backend.if1_bw`). 
   (4) Amplify by +22 dB. 
   (5) Mix with oscillator at 80.7 Mhz (:data:`backend.lo2`).
   (6) Ceramic filter at 10.7 Mhz (:data:`backend.if2_cf`), +/- 125 Khz 
       (:data:`backend.if2_bw`).
   (7) Amplify by +22 dB
   (8) Output to USRP for digital sampling. 

  The USRP Samples analog signal at 64 Ms/sec (:data:`usrp_sampling_rate`). Each 
  per channel sample has a real part (*in-phase*) and imaginary part 
  (*quadrature*). Both of these samples are mixed with the NCO by +/- 
  10.7 Mhz (see :data:`backend.high_lo`.) The signal 
  is then down-sampled to 256 Ks/sec. We need to maintain the Nyquist-Shannon 
  theorem criterion in order to avoid aliasing in the resulting 
  digital signal. The process of first passing the signal through a 
  low-pass anti-aliasing filter and then reducing the sampling rate 
  is known as decimation. The low pass filter yields an approximation, 
  since a perfect realtime filter isn't realizable. 
   
"""

import math, sys
import qraat 

#: Enumerated type for the data type output for a particular band from 
#: radio. This is used in qraat.rmg.run to decide to use a continuous 
#: baseband recorder or pulse detector. 
det_type = qraat.util.enum('PULSE', 'CONT')

#: String representations of radio output types. 
det_type_str = { det_type.PULSE : "Pulse Detector", 
                 det_type.CONT  : "Raw Baseband Recording" }

#: The type of data produced by a transmitter, specified in the 'type' 
#: column of the configuration file. This dictionary maps the transmitter
#: type to the detector type. 
tx_type = { "pulse"      : det_type.PULSE, 
            "continuous" : det_type.CONT, 
            "other"      : det_type.CONT }

#: Number of samples processed by the USRP per second. (Usually 64 Ms/sec.)  
usrp_sampling_rate = 64e6 

#: Maximum decimation factor for the USRP. 
usrp_max_decimation = 250



class band:
    """ Data for a single detector band, including the transmitter parameters.  
    
    :param tx: Transmitter paramters. 
    :type tx: qraat.csv.csv.Row 
    :param band_num: Band number, i.e. index in pulse detector array. 
    :type band_num: int
    :param band_cf: Band center frequency.
    :type band_cf: float
    :param filter_length: (?) 
    :type filter_length: int 

    """

    def __init__(self, tx, band_num, band_cf, filter_length):
        self.name = tx.name        #: Transmitter name. 
        self.tx_type = tx.type     #: Transmitter type. 
        self.band_num = band_num   #: Index of band in pulse detector array. 
        self.cf = band_cf          #: Band center frequency. 
        
        if (self.tx_type == det_type.PULSE):
            self.filter_length = filter_length #: (?) 
            self.rise = tx.rise_trigger        #: Rise trigger (pulse detector paramater).
            self.fall = tx.fall_trigger        #: Fall trigger (pulse detector paramater).
            self.alpha = tx.filter_alpha       #: Alpha factor (pulse detector paramater).
        
        else:
            self.filter_length = 0
            self.rise = 0.0
            self.fall = 0.0
            self.alpha = 0.0


    def combine_tx(self, tx, filter_length):
        """ Listen to many transmitters on the same frequency in the same band. 

          It's impossible to avoid false positives in this situation in general, 
          so we'll pick up pulses from any tranmmitter on this frequency. The 
          idea is that there may be a way to uniquely identify them downstream. 
        """ 
        self.name = self.name + tx.name + '_'
        if (self.tx_type != CONT):
        
            if (tx.type == CONT):
                self.tx_type = CONT
            else:
                if (filter_length > self.filter_length):
                    self.filter_length = filter_length
                if (tx.rise_trigger < self.rise):
                    self.rise = tx.rise_trigger
                if (tx.fall_trigger > self.fall  and self.rise > tx.fall_trigger):
                    self.fall = tx.fall_trigger
                if (tx.filter_alpha < self.alpha):
                    self.alpha = tx.filter_alpha


    def __str__(self):
        """ Print band paramters to console. """ 
        if (self.tx_type == det_type.PULSE):
            band_str = ("Band #: {0:d}\nBand Frequency: {1:f} MHz\n\tName: "
                        "{2}\n\tType: {3}\n\tFilter Length: {4:d} samples"
                        "\n\tRise: {5:.2f}, Fall: {6:.2f}, Alpha: {7:.3f}").format(
                self.band_num, self.cf/1000000, self.name, det_type_str[self.tx_type], 
                self.filter_length,self.rise,self.fall,self.alpha)
        else:
            band_str = ("Band #: {0:d}\nBand Frequency: {1:f} MHz\n\tName: "
                        "{2}\n\tType: {3}").format(
                 self.band_num, self.cf/1000000, self.name, det_type_str[self.tx_type])
        return band_str



class tuning:
    """ Data for a single tuning of the RMG receiver. 
      
      The RMG receiver was built with bandwidth restrictions in mind. 
      When two transmitters use frequencies differing by more than the 
      USRP output bandwidth (typically 256 Khz), it is necessary to 
      time-multiplex the frequencies, retuning the RMG receiver during 
      the transition. (See :class:`qraat.rmg.run.detector_array`.) 

    :param backend: Backend paramters
    :type backend: qraat.rmg.params.backend
    :param cf: Center frequency for tuning. 
    :type cf: float
    :param lo1: Actual PLL frequency of receiver. 
    :type lo1: float
    """ 
    
    def __init__(self, backend, cf = 0.0, lo1 = 0.0):
      self.cf = cf   #: Center frequency for tuning. 
      self.lo1 = lo1 #: Actual PLL frequency (derived from center frequency and RF parameters).

      self.num_possible_bands = backend.num_bands # ref up stream
      self.bw = backend.bw # ref upstream

      #: Detector bands of type :class:`qraat.rmg.params.band`.  
      self.bands = [] 


    def add_tx(self, tx):
      """ Assign transmitter to a band.
      
        The transmitter's baseband is the tuning's center frequency 
        subtracted from the transmission frequency. This value is 
        used to bin the transmitter. It's possible that we may have 
        many transmitters on the same frequency, or whose frequencies
        are close enough to be indistinguishable in this context. To 
        deal with this as elegantly as possible, we check to see if 
        there is already a transmitter assigned ot this band on this 
        tuning. If so, then combine the detector parameters in an 
        intelligent way. (See :func:`band.combine_tx`.) 

      :param tx: Transmitter configuration.
      :type tx: qraat.csv.csv.Row
      """

      tx_freq = tx.frequency * 1000000.0
      baseband_freq = tx_freq - self.cf
      baseband_band_num = round(baseband_freq / self.bw)

      if (baseband_band_num >= 0):
        band_num = int(baseband_band_num)
      else:
        band_num = int(self.num_possible_bands + baseband_band_num)
      filter_length = int(round(tx.pulse_width * self.bw / 1000))

      # Check to see if there is already a transmitter assigned ot 
      # this band on this tuning. 
      for c in self.bands:
        if (c.band_num == band_num):
           c.combine_tx(tx, filter_length)
           return
      
      # Otherwise, add the band. 
      band_cf = baseband_band_num*self.bw+self.cf
      self.bands.append(
        band(tx, band_num, band_cf, filter_length))


    def __str__(self):
      """ Return string representation of the tuning. """ 
      be_str = ("Center Frequency: {0:.1f} MHz\nPLL Frequency: {1:.1f} "
                "MHz\nNumber of Occupied Bands: {2:d}").format(
        self.cf/1000000.0, self.lo1/1000000.0, len(self.bands))
      for j in self.bands:
        be_str += '\n' + str(j)
      return be_str



class backend:
    """ RF parameters for the RMG receivers.  

      Load a list of transmitters from a .csv file. (This is for modifying 
      the list of transmitters.) Calculate the backend tuning. 

    :param path: filename of transmitter configuration file. 
    :type path: string
    :param num_bands: Number of detector bands
    :type num_bands: int
    """ 

    pa_min = 148000000 #: Lower bound frequency (Hz) for the pre amps output. 
    pa_max = 178000000 #: Upper bound frequency (Hz) for the pre amp output.

    if1_cf = 70000000 #: Center frequency of the first saw filter (intermediate freqency). 
    if1_bw = 500000   #: Bandwidth of the first saw filter. 
    if2_cf = 10700000 #: Center freqency of the second ceramic filter (intermediate frequency). 
    if2_bw = 250000   #: Bandwidth of the the second ceramic filter. 
    
    #: Frequency of oscillator between the saw and ceramic filters.  
    lo2 = 80700000  
      
    #: Step size (Hz) for the phase-locked loop (PLL), controlled by the 
    #: PIC interface of the RMG receiver. (Default is 100 Khz; you don't 
    #: want to change this, since the circuitry is optimized for this step.)
    pv_step = 100000

    pv_min = 218500000 #: Lower bound frequency (Hz) for the PLL. 
    pv_max = 248000000 #: Upper bound frequency (Hz) for the PLL. 

    #: Account for minor frequency error for the RMG receiver. It may be 
    #: possible that the output frequency of the PLL is off the center
    #: frequency by a few Khz. ``pv_tune + pv_offset = actual_pv_tune``.
    #: **NOTE**: this should be callibrated per RMG receiver. 
    pv_offset = 0 
      
    #: The USRP has a numerically controlled oscillator (NCO)
    #: which mixes the frequency of the in-phase and quadrature 
    #: signals. If ``high_lo == True``, then mix by 10.7 Mhz; 
    #: otherwise, mix by -10.7 Mhz. The intermediate frequency 
    #: domain is defined by the hardware filters on the quad 
    #: board. When mixed by the PLL, the frequency domain of the 
    #: preamp signal should fall in this range. If ``high_lo`` is
    #: ``False``, then the sign of if domain is switched. (?) 
    #: (See :func:`backend.lo_calc`.)
    high_lo = False 

    #: Receiver tuning groups of type :class:`qraat.rmg.params.tuning`. 
    tunings = [] 

    def __init__(self, path, num_bands = 1):

      #: The bandwidth of the digital signal produced by the USRP is 
      #: divided into bands. A pulse detector is instantiated for 
      #: each of these bands. 
      self.num_bands = num_bands
      
      self.transmitters = qraat.csv(path) #: Transmitter data.
      print 'Transmitters from {0}'.format(path)
    
      for tx in self.transmitters.table: 
        if tx.use in ['Y', 'y', 'yes', 'Yes', 'YES']: 
          tx.use = True
        else:
          tx.use = False 
        tx.frequency = float(tx.frequency) 
        tx.pulse_width = float(tx.pulse_width) 
        tx.rise_trigger = float(tx.rise_trigger) 
        tx.fall_trigger = float(tx.fall_trigger) 
        tx.filter_alpha = float(tx.filter_alpha) 
        tx.type = tx_type[tx.type.lower()]
      
      self.lo_calc()
      self.backend_calc()
        
    def add_tuning(self, cf = 0.0, lo1 = 0.0):
      """ Add tuning. """ 
      self.tunings.append(tuning(self, cf, lo1))

    def __str__(self):
      """ Print tuning parameters to console. """ 
      be_str = ("Number of Frequency Bands in Filterbank: {0:d}\nBandwidth:"
                "{1:.3f} kHz\nNumber of Tunings: {2:d}").format(
        self.num_bands, self.bw/1000.0, len(self.tunings))
      for tuning in self.tunings:
        be_str += '\n' + str(tuning)
      return be_str


    def lo_calc(self):
      """ Decide whether to use high lo or low lo. Set :data:`backend.high_lo`. """ 

      self.if_min = self.lo2 - (self.if2_cf + self.if2_bw/2.0)
      if self.if_min > self.if1_cf + self.if1_bw/2.0:
        self.if_min = self.if1_cf + self.if1_bw/2.0
      self.if_max = self.lo2 - (self.if2_cf - self.if2_bw/2.0)
      if self.if_max < self.if1_cf - self.if1_bw/2.0:
        self.if_max = self.if1_cf - self.if1_bw/2.0

      actual_pv_min = self.pv_min + self.pv_offset
      actual_pv_max = self.pv_max + self.pv_offset

      self.high_lo = False if self.pa_min > self.if_max + actual_pv_min else True
      
      bandwidth = self.if_max - self.if_min 

      #: Decimation factor for the USRP. This parameter controls the rate 
      #: at which the uhd source block produces samples. Default is 250. 
      #: usrp_sampling_rate (64 Ms/sec) / decim (250) = 256 Ks/sec.
      self.decim = math.floor(usrp_sampling_rate / (self.num_bands/(self.num_bands-(1-self.num_bands % 2))*bandwidth))
      if self.decim > usrp_max_decimation:
        self.decim = usrp_max_decimation
      
      #: Width of each band in s/sec. 
      self.bw = usrp_sampling_rate / self.decim / self.num_bands
      
      print ("USRP Rate: {3}\nDecimation Factor: {1}\nNumber of Bands:"
             "{2}\nBandwidth: {0}").format(
        self.bw, self.decim, self.num_bands, usrp_sampling_rate)
        
        

    def backend_calc(self):
        """ Calculate the smallest set of tunings to record all transmitters. 

          Instance of the set cover problem (NP-hard). **TODO:** what's the solution(?) 
        """

        #make list of transmitter frequencies
        num_freqs = len(self.transmitters)
        list_of_tx_freqs = []#list of frequencys
        dict_of_tunings_per_freq = dict()#dictionary of sets of tunings for a given frequency
        set_of_needed_tunings = set()#list of tunings to get all the transmitters
        data_index = []
        for j in range(num_freqs):
            if self.transmitters[j].use:
                curr_freq = int(self.transmitters[j].frequency*1000000)
                list_of_tx_freqs.append(curr_freq)
                data_index.append(j)

        #Calculate all tunings which will receive at least one transmitter
        for freq in list_of_tx_freqs:
            if not self.high_lo:
                #Using Low LO, high_lo = False 
                max_tune = freq - self.if_min - self.pv_offset
                min_tune = freq - self.if_max - self.pv_offset
        
                if max_tune > self.pv_max:
                    max_tune = self.pv_max
                if min_tune < self.pv_min:
                    min_tune = self.pv_min


            else:
                #Using High LO, high_lo = True
                max_tune = freq + self.if_max - self.pv_offset
                min_tune = freq + self.if_min - self.pv_offset
                if max_tune > self.pv_max:
                    max_tune = self.pv_max
                if min_tune < self.pv_min:
                    min_tune = self.pv_min

            min_steps = int(math.ceil(min_tune/self.pv_step))
            max_steps = (int(math.floor(max_tune/self.pv_step)))
            tuning_range = range(min_steps, max_steps +1)

            if self.num_bands > 1:
            #check that tx isn't on filter edge
                tr_cp = list(tuning_range)#so I can remove bad values and still iterate over the whole thing
                for t in tr_cp:
                    base_freq = ((t*self.pv_step - freq) % self.bw)
                    if (base_freq > self.bw*7/16) and (base_freq < self.bw*9/16):
                        tuning_range.remove(t)
            dict_of_tunings_per_freq[freq] = set(tuning_range)
            if len(tuning_range) == 1:#only one tuning will work for this transmitter
                set_of_needed_tunings.add(tuning_range[0])
            elif len(tuning_range) == 0:
                raise ValueError("No viable tuning found for {0} Hz".format(freq))
                
        #build "set_of_all_tunings"
        set_of_all_tunings = set()
        for freq,tunings in dict_of_tunings_per_freq.iteritems():
            set_of_all_tunings.update(tunings)

        #build "dict_of_freqs_per_tuning" which maps the list of transmitters to tuning frequency
        dict_of_freqs_per_tuning = dict()
        for temp_tune in set_of_all_tunings:
            dict_of_freqs_per_tuning[temp_tune] = set()
            for freq in list_of_tx_freqs:
                if temp_tune in dict_of_tunings_per_freq[freq]:
                    dict_of_freqs_per_tuning[temp_tune].add(freq)

        #generate set of frequencies not covered by "needed tunings"
        set_of_missing_freqs = set(list_of_tx_freqs)
        for tuning in set_of_needed_tunings:
            set_of_missing_freqs.difference_update(dict_of_freqs_per_tuning[tuning])

        #Use "greedy" algorithm to add tunings to "needed tunings"
        while len(set_of_missing_freqs) > 0:
            set_of_available_tunings = set()
            for freq in set_of_missing_freqs:
                set_of_available_tunings.update(dict_of_tunings_per_freq[freq])
            max_value = 0
            max_key = None
            for tuning in set_of_available_tunings:
                l = len(dict_of_freqs_per_tuning[tuning])
                if l > max_value:
                    max_value = l
                    max_key = tuning
            set_of_needed_tunings.add(max_key)
            set_of_missing_freqs.difference_update(dict_of_freqs_per_tuning[max_key])

        #builds optimized tuning parameters
        for t in set_of_needed_tunings:#for each tuning required
            lo1 = t*self.pv_step
            #calculate tuning center frequency
            if self.high_lo:
                center_freq = lo1 + self.pv_offset - (self.lo2 - self.if2_cf)
            else:
                center_freq = lo1 + self.pv_offset + (self.lo2 - self.if2_cf)

            #initialize tuning
            self.add_tuning(center_freq, lo1)
            print "{0:.1f} MHz - RMG Center Frequency".format(center_freq/1000000.0)

            for tx_freq in dict_of_freqs_per_tuning[t]:#for each transmitter tunable
                tx_index = list_of_tx_freqs.index(tx_freq)

                #get transmitter data
                tx_data = self.transmitters[data_index[tx_index]]
                print "\t{0} {1:.3f} MHz".format(tx_data.name, tx_data.frequency)
                self.tunings[-1].add_tx(tx_data)



if __name__ == "__main__": # testing, testing ... 
  be = backend("../../build/tx.csv", 32)
