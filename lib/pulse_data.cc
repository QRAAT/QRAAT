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

  /** 
   * outputing the data 
   */

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
  * class pulse_data 
  */

pulse_data::pulse_data( const char *fn ) {
  /* save filename and read *.det file */
  data = NULL;
  filename = NULL;
  index = 0; 
  if( fn && read(fn)==-1 ) 
    throw FileReadError;
} // constr


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
  
  filename = NULL; 
  data = new gr_complex [params.channel_ct * params.sample_ct]; 
} 

pulse_data::pulse_data(const pulse_data &det){
  params = det.params; 
  index = det.index;
  filename = NULL; 
  data = new gr_complex [params.channel_ct * params.sample_ct]; 
  memcpy(data,det.data, params.channel_ct * params.sample_ct * sizeof(gr_complex));

}

pulse_data::~pulse_data() {
  if( filename )
    delete [] filename;
  if( data ) 
    delete [] data;
} // destr


/** 
 * read .det file 
 * return the number of bytes in the file
 * note that this method doesn't do any error checking. we 
 * expect a correctly formatted .det
 */
int pulse_data::read(const char *fn) {
  if( filename )
    delete [] filename;
  if( data ) 
    delete [] data;

  filename = new char [strlen(fn)+1];
  strcpy(filename, fn); 
  
  struct stat results; 
  if( stat(filename, &results) == 0 ) 
    cout << "reading " << results.st_size << " bytes from "
         << filename << endl;
  else return -1; 

  /* get parameters */
  fstream file( filename, ios::in | ios::binary ); 
  file.read((char*)&params, sizeof(param_t)); 
  
  /* get data */
  data = new gr_complex [params.channel_ct * params.sample_ct]; 
  file.read((char*)data, sizeof(gr_complex) * params.sample_ct * params.channel_ct);

  int res; 
  if (file)
    res = results.st_size; 
  else 
    res = -1; 

  file.close(); 
  return res; 
}


/**
 * write out *.det file
 * filename has an optional prefix
 */
int pulse_data::write( const char *fn ) {
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
          sizeof(gr_complex) * (params.sample_ct - index) * params.channel_ct);
  file.write((char*)data, sizeof(gr_complex) * index * params.channel_ct); 
  file.close();
  return 0; 
}

/**
 * return parameters 
 * we don't want to be able to change this. 
 */ 
const param_t& pulse_data::param() const {
  return params;
}

/** 
 * return a data sample
 * this should be modifiable.
 */ 
gr_complex& pulse_data::operator[] (int i){
  int size = params.sample_ct * params.channel_ct; 
  if( !data ) 
    throw NoDataError;
  if( i < 0 || i > size ) 
    throw IndexError; 
  return data[(i + index) % size];
}


float pulse_data::real(int i) {
  int size = params.sample_ct * params.channel_ct; 
  if( !data ) 
    throw NoDataError;
  if( i < 0 || i> size ) 
    throw IndexError; 
  return data[(i + index) % size].real();
}

float pulse_data::imag(int i) {
  int size = params.sample_ct * params.channel_ct; 
  if( !data ) 
    throw NoDataError;
  if( i< 0 || i > size ) 
    throw IndexError; 
  return data[(i + index) % size].imag();
}

void pulse_data::set_real(int i, float val) {
  int size = params.sample_ct * params.channel_ct; 
  if( !data ) 
    throw NoDataError;
  if( i < 0 || i > size ) 
    throw IndexError; 
  data[(i + index) % size].real(val);
}

void pulse_data::set_imag(int i, float val) {
  int size = params.sample_ct * params.channel_ct; 
  if( !data ) 
    throw NoDataError;
  if( i < 0 || i > size ) 
    throw IndexError; 
  data[(i + index) % size].imag(val);
}





pulse_data& pulse_data::operator=(const pulse_data &det){

  /* TODO: clean up. */ 

  if (params.channel_ct == det.params.channel_ct && params.sample_ct == det.params.sample_ct){
    memcpy(data,det.data,params.channel_ct*params.sample_ct*sizeof(gr_complex));
    index = det.index;
  }
  else if (params.channel_ct*params.sample_ct == det.params.channel_ct*det.params.sample_ct){  /* What's this? */ 
    params.channel_ct = det.params.channel_ct;
    params.sample_ct = det.params.sample_ct;
    memcpy(data,det.data,params.channel_ct*params.sample_ct*sizeof(gr_complex));
    index = det.index;
  }
  else{
    params.channel_ct = det.params.channel_ct;
    params.sample_ct = det.params.sample_ct;
    delete [] data; 
    data = new gr_complex [params.channel_ct * params.sample_ct]; 
    memcpy(data,det.data,params.channel_ct*params.sample_ct*sizeof(gr_complex));
    index = det.index;
  }
  return *this;
}


void pulse_data::add(gr_complex *in){
/** 
 * Adds new values to the buffer
 */

  memcpy(data + (index * params.channel_ct), in, params.channel_ct * sizeof(gr_complex));
  index ++;
  if(index >= params.sample_ct){
    index = 0;
  }
  
  return;
}

int pulse_data::get_index(){
  return index;
}

gr_complex* pulse_data::get_buffer(){
/** 
 * Returns the current buffer contents
 * The contents are not re-ordered before the return
 */

  return data;
}

gr_complex* pulse_data::get_sample(){
//Returns address to the current sample to be replaced when adding data

  return data + (index * params.channel_ct);
}

void pulse_data::inc_index(){
//increments index

  index++;
  if(index >= params.sample_ct){
    index = 0;
  }
  
  return;
}




/*
int main (int argc, const char** argv) {

  if( argc < 2 ) {
    cout << "usage: " << argv[0] << " rmg_pulse_data.det\n"; 
    return 1; 
  }

  try { 
    * this is it *


    pulse_data pd(argv[1]); 
    cout << pd();
    for( int i = 0; i < pd().sample_ct; i++ ) 
       cout << pd[i];
    pd.write("new_");


   * this is the end *
  } catch (PulseDataErr e) { 
    cout << "err "; 
    switch(e) {
      case FileReadError: 
        cout << "file " << argv[1] << " not read"; break;
      case IndexError: 
        cout << "index"; break;
    }
    cout << endl;
  }

  return 0;
}
*/
