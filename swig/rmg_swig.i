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

%include "gnuradio.i" // the common stuff

%{
#include "detectmod_detect.h"
%}


GR_SWIG_BLOCK_MAGIC(detectmod,detect);
%include "detectmod_detect.h"

