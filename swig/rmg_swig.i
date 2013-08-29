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
#include "pulse_data.h"
%}


GR_SWIG_BLOCK_MAGIC(detectmod,detect);
%include "detectmod_detect.h"


/* param_t */

typedef struct {
  int channel_ct,
      sample_ct,
      pulse_sample_ct,
      pulse_index;
  float sample_rate, 
        ctr_freq;
  int t_sec, t_usec; 
  %extend{ 
    char* __str__() {
      static char tmp [256];
      time_t pulse_time = $self->t_sec + ($self->t_usec * 0.000001); 
      sprintf(tmp, 
"channel_ct     %d\n\
sample_ct        %d\n\
pulse_sample_ct %d\n\
pulse_index    %d\n\
sample_rate    %g\n\
ctr_freq       %g\n\
pulse_time     %s", 
       $self->channel_ct, $self->sample_ct, $self->pulse_sample_ct, $self->pulse_index,
       $self->sample_rate, $self->ctr_freq, asctime(gmtime(&pulse_time))
      );
      return &tmp[0];
    }
  }
} param_t; 

//%rename(sample) pulse_data::operator[] (int i);

%exception {
  try { 
    $function
  } catch ( PulseDataError e ) {
    switch(e) {
      case FileReadError: 
        SWIG_exception(SWIG_RuntimeError,"file doesn't exist or doesn't contain pulse data"); break;
      case NoDataError:
        SWIG_exception(SWIG_RuntimeError,"no data read yet"); break;
      case IndexError: 
        SWIG_exception(SWIG_RuntimeError,"index out of range!"); break;
      default: cout << "unknown";
    }
    return 0;
  } 
}

/* pulse_data */

class pulse_data {
friend class detectmod_detect; 

  fstream det; 
  param_t params; 
  sample_t prev; 
  gr_complex *data;
  char *filename;

public:
  
  pulse_data (const char *fn=NULL); // throw PulseDataErr
  pulse_data (
    int channel_ct, 
    int sample_ct,
    int pulse_sample_ct,
    float sample_rate,
    float ctr_freq
  ); 
  ~pulse_data ();

  /* file io */
  int read(const char *fn); 
  int write(const char *fn="");

  /* accessors - throw PulseDataErr */
  const param_t& param(); 
  float imag(int i);
  float real(int i); 
  void set_imag(int i, float val);
  void set_real(int i, float val);

};
