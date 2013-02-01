#rmg_param.py
#Container classes for data that defines the software defined detector backend

#Todd Borrowman ECE-UIUC 02/2010

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
        self.file_prefix = directory + '/' + self.name + '_'
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
        self.file_prefix = self.file_prefix + tx_data[0] + '_'
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
        self.pa_min = 162000000
        self.pa_max = 167000000
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
    
        data = self.data

        #make list of transmitter frequencies
        num_freqs = len(data)
        freqs = []
        freq_tune = []
        data_index = []
        for j in range(num_freqs):
            if data[j][0]:
                curr_freq = int(data[j][2]*1000000)
                freqs.append(curr_freq)
                data_index.append(j)

        #make sorted list of frequencies
        s_freqs = sorted(freqs)
        max_steps = []

        #Calculate all tunings which will receive at least one transmitter
        for j in s_freqs:
            if not self.high_lo:
                #high_lo = False
                max_tune = j - self.if_min - self.pv_offset
                min_tune = j - self.if_max - self.pv_offset
        
                if max_tune > self.pv_max:
                    max_tune = self.pv_max
                if min_tune < self.pv_min:
                    min_tune = self.pv_min


            else:
                #high_lo = True
                max_tune = j + self.if_max - self.pv_offset
                min_tune = j + self.if_min - self.pv_offset
                if max_tune > self.pv_max:
                    max_tune = self.pv_max
                if min_tune < self.pv_min:
                    min_tune = self.pv_min

            min_steps = int(math.ceil(min_tune/self.pv_step))
            max_temp = (int(math.floor(max_tune/self.pv_step)))
            tuning_range = range(min_steps, max_temp +1)
            if self.num_bands > 1:
            #check that tx isn't on filter edge
                tr_cp = list(tuning_range)#so I can remove bad values and still iterate over the whole thing
                for t in tr_cp:
                    base_freq = ((t*self.pv_step - j) % self.bw)
                    if (base_freq > self.bw*7/16) and (base_freq < self.bw*9/16):
                        tuning_range.remove(t)
            freq_tune.append(set(tuning_range))
            max_steps.append(max(tuning_range))
                
        #build "inv" which maps the list of transmitters to tuning frequency
        num_freqs = len(s_freqs)
        super_set = set()
        for j in range(num_freqs):
            super_set.update(freq_tune[j])
        inv = dict()
        cp_ss = super_set.copy()
        for j in range(len(super_set)):
            temp_tune = cp_ss.pop()
            inv[temp_tune] = set()
            for k in range(num_freqs):
                if temp_tune in freq_tune[k]:
                    inv[temp_tune].add(s_freqs[k])

        #build "save_keys", the smallest amount of tunings to reach all transmitters
        save_keys = []
        f_index = 0
        found_freqs = set()
        while num_freqs > f_index:
            save_keys.append(max_steps[f_index])
            found_freqs.update(inv[max_steps[f_index]])
            f_index = len(found_freqs)
            
        #print tunings
        #print save_keys
        #for j in save_keys:
            #print inv[j]

        #builds optimized tuning parameters
        for j in save_keys:#for each tuning required
            lo1 = j*self.pv_step
            #calculate tuning center frequency
            if self.high_lo:
                center_freq = lo1 + self.pv_offset - (self.lo2 - self.if2_cf)
            else:
                center_freq = lo1 + self.pv_offset + (self.lo2 - self.if2_cf)

            #initialize tuning
            self.add_tuning(center_freq, lo1)
            print "{0:.1f} MHz - RMG Center Frequency".format(center_freq/1000000.0)

            for k in range(len(inv[j])):#for each transmitter tunable
                tx_freq = inv[j].pop()
                tx_index = freqs.index(tx_freq)

                #get transmitter data
                tx_data = data[data_index[tx_index]][1:]
                print "\t{0} {1:.3f} MHz".format(tx_data[0],tx_data[1])
                tx_data[2] = transmitter_types[tx_data[2]]
                self.add_tx(tx_data)
              


