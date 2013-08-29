/* pulse_data.h
 * Data structure for .det files. This file is part of QRAAT, an automated 
 * animal tracking system based on GNU Radio. 
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

#ifndef pulse_data_h
#define pulse_data_h

#include <rmg_api.h>
#include <iostream> 
#include <fstream> 
#include <sys/time.h>
#include <ctime>
#include <gr_complex.h>

using namespace std;

typedef enum { FileReadError, NoDataError, IndexError } PulseDataError; 

/* parameters */
typedef struct {
  int channel_ct,
      data_ct,
      filter_data_ct,
      pulse_index;
  float sample_rate, 
        ctr_freq;
  //time_t pulse_time;
  //struct timeval pulse_time;
  int t_sec, t_usec; 
} param_t; 

ostream& operator<< ( ostream &out, const param_t &p );

class detectmod_detect;

class RMG_API pulse_data {
friend class detectmod_detect; 

  fstream det; 
  param_t params; 
  gr_complex *data;
  char *filename;
  
    /* circ_buffer */
  int index;

public:
  
  pulse_data (const char *fn=NULL); // throw PulseDataErr
  ~pulse_data ();

  /* file io */
  int read(const char *fn); 
  int write(const char *fn="");

  /* accessors - throw PulseDataErr */
  const param_t& param() const; 
  gr_complex& operator[] (int i); 

  float real(int i); 
  float imag(int i); 
  void set_real(int i, float val);
  void set_imag(int i, float val);

     /* circ_buffer */
  pulse_data(
   int channel_ct,
   int data_ct,
   int filter_data_ct,
   float sample_rate, 
   float ctr_freq
  );

  pulse_data(const pulse_data &det);
  pulse_data& operator=(const pulse_data &det);
  void add(gr_complex *in);
  int get_index();
  gr_complex *get_buffer();
  gr_complex *get_sample();
  void inc_index();

};

#endif
