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

%module(docstring="""
  ``pulse_data`` is a class used by the pulse detector for data storage and 
  for writing pulse records out to disk. It's also the parent class :mod:`qraat.det.det`. 
""") pulse_data

%{
#include "../include/pulse_data.h"
%}

%include "../include/pulse_data.h"

/* Doesn't work!!
%exception {
  try { 
    $function
  } catch ( PulseDataError e ) {
    switch(e) {
      case FileReadError: 
        PyErr_SetString(PyExc_RuntimeError, "file doesn't exist or doesn't contain pulse data"); break;
      case NoDataError:
        PyErr_SetString(PyExc_RuntimeError, "no data read yet"); break;
      case IndexError: 
        PyErr_SetString(PyExc_RuntimeError, "index out of range"); break;
      default: std::cout << "unknown";
    }
    return 0;
  } 
}
*/

//%rename(index_operator) operator[](const int i);
%extend pulse_data {
  float r_sample(int c, int i) {
    return $self->get_sample(c,i).real();
  }
  float i_sample(int c, int i) {
    return $self->get_sample(c,i).imag();
  }
};


/* Map my_complex to a Python tuple, (real, imag) */
/* Doesn't work!!
%typemap(out) my_complex * {
  $result = PyTuple_New(2);
  PyObject *r = PyFloat_FromDouble((double) $1->real()); 
  PyObject *i = PyFloat_FromDouble((double) $1->imag()); 
  PyTuple_SetItem($result, 0, r);
  PyTuple_SetItem($result, 1, i);
}

%typemap(out) my_complex {
  $result = PyTuple_New(2);
  PyObject *r = PyFloat_FromDouble((double) $1.real()); 
  PyObject *i = PyFloat_FromDouble((double) $1.imag()); 
  PyTuple_SetItem($result, 0, r);
  PyTuple_SetItem($result, 1, i);
}
*/

