# pic_interface.py
# Communication with the PIC interace on the RMG, developed at UIUC-ECE. 
# This file is part of QRAAT, an automated animal tracking system based 
# on GNU Radio. 
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

import serial
import time

lo_str = ['No Calc', 'High LO', 'Low LO']

class pic_interface:
  """ Communication with the PIC interface for the RMG, developed at UUIC-ECE. 

          The PIC controls various tuning parameters for the RMG hardware, the most 
          important of these being PLL frequency. See :class:`qraat.rmg.params.backend`.  

        :param port: Serial device file, e.g */dev/ttyS0*, */dev/ttyUSB0*.
        :type port: string
        """

  def __init__(self, port = '/dev/ttyS0'):
    self.ser = serial.Serial(port, timeout = 1)  #open serial port
    print "Serial port: %s" % (self.ser.portstr,)       #check which port was realy used
    self.lo = -1
    self._read()

  def tune(self, freq):
    """ Set center frequency at *freq* Hz. """
    if (freq != 0):
      self.ser.write("f")
      time.sleep(.05)
      self.ser.write("%d\r" %(freq,))
      time.sleep(.05)
    self.ser.read(len('%d' %(freq,)))
    #return self.check(freq)

  def _read(self):
    """ Read PLL information. """
    self._flush_buffer()
    self.ser.write('/')
    output = self.ser.readline()
    try:
      self.freq = int(output[2:12],16)
    except ValueError:
      raise IOError, "No serial connection with RMG"
    strw = output[80]
    if (strw == 'Y'):
      self.w = True
    else:
      self.w = False
    strlock = output[84:]
    if (strw == "LOCKED", chr(13), chr(10)):
      self.lock = True
    else:
      self.lock = False

  def load(self):
    """ Load PIC firmware variables from EEPROM. """
    self.ser.write('l')
    time.sleep(.1)

  def save(self):
    """ Saves PIC firmware variables to EEPROM. """
    self.ser.write('s')
    time.sleep(.1)

    def reset_pic(self):
      """ Reset the PIC< wait a few seconds to come back up. """
      self.ser.write('0')
      time.sleep(1.5)

    def change_contrast(self, t):
      """ Change the contrast of the LCD. """
      if t > 0 and t < 10:
        self.ser.write('t')
        time.sleep(.05)
        setting = '%d\r' % (t,)
        self.ser.write(setting)
      else:
        raise ValueError

    def lcd_print(self, string, row = 1, col = 1):
      """ Print a string to the LCD. """
      self.ser.write('p')
      time.sleep(.05)
      self.ser.write('%d\r' %(row, ))
      self.ser.write('%d\r' %(col, ))
      self.ser.write('%s\r' %(string, ))

    def inc_freq(self):
      """ Increment the PLL frequency by one step. """
      self.ser.write('+')
      time.sleep(.1)

    def dec_freq(self):
      """ Decrement the PLL frequency by one step. """
      self.ser.write('-')
      time.sleep(.1)

    def use_high_lo(self):
      """ Set LCD to display frequency based on High LO. """ 
      self._change_lo(1)

    def use_low_lo(self):
      """ Set LCD to display frequency based on Low LO. """ 
      self._change_lo(2)

    def use_no_lo(self):
      """ Set LCD to display frequency of the PLL. """ 
      self._change_lo(0)

    def _change_lo(self, n):
      """ Do the change in display frequency calculation """ 
      self.ser.write('a')
      time.sleep(.8)
      self.ser.write('o')
      time.sleep(.05)
      self.ser.write('%d\r' %(n,))
      time.sleep(.05)
      self.ser.write('a')
      time.sleep(.8)
      self.lo = n
      self._flush_buffer()

    def _flush_buffer(self):
      """ Flush the read buffer of the serial connection. 
               
          This relies on the timeout argument. 
          """
      buff = self.ser.readline()
      while not buff == '':
        buff = self.ser.readline()

    def __del__(self):
      """ Close the serial connection. """
      self.ser.close()

    def check(self, in_freq):
      """ Verify the PLL frequency. 
       
          :param in_freq: Expected frequency in Hz. 
          :type in_freq: int
          :rtype: boolean
      """
      self._read()
      out = (self.freq == in_freq) and self.w and self.lock
      return out

    def print_status(self):
      """ Print frequency to the terminal. """ 
      self._read()
      print "Frequency: {0:d} Hz, Write: {1}, Lock: {2}".format(self.freq, self.w, self.lock)

    def check_lo(self):
      """ Get the current LO display setting. """ 
      if self.lo == -1:
        self._flush_buffer()
        self.ser.write('a')
        for j in range(12):
          buff = self.ser.readline()
        result = buff[28:].rstrip()
        print result
        self.lo = lo_str.index(result)
        print self.lo
        self.ser.write('a')
        self._flush_buffer()
      return self.lo

#Test code for the module
if __name__ == "__main__":

    sc = pic_interface()
#    sc.reset_pic()
    sc.check_lo()
    sc.print_status()
    del sc


