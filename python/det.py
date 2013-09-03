# det.py - Python encapsulation for .det files. This file is part 
# of QRAAT, an automated animal tracking system based on GNU Radio. 
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

import numpy as np
import os, time, re

from pulse_swig import pulse_data, param_t

tag_regex = re.compile("([^/]*)_[0-9]*\.det$")

class det (pulse_data):
  
  """ Encapsulation of .det files, the output of the pulse detector. 

    This class also has some math on the signal (desc). **TODO**: 
    This class should be extended to interface with the database 
    as well. 

  :param filename: The name of the .det file. 
  :type filename: string
  """

  f = None              #: Result of :func:`det.fft`. 
  f_sig = None          #: Result of :func:`det.f_signal`.
  e_sig = None          #: Result of :func:`det.eig`. 
  eigenvalues = None    #: See :func:`det.eig`. 
  eigenvectors = None   #: See :func:`det.eig`. 
  n_cov = None          #: Result of :func:`det.noise_cov`. 
  tag_name = ""         #: Tag name parsed from input file name. 
 
  def __init__(self, fn):
    pulse_data.__init__(self, fn)
    self.data = np.zeros((self.params.sample_ct,self.params.channel_ct),np.complex)
    for j in range(self.params.sample_ct):
      for k in range(self.params.channel_ct):
        (r, i) = self.sample((j * self.params.channel_ct) + k)
        self.data[j,k] = np.complex(r,i)
    self.pulse = self.data[self.params.pulse_index:self.params.pulse_index+self.params.pulse_sample_ct,:]
    self.time = self.params.t_sec + (self.params.t_usec * 1e-6)
    m = tag_regex.search(fn)
    if m:
      self.tag_name = m.groups()[0]


  def __str__(self):
    """ Return the filename as a string. """
    return self.filename


  def print_det(self):
    """ Print the record's metdata to standard output. """
    print self.params

  
  @classmethod
  def read_many(i, j, base_dir): 
    """ Return a set of det instances over time interval ``(i, j)``. 

      :param i: Interval start
      :type i: datetime.datetime
      :param j: Interval end
      :type j: datetime.datetime
      :param base_dir: Root directory for det files. 
      :type base_dir: str
      :rtype: det list

    """
    return [] #TODO


  def fft(self):
    """ Performs an fft on pulse data. 
          
      Saves result as instance attribute f.

    :returns: result of fft calculation
    """
    if not self.f:
      self.f = np.zeros((self.params.pulse_sample_ct,self.params.channel_ct),np.complex)
      for j in range(self.params.channel_ct):
        self.f[:,j] = np.fft.fft(self.pulse[:,j])
    return self.f


  def f_signal(self):
    """ Calculate pulse paramters based on Fourier Analysis. 
        **TODO:** description of paramters(?)
    
    :returns: parameters
    :rtype: (?)
    """
    if not self.f: self.fft()
    
    if not self.f_sig: 
      bin_width = self.params.sample_rate/self.params.pulse_sample_ct
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
      if freq_index >= self.params.pulse_sample_ct/2:
        freq = freq - self.params.sample_rate
      self.freq = freq + self.params.ctr_freq

      #total received power in bin with peak
      self.f_pwr = np.abs(f_pwr[freq_index])*bin_width

    return self.f_sig


  def eig(self):
    """ Calculate the eigenvalue decomposition of pulse covariance. 
    
    :rtype: (?) 
    """

    if not self.e_sig:
      pulse_ct = self.pulse.conjugate().transpose()
      sq = np.dot(pulse_ct,self.pulse)
      (self.eigenvalues, self.eigenvectors) = np.linalg.eigh(sq)
        
      #column vector of eigenvectors, complex signal vector
      self.e_sig = self.eigenvectors[:,(self.eigenvalues == np.amax(self.eigenvalues))]

      #total received power
      self.e_pwr = np.max(self.eigenvalues)/self.params.pulse_sample_ct*self.params.sample_rate

      #confidence measure, ratio of signal eigenvalue to total power
      self.e_conf = np.max(self.eigenvalues)/np.sum(self.eigenvalues)
    return self.e_sig


  def noise_cov(self):
    """ Calculate the noise covariance from front of data with some size as the pulse. 
    
    :rtype: (?) 
    """

    if not self.n_cov:
      if self.params.sample_ct - self.params.pulse_index >= self.params.pulse_sample_ct:
        noise_start = int(self.params.sample_ct - self.params.pulse_index - self.params.pulse_sample_ct)/2
        noise = self.data[noise_start:noise_start+self.params.pulse_sample_ct,:]
        noise_ct = noise.conjugate().transpose()
        self.n_cov = np.dot(noise_ct,noise)/self.params.pulse_sample_ct*self.params.sample_rate
      else:
        self.n_cov = np.array([[]])
    return self.n_cov


#testing stuff
if __name__ == '__main__':
    df = det('test.det')
    #df.fft()
    #import matplotlib.pyplot as pp
    #pp.plot(abs(df.f))
    #pp.show()
    df.eig()
    print abs(df.eigenvalues)
    print abs(df.eigenvectors)
    
    temp = np.sum(df.signal*df.signal.conjugate())
    #print abs(np.linalg.pinv(df.signal.reshape(4,1)/np.sqrt(temp)))
    print abs((df.signal.reshape(4,1)/np.sqrt(temp)))
