# rmg_param.py
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

import math, csv

PULSE, CONT = range(2)#detector types used in the bands
det_type_str = ["Pulse Detector", "Raw Baseband Recording"]
transmitter_types = {"Pulse":PULSE, "Continuous":CONT, "Other":CONT}
usrp_sampling_rate = 64e6 
usrp_max_decimation = 250

class band:
#
# Data for a single band for detection
#

    def __init__(self, tx_data, band_num, band_cf, filter_length, directory):
        self.name = tx_data[0]
        self.directory = directory
        self.band_num = band_num
        self.cf = band_cf
        self.tx_type = tx_data[2]
        if (self.tx_type == PULSE):
            self.filter_length = filter_length
            self.rise = tx_data[4]
            self.fall = tx_data[5]
            self.alpha = tx_data[6]
        else:
            self.filter_length = 0
            self.rise = 0.0
            self.fall = 0.0
            self.alpha = 0.0

    def combine_tx(self, tx_data, filter_length):
        self.name = self.name + tx_data[0] + '_'
#        self.file_prefix = self.file_prefix + tx_data[0] + '_'
        if (self.tx_type != CONT):
        
            if (tx_data[2] == CONT):
                self.tx_type = CONT
            else:
                if (filter_length > self.filter_length):
                    self.filter_length = filter_length
                if (tx_data[4] < self.rise):
                    self.rise = tx_data[4]
                if (tx_data[5] > self.fall  and self.rise > tx_data[5]):
                    self.fall = tx_data[5]
                if (tx_data[6] < self.alpha):
                    self.alpha = tx_data[6]

    def __str__(self):
        if (self.tx_type == PULSE):
            band_str = "Band #: {0:d}\nBand Frequency: {1:f} MHz\n\tName: {2}\n\tType: {3}\n\tFilter Length: {4:d} samples\n\tRise: {5:.2f}, Fall: {6:.2f}, Alpha: {7:.3f}".format(self.band_num, self.cf/1000000, self.name, det_type_str[self.tx_type], self.filter_length,self.rise,self.fall,self.alpha)
        else:
            band_str = "Band #: {0:d}\nBand Frequency: {1:f} MHz\n\tName: {2}\n\tType: {3}".format(self.band_num, self.cf/1000000, self.name, det_type_str[self.tx_type])

        return band_str


class tuning:
#
# Data for a single tuning of the RMG receiver
#

    def __init__(self, backend, cf = 0.0, lo1 = 0.0):
        self.cf = cf
        self.lo1 = lo1
        self.num_possible_bands = backend.num_bands
        self.bw = backend.bw
        self.bands = []
        self.directory = backend.directory

    def add_tx(self, tx_data):

        tx_freq = tx_data[1]*1000000.0
        baseband_freq = tx_freq - self.cf
        baseband_band_num = round(baseband_freq/self.bw)
        if (baseband_band_num >=0):
            band_num = int(baseband_band_num)
        else:
            band_num = int(self.num_possible_bands + baseband_band_num)
        filter_length = int(round(tx_data[3]*self.bw/1000))
        #check if already a tx on this band
        for c in self.bands:
            if (c.band_num == band_num):
                c.combine_tx(tx_data, filter_length)
                return

        band_cf = baseband_band_num*self.bw+self.cf
        self.bands.append(band(tx_data, band_num, band_cf, filter_length, self.directory))

    def __str__(self):

        be_str = "Center Frequency: {0:.1f} MHz\nPLL Frequency: {1:.1f} MHz\nNumber of Occupied Bands: {2:d}".format(self.cf/1000000.0, self.lo1/1000000.0, len(self.bands))
        for j in self.bands:
            be_str += '\n' + str(j)
        return be_str



class backend:
#
# Top level RMG parameters (backend tunings, high_lo, decim)
# calculate tuning  
#
    def __init__(self, path, num_bands = 1, directory = "./det_files"):
    #
    # Load a list of transmitters from a .csv file. This is for modifying 
    # the list of transmitters.  Chris ~18 Sep 2012
    #
        self.num_bands = num_bands
        self.directory = directory
        if self.directory[-1] == "/":
            self.directory = self.directory[:-1]
        self.num_tunings = 0
        self.tunings = []
    
        #hardcoded RF parameters
        self.pa_min = 148000000
        self.pa_max = 178000000
        self.if1_cf = 70000000
        self.if1_bw = 500000
        self.if2_cf = 10700000
        self.if2_bw = 250000
        self.lo2 = 80700000
        self.pv_min = 218500000
        self.pv_max = 248000000
        self.pv_step = 100000
        self.pv_offset = 0#pv_tune + pv_offset = actual frequency output of the pll

        self.__lo_calc()
        self.data = []
        
        inf = open(path, 'rb')
        transmitters = csv.reader(inf, delimiter = ",", quotechar='"') 
        cols  = transmitters.next() # first row is header
        index = dict( [(cols[i], i) for i in range(len(cols))] ) 
        print 'Transmitters from {0}'.format(path)
        for tx in transmitters:
            if tx[index['use']] in ['Y', 'y', 'yes', 'Yes', 'YES']: 
                tx[index['use']] = True
            else:
                tx[index['use']] = False
          
            tx[index['freq']] = float(tx[index['freq']])
            tx[index['pulse_width']] = float(tx[index['pulse_width']])
            tx[index['rise_trigger']] = float(tx[index['rise_trigger']])
            tx[index['fall_trigger']] = float(tx[index['fall_trigger']])
            tx[index['filter_alpha']] = float(tx[index['filter_alpha']])
            self.data.append( tx )

        self.__backend_calc()
        
    def add_tuning(self, cf = 0.0, lo1 = 0.0):
        self.tunings.append(tuning(self, cf, lo1))
        self.num_tunings += 1

    def add_tx(self, tx_data, tuning_index = -1):
        self.tunings[tuning_index].add_tx(tx_data)

    def __str__(self):
        be_str = "Number of Frequency Bands in Filterbank: {0:d}\nBandwidth: {1:.3f} kHz\nNumber of Tunings: {2:d}".format(self.num_bands, self.bw/1000.0, self.num_tunings)
        for j in range(self.num_tunings):
            be_str += '\n' + str(self.tunings[j])
        return be_str


    def __lo_calc(self):

        self.if_max = self.lo2 - (self.if2_cf - self.if2_bw/2.0)
        if self.if_max > self.if1_cf + self.if1_bw/2.0:
            self.if_max = self.if1_cf + self.if1_bw/2.0
        self.if_min = self.lo2 - (self.if2_cf + self.if2_bw/2.0)
        if self.if_min > self.if1_cf + self.if1_bw/2.0:
            self.if_min = self.if1_cf + self.if1_bw/2.0

        actual_pv_min = self.pv_min + self.pv_offset
        actual_pv_max = self.pv_max + self.pv_offset

        self.high_lo = True
        if self.pa_min > self.if_max + actual_pv_min:
            self.high_lo = False
        
        bandwidth = self.if_max - self.if_min
        decim = math.floor(usrp_sampling_rate / (self.num_bands/(self.num_bands-(1-self.num_bands % 2))*bandwidth))
        if decim > usrp_max_decimation:
            decim = usrp_max_decimation
        self.bw = usrp_sampling_rate / decim / self.num_bands
        self.decim = decim

        print "USRP Rate: {3}\nDecimation Factor: {1}\nNumber of Bands: {2}\nBandwidth: {0}".format(self.bw, self.decim, self.num_bands, usrp_sampling_rate)
        
        

    def __backend_calc(self):
        #Calculates the smallest set of tunings to record all transmitters
        #this is a "set covering optimization problem", NP-hard

        data = self.data

        #make list of transmitter frequencies
        num_freqs = len(data)
        list_of_tx_freqs = []#list of frequencys
        dict_of_tunings_per_freq = dict()#dictionary of sets of tunings for a given frequency
        set_of_needed_tunings = set()#list of tunings to get all the transmitters
        data_index = []
        for j in range(num_freqs):
            if data[j][0]:
                curr_freq = int(data[j][2]*1000000)
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
        for tuning in set_of_needed_tunings:#for each tuning required
            lo1 = tuning*self.pv_step
            #calculate tuning center frequency
            if self.high_lo:
                center_freq = lo1 + self.pv_offset - (self.lo2 - self.if2_cf)
            else:
                center_freq = lo1 + self.pv_offset + (self.lo2 - self.if2_cf)

            #initialize tuning
            self.add_tuning(center_freq, lo1)
            print "{0:.1f} MHz - RMG Center Frequency".format(center_freq/1000000.0)

            for tx_freq in dict_of_freqs_per_tuning[tuning]:#for each transmitter tunable
                tx_index = list_of_tx_freqs.index(tx_freq)

                #get transmitter data
                tx_data = data[data_index[tx_index]][1:]
                print "\t{0} {1:.3f} MHz".format(tx_data[0],tx_data[1])
                tx_data[2] = transmitter_types[tx_data[2]]
                self.add_tx(tx_data)

