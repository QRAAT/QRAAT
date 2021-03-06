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

from qraat.pulse_data import pulse_data

tag_regex = re.compile("([^/]*)_[0-9]*\.det$")

class det (pulse_data):
  
  """ 
  
    Encapsulation of pulse records (.det files), the output of the pulse detector. 
    In addition to storing the pulse metadata and samples, this class 
    performs the various calculations that characterize the recorded 
    samples in signal space. This class is based on 
    :class:`qraat.pulse_swig.pulse_data`, which is used directly by 
    the pulse detector (:class:`qraat.rmg.detect`) for storage and 
    writing to disk. This allows us to handle metadata uniformly 
    across the API. 

  :param filename: The name of the .det file. 
  :type filename: string
  """
   
  def __init__(self, fn):
    pulse_data.__init__(self, fn)
    if self.channel_ct==0:
      raise IOError("pulse_data failed to read det file")
    self.f = None              #: Result of :func:`det.fft`. 
    self.f_sig = None          #: Result of :func:`det.f_signal`.
    self.e_sig = None          #: Result of :func:`det.eig`. 
    self.eigenvalues = None    #: See :func:`det.eig`. 
    self.eigenvectors = None   #: See :func:`det.eig`. 
    self.n_cov = None          #: Result of :func:`det.noise_cov`. 
    self.tag_name = ""         #: Tag name parsed from input file name. 
    self.fn = fn 
    self.data = np.zeros((self.sample_ct,self.channel_ct),np.complex)
    for j in range(self.sample_ct):
      for k in range(self.channel_ct):
        r = self.r_sample(k,j)
        i = self.i_sample(k,j)
        self.data[j,k] = np.complex(r,i)
    if np.any(np.isnan(self.data)):
      raise IOError("NaN in det data")#bad data samples
    self.pulse = self.data[self.pulse_index:self.pulse_index+self.pulse_sample_ct,:]
    self.time = self.t_sec + (self.t_usec * 1e-6)
    m = tag_regex.search(fn)
    if m:
      self.tag_name = m.groups()[0]


  def __str__(self):
    """ Return the filename as a string. """
    return self.filename

  
  @classmethod
  def read_dir(cls, base_dir): 
    """ Return a list of det instances from readable files in base_dir
        and a list of file names of un-readable files. 

      :param base_dir: Root directory for det files. 
      :type base_dir: str
      :rtype: :class:`qraat.det.det.det` list

    """
    files = os.listdir(base_dir)
    files.sort()
    det_list = []
    bad_file_list = []
    for fn in files:
      file_path = os.path.join(base_dir,fn)
      try:
        det_list.append(cls(file_path))
      except:
        import sys
        print >>sys.stderr, "Couldn't read det file: {}".format(file_path)
        bad_file_list.append(file_path)
    return det_list, bad_file_list
  

  def fft(self):
    """ Performs an fft on pulse data. 
          
      Saves result as instance attribute f.

    :returns: result of fft calculation
    """
    if self.f is None:
      self.f = np.zeros((self.pulse_sample_ct,self.channel_ct),np.complex)
      for j in range(self.channel_ct):
        self.f[:,j] = np.fft.fft(self.pulse[:,j])
    return self.f


  def f_signal(self):
    """ Calculate pulse paramters based on Fourier Analysis. 
        **TODO:** description of paramters(?)
    
    :returns: parameters
    :rtype: (?)
    """
    if self.f is None: self.fft()
    
    if self.f_sig is None: 
      bin_width = self.sample_rate/self.pulse_sample_ct
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
      if freq_index >= self.pulse_sample_ct/2:
        freq = freq - self.sample_rate
      self.freq = freq + self.ctr_freq

      #total received power in bin with peak
      self.f_pwr = np.abs(f_pwr[freq_index])*bin_width

    return self.f_sig


  def eig(self):
    """ Calculate the eigenvalue decomposition of pulse covariance. 
    
    :rtype: (?) 
    """

    if self.e_sig is None:
      pulse_ct = self.pulse.conjugate().transpose()
      sq = np.dot(pulse_ct,self.pulse)
      (self.eigenvalues, self.eigenvectors) = np.linalg.eigh(sq)
        
      #column vector of eigenvectors, complex signal vector
      self.e_sig = self.eigenvectors[:,(self.eigenvalues == np.amax(self.eigenvalues))]

      #total received power
      self.e_pwr = np.max(self.eigenvalues)/self.pulse_sample_ct*self.sample_rate

      #confidence measure, ratio of signal eigenvalue to total power
      self.e_conf = np.max(self.eigenvalues)/np.sum(self.eigenvalues)
    return self.e_sig


  def noise_cov(self):
    """ Calculate the noise covariance from front of data with some size as the pulse. 
    
    :rtype: (?) 
    """

    if self.n_cov is None:
      if self.sample_ct - self.pulse_index >= self.pulse_sample_ct:
        noise_start = int(self.sample_ct - self.pulse_index - self.pulse_sample_ct)/2
        noise = self.data[noise_start:noise_start+self.pulse_sample_ct,:]
        noise_ct = noise.conjugate().transpose()
        self.n_cov = np.dot(noise_ct,noise)/self.pulse_sample_ct*self.sample_rate
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
