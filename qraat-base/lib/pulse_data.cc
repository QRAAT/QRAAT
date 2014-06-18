/* pulse_data.cc 
 * Implementation of the pulse_data class. This file is part of QRAAT, 
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

#include <iostream> 
#include <iomanip>
#include <fstream>
#include <ctime>
#include <cstdio>
#include <cstring> // memcpy, strerror
#include <sys/stat.h>
#include <errno.h>

#include "pulse_data.h"

using namespace std;

ostream& operator<< ( ostream &out, const param_t &p ) {
  time_t pulse_time = p.t_sec + (p.t_usec * 0.000001);
  out << "channel_c t     " << p.channel_ct << endl;
  out << "sample_ct       " << p.sample_ct << endl;
  out << "pulse_sample_ct " << p.pulse_sample_ct << endl;
  out << "pulse_inde x    " << p.pulse_index << endl;
  out << "sample_rate     " << p.sample_rate << endl;
  out << "ctr_freq        " << p.ctr_freq << endl;
  printf("pulse_time      %s", asctime(gmtime(&pulse_time)));
  return out;
}


/**
 * class pulse_data. 
 */

pulse_data::pulse_data( const char *fn ) 
{
  data = NULL;
  filename = NULL;
  index = size = 0;  
  if( fn && read(fn)==-1 ) 
    throw FileReadError;
} // constructor for Python interface

pulse_data::pulse_data(
   int channel_ct,
   int sample_ct,
   int pulse_sample_ct,
   float sample_rate, 
   float ctr_freq)
{
  params.channel_ct = channel_ct;
  params.sample_ct = sample_ct;
  params.pulse_sample_ct = pulse_sample_ct;
  params.sample_rate = sample_rate; 
  params.ctr_freq = ctr_freq; 
  index = 0;
  size = params.channel_ct * params.sample_ct; 
 
  filename = NULL; 
  data = new my_complex [params.channel_ct * params.sample_ct]; 
} // constructor for pulse detector

pulse_data::pulse_data(const pulse_data &det)
{
  params = det.params; 
  index = det.index;
  size = det.size; 
  filename = NULL; 
  data = new my_complex [params.channel_ct * params.sample_ct]; 
  memcpy(data,det.data, params.channel_ct * params.sample_ct * sizeof(my_complex));
} // constructor from pulse_data instance

pulse_data::~pulse_data() 
{
  if( filename )
    delete [] filename;
  if( data ) 
    delete [] data;
} // destructor


/*
 * Assignment operator. TODO this method can use a bit of cleaning up. 
 */ 
pulse_data& pulse_data::operator=(const pulse_data &det)
{
  if (params.channel_ct == det.params.channel_ct && params.sample_ct == det.params.sample_ct){
    memcpy(data,det.data,params.channel_ct*params.sample_ct*sizeof(my_complex));
    index = det.index;
    size = det.size; 
  }
  else if (params.channel_ct*params.sample_ct == det.params.channel_ct*det.params.sample_ct){  /* What's this? */ 
    params.channel_ct = det.params.channel_ct;
    params.sample_ct = det.params.sample_ct;
    memcpy(data,det.data,params.channel_ct*params.sample_ct*sizeof(my_complex));
    index = det.index;
    size = det.size;
  }
  else{
    params.channel_ct = det.params.channel_ct;
    params.sample_ct = det.params.sample_ct;
    delete [] data; 
    data = new my_complex [params.channel_ct * params.sample_ct]; 
    memcpy(data,det.data,params.channel_ct*params.sample_ct*sizeof(my_complex));
    index = det.index;
    size = det.size; 
  }
  return *this;
} // operator=


/* 
 * Read a pulse record file (.det). 
 */
int pulse_data::read(const char *fn) 
{
  if( filename )
    delete [] filename;
  if( data ) 
    delete [] data;

  int res = -1;
  filename = new char [strlen(fn)+1];
  strcpy(filename, fn); 
  
  /* Check file integrity. */ 
  struct stat results; 
  if( stat(filename, &results) != 0 ) 
    return -1; 

  /* Get parameters. */
  fstream file( filename, ios::in | ios::binary ); 
  file.read((char*)&params, sizeof(param_t)); 
  if (file.eof()) {
    file.close();
    res = -1;
  }
  else {
    size = params.sample_ct * params.channel_ct; 
  
    /* Get data. */
    data = new my_complex [params.channel_ct * params.sample_ct]; 
    file.read((char*)data, sizeof(my_complex) * params.sample_ct * params.channel_ct);
  }

  if (file)
    res = results.st_size; 

  file.close(); 
  return res; 
} // read()

/*
 * Write out a pulse record file.
 */
int pulse_data::write( const char *fn ) 
{
  /* filename for writing */
  if( strcmp(fn,"")==0 ) 
    fn = filename; 

  fstream file( fn, ios::out | ios::binary );
  if (!file.is_open())
    return -1; 
  
  /* write parameters */
  file.write((char*)&params, sizeof(param_t)); 

  /* Unwrap circular buffer and write data */
  file.write((char*)(data + (index * params.channel_ct)), 
          sizeof(my_complex) * (params.sample_ct - index) * params.channel_ct);
  file.write((char*)data, sizeof(my_complex) * index * params.channel_ct); 
  file.close();
  return 0; 
} // write() 

/* 
 * Return parameters as constant. 
 */  
const param_t& pulse_data::param() const {
  return params;
} // params() const


 /* Accessors */

my_complex& pulse_data::operator[] (int i) {
  return sample(i); 
} // operator[]

my_complex& pulse_data::sample(int i) {
  if( i< 0 || i > size ) 
    throw IndexError; 
  return data[(i + index) % size];    
} // sample()

float pulse_data::real(int i) {
  if( !data ) 
    throw NoDataError;
  return data[(i + index) % size].real();
} // real()

float pulse_data::imag(int i) {
  if( i< 0 || i > size ) 
    throw IndexError; 
  return data[(i + index) % size].imag();
} // imag() 

void pulse_data::set_real(int i, float val) {
  int size = params.sample_ct * params.channel_ct; 
  if( !data ) 
    throw NoDataError;
  if( i < 0 || i > size ) 
    throw IndexError; 
  data[(i + index) % size].real(val);
} // set_real()

void pulse_data::set_imag(int i, float val) {
  int size = params.sample_ct * params.channel_ct; 
  if( !data ) 
    throw NoDataError;
  if( i < 0 || i > size ) 
    throw IndexError; 
  data[(i + index) % size].imag(val);
} // set_imag()

my_complex* pulse_data::get()
{
  return data;
} // get()


  /* Circular buffer methods */ 

void pulse_data::add(my_complex *in)
{
  memcpy(data + (index * params.channel_ct), in, params.channel_ct * sizeof(my_complex));
  index ++;
  if(index >= params.sample_ct){
    index = 0;
  }
} // add()

int pulse_data::get_index()
{
  return index;
} // get_index()

my_complex* pulse_data::get_buffer()
{
  return data;
} // get_buffer()

my_complex* pulse_data::get_sample()
{
  return data + (index * params.channel_ct);
} // get_sample()

void pulse_data::inc_index()
{
  index++;
  if(index >= params.sample_ct){
    index = 0;
  }
} // inc_index()

