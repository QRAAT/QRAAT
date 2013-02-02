# rmg_pic_interface.py
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

try:
    import serial
except ImportError:
    print "This module requires the installation of python-serial"
    print "To do this from the commandline:"
    print "\tsudo apt-get install python-serial"
    raise


import time

lo_str = ['No Calc', 'High LO', 'Low LO']

class rmg_pic_interface:

	def __init__(self, port = '/dev/ttyS0'):
		self.ser = serial.Serial(port, timeout = 1)  #open serial port
		print "Serial port: %s" % (self.ser.portstr,)       #check which port was realy used
                self.lo = -1
                self._read()

	#Set frequency in Hz
	def tune(self, freq):
		if (freq != 0):
			self.ser.write("f")
                	time.sleep(.05)
                	self.ser.write("%d\r" %(freq,))
                	time.sleep(.05)
			self.ser.read(len('%d' %(freq,)))
		#return self.check(freq)

	#Reads pll information
	def _read(self):
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

	#Loads pic firmware variables from EEPROM
        def load(self):
                self.ser.write('l')
                time.sleep(.1)

	#Saves pic firmware variables from EEPROM
        def save(self):
                self.ser.write('s')
                time.sleep(.1)

	#Resests the PIC, waits for it to come back up
        def reset_pic(self):
                self.ser.write('0')
                time.sleep(1.5)

	#Changes the contrast of the LCD
        def change_contrast(self, t):
                if t > 0 and t < 10:
                        self.ser.write('t')
                        time.sleep(.05)
                        setting = '%d\r' % (t,)
                        self.ser.write(setting)
		else:
			raise ValueError

	#Prints characters to the LCD
        def lcd_print(self, string, row = 1, col = 1):
                self.ser.write('p')
                time.sleep(.05)
                self.ser.write('%d\r' %(row, ))
                self.ser.write('%d\r' %(col, ))
                self.ser.write('%s\r' %(string, ))

	#Increment the frequency
        def inc_freq(self):
                self.ser.write('+')
                time.sleep(.1)

	#Decrement the frequency
        def dec_freq(self):
                self.ser.write('-')
                time.sleep(.1)

	#Sets LCD to display frequency based on High LO
        def use_high_lo(self):
                self._change_lo(1)

	#Sets LCD to display frequency based on Low LO
        def use_low_lo(self):
                self._change_lo(2)

	#Sets LCD to display frequency of the pll
        def use_no_lo(self):
                self._change_lo(0)

	#Does the clange in display
        def _change_lo(self, n):
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

	#Flushes the read buffer of the serial connection
	#This relies on the timeout arguement
        def _flush_buffer(self):
                buff = self.ser.readline()
                while not buff == '':
                    buff = self.ser.readline()

	#Closes the serial connection when the object is deleted
	def __del__(self):
		self.ser.close()

	#Determines if the pll is at the given frequency
	def check(self, in_freq):
		self._read()
		out = (self.freq == in_freq, self.w, self.lock)
		return out

	#Displays the current frequency
        def freq_check(self):
                self._read()
                if self.lock:
                        print "Frequency: %d LOCKED" % (self.freq,)
                else:
                        print "Write Status: %d, Lock Status: %d" %(self.w, self.lock)

	#Returns the current LO display setting
        def check_lo(self):
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

    sc = rmg_pic_interface()
#    sc.reset_pic()
    sc.check_lo()
    sc.freq_check()
    del sc


