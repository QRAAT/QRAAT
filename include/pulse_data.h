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
  struct timeval pulse_time;
} param_t; 

ostream& operator<< ( ostream &out, const param_t &p );

class detectmod_detect;

class RMG_API pulse_data {
friend class detectmod_detect; 

  fstream det; 
  param_t params; 
  gr_complex *data;
  char *filename;

public:
  
  pulse_data (const char *fn=NULL); // throw PulseDataErr
  ~pulse_data ();

  /* open stream for writing */
  void open(
   int channel_ct,
   int data_ct,
   int filter_data_ct,
   int pulse_index,
   float sample_rate, 
   float ctr_freq,
   struct timeval *pulse_time,
   const char *fn
  );
  
  /* write something to stream */
  void write(const char *data, int n);

  /* close stream */
  void close();

  /* file io */
  int read(const char *fn); 
  void writeout(const char *fn="");

  /* accessors - throw PulseDataErr */
  const param_t& param() const; 
  gr_complex& operator[] (int i); 

  float real(int i); 
  float imag(int i); 
  void set_real(int i, float val);
  void set_imag(int i, float val);

};

#endif
