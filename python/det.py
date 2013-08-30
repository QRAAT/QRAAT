# det_file.py - Python encapsulation for .det files. This file is part 
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
import os
import time

from pulse_swig import pulse_data, param_t


class det (pulse_data):
  def __str__(self):
    """ Return the filename as a string. """
    return self.filename

  def print_det(self):
    """ Print the record's metdata to standard output. """
    print self.param()

  def dumb(self):
    print self.data[2]



class det_file():
    """ Encapsulation of .det files, the output of the pulse detector. 

      This class also has some math on the signal (desc). **TODO**: 
      This class should be extended to interface with the database 
      as well. 

    :param filename: The name of the .det file. 
    :type filename: string
    """

    #: Result of pulse data's fast fourier transform. (See :func:`det_file.fft`.)
    f = None 

    def __init__(self, filename):

        self.null_file = True #flag if the file has data or not
        if filename[-4:] == ".det":#check if the file is a .det file
            try:
                filesize = os.path.getsize(filename)
            except OSError:
                filesize = 0
            if filesize >= 4*8:#check that the file has more than just the header
                with open(filename,'r+b') as f:
                    #read header info
                    self.filename = filename
                    tagname_index = filename.rfind('/')
                    tagname_last_index = filename.rfind('_')
                    self.tag_name = filename[tagname_index+1:tagname_last_index]
                    self.num_ch = struct.unpack('i',f.read(4))[0]
                    self.data_length = struct.unpack('i',f.read(4))[0]
                    self.acc_length = struct.unpack('i',f.read(4))[0]
                    self.pulse_start = struct.unpack('i',f.read(4))[0]
                    self.sampling_rate = struct.unpack('f',f.read(4))[0]
                    self.center_freq = struct.unpack('f',f.read(4))[0]
                    self.time = struct.unpack('i',f.read(4))[0] + struct.unpack('i',f.read(4))[0]*1e-6

                    #read data
                    if filesize - 32 >= self.num_ch*self.data_length*2*4:
                        self.data = np.zeros((self.data_length,self.num_ch),np.complex)
                        for j in range(self.data_length):
                            for k in range(self.num_ch):
                                r = struct.unpack('f',f.read(4))[0]
                                i = struct.unpack('f',f.read(4))[0]
                                self.data[j,k] = np.complex(r,i)
                        self.pulse = self.data[self.pulse_start:self.pulse_start+self.acc_length,:]
                        self.null_file = False

    def __str__(self):
        """ Return the filename as a string. """
        return self.filename

    def print_det(self):
        """ Print the record's metdata to standard output. """

        print "File: {0}".format(self.filename)
        print "Date: {0}".format(time.strftime('%d-%m-%Y %H:%M:%S', time.gmtime(self.time)))
        print "Center Frequency: {0} Hz".format(self.center_freq)
        print "Sampling Rate: {0} Samples per Second".format(self.sampling_rate)
        print "Number of channels: {0}".format(self.num_ch)
        print "Data Length: {0}".format(self.data_length)
        print "Pulse Length: {0}".format(self.acc_length)

    def fft(self):
        """ Performs an fft on pulse data. 
              
              Saves result as instance attribute f.

        :returns: result of fft calculation
        """
        if not hasattr(self,'f'):
            self.f = np.zeros((self.acc_length,self.num_ch),np.complex)
            for j in range(self.num_ch):
                self.f[:,j] = np.fft.fft(self.pulse[:,j])

        return self.f

    def f_signal(self):
        """ Calculate pulse paramters based on Fourier Analysis. 
            **TODO:** description of paramters(?)
        
        :returns: parameters
        :rtype: (?)
        """

        if not hasattr(self,'f'):
            self.fft()
        if not hasattr(self,'f_sig'):
            bin_width = self.sampling_rate/self.acc_length
            f_pwr = np.sum(self.f*self.f.conjugate(),axis = 1)
            freq_index = np.argmax(f_pwr)

            #complex signal vector
            self.f_sig = self.f[freq_index,:][:,np.newaxis]/np.sqrt(f_pwr[freq_index])

            #3dB pulse bandwidth
            self.f_bandwidth3 = np.sum(f_pwr > f_pwr[freq_index]/2)*bin_width

            #10dB pulse bandwidth
            self.f_bandwidth10 = np.sum(f_pwr > f_pwr[freq_index]/10)*bin_width

            #frequency of peak
            freq = freq_index*bin_width
            if freq_index >= self.acc_length/2:
                freq = freq - self.sampling_rate
            self.freq = freq + self.center_freq

            #total received power in bin with peak
            self.f_pwr = np.abs(f_pwr[freq_index])*bin_width

        return self.f_sig

    def eig(self):
        """ Calculate the eigenvalue decomposition of pulse covariance. 
        
        :rtype: (?) 
        """

        if not hasattr(self,'eigenvalues'):
            pulse_ct = self.pulse.conjugate().transpose()
            sq = np.dot(pulse_ct,self.pulse)
            (self.eigenvalues, self.eigenvectors) = np.linalg.eigh(sq)
            
            #column vector of eigenvectors, complex signal vector
            self.e_sig = self.eigenvectors[:,(self.eigenvalues == np.amax(self.eigenvalues))]

            #total received power
            self.e_pwr = np.max(self.eigenvalues)/self.acc_length*self.sampling_rate

            #confidence measure, ratio of signal eigenvalue to total power
            self.e_conf = np.max(self.eigenvalues)/np.sum(self.eigenvalues)
        return self.e_sig

    #calculates noise covariance from front of data with same size as the pulse
    def noise_cov(self):
        """ Calculate the noise covariance from front of data with some size as the pulse. 
        
        :rtype: (?) 
        """

        if not hasattr(self,'n_cov'):
            if self.data_length - self.pulse_start >= self.acc_length:
                noise_start = int(self.data_length - self.pulse_start - self.acc_length)/2
                noise = self.data[noise_start:noise_start+self.acc_length,:]
                noise_ct = noise.conjugate().transpose()
                self.n_cov = np.dot(noise_ct,noise)/self.acc_length*self.sampling_rate
            else:
                self.n_cov = np.array([[]])
        return self.n_cov


#testing stuff
if __name__ == '__main__':
    df = det_file('test.det')
    #df.fft()
    #import matplotlib.pyplot as pp
    #pp.plot(abs(df.f))
    #pp.show()
    df.eig()
    df.get_signal()
    print abs(df.eigenvalues)
    print abs(df.eigenvectors)
    
    temp = np.sum(df.signal*df.signal.conjugate())
    #print abs(np.linalg.pinv(df.signal.reshape(4,1)/np.sqrt(temp)))
    print abs((df.signal.reshape(4,1)/np.sqrt(temp)))
