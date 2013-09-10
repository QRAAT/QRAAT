/* -*- c++ -*- 
 * rmg_swig.i
 * Swig C++ -> Python wrapper for pulse detector. This file is part of QRAAT, 
 * an automated animal tracking system based on GNU Radio. 
 *
 * Copyright (C) 2012 Christopher Patton
 * 
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 * 
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#define RMG_API


%feature("autodoc");

%module(docstring="""
 ``detect`` is the Python interface for the GNU Radio pulse detector written in C++. 
 Technically speaking, it is a C++ routine that creates a 
 `Boost smart pointer <http://www.boost.org/doc/libs/1_54_0/libs/smart_ptr/shared_ptr.htm>`_
 to an instace of the ``detectmod_detect`` class which is then SWIG'ed into Python.
 This is the canonical way to instantiate signal processing blocks in GNU Radio; the
 C++ constructor is declared private so that it can't be used directly. In fact, 
 SWIG will only make public methods and attributes available in Python. 

 :Parameters:
   * **pulse_wdith** (*int*) -- Width of transmitter pulse in samples. 
   * **save_width** (*int*) -- Number of samples to store in pulse record. 
   * **channels** (*int*) -- Number of input channels.
   * **directory** (*char \**) -- Output directory for pulse records. 
   * **tx_name** (*char \**) -- Name of the transmitter.
   * **c_freq** (float) -- Center frequency of this band. 
   * **psd** (char) -- Flag for pulse shape discriminator. 

""") rmg_swig


%include "gnuradio.i" // the common stuff

%{
#include "detectmod_detect.h"
%}

GR_SWIG_BLOCK_MAGIC(detectmod,detect);
%include "detectmod_detect.h"

