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
#include <cstring> // memcpy
#include <sys/stat.h>

#include "pulse_data.h"

using namespace std;

  /** 
   * outputing the data 
   */

ostream& operator<< ( ostream &out, const param_t &p ) {
  out << "channel_ct     " << p.channel_ct << endl;
  out << "data_ct        " << p.data_ct << endl;
  out << "filter_data_ct " << p.filter_data_ct << endl;
  out << "pulse_index    " << p.pulse_index << endl;
  out << "sample_rate    " << p.sample_rate << endl;
  out << "ctr_freq       " << p.ctr_freq << endl;
  printf("pulse_time     %s", asctime(gmtime(&(p.pulse_time.tv_sec)))); 
  return out;
}


 /**
  * class pulse_data 
  */

pulse_data::pulse_data( const char *fn ) {
  /* save filename and read *.det file */
  data = NULL;
  filename = NULL; 
  if( fn && read(fn)==-1 ) 
    throw FileReadError;
} // constr


pulse_data::~pulse_data() {
  if( filename )
    delete [] filename;
  if( data ) 
    delete [] data;
} // destr

void pulse_data::open( 
   int channel_ct,
   int data_ct,
   int filter_data_ct,
   int pulse_index,
   float sample_rate, 
   float ctr_freq,
   struct timeval *pulse_time,
   const char *fn)
{
  params.channel_ct     =  channel_ct; 
  params.data_ct        =  data_ct; 
  params.filter_data_ct =  filter_data_ct; 
  params.pulse_index    =  pulse_index; 
  params.sample_rate    =  sample_rate; 
  params.ctr_freq       =  ctr_freq; 
  params.pulse_time     = *pulse_time; 

  if( data ) 
    delete [] data; 
  data = NULL; //new sample_t [params.data_ct];

  det.open( fn, ios::out | ios::binary );
  
  /* write parameters */
  det.write((char*)&params, sizeof(param_t)); 

} //open()


/**
 * write n bytes from data to det stream
 */
void pulse_data::write(const char *data, int n) {
  det.write(data, n);  
} //write()


void pulse_data::close() {
  det.close();
} //close()


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
  if( !file.read((char*)&params, sizeof(param_t)) ) {
    file.close();
    return -1;
  }

  /* get data */
  data = new gr_complex [params.channel_ct * params.data_ct]; 
  if( !file.read((char*)data, sizeof(gr_complex) * params.data_ct * params.channel_ct) )
    return -1; 

  file.close(); 
  return results.st_size; 
}


/**
 * write out *.det file
 * filename has an optional prefix
 */
void pulse_data::writeout( const char *fn ) {
  /* filename for writing */
  if( strcmp(fn,"")==0 ) 
    fn = filename; 

  fstream file( fn, ios::out | ios::binary );
  
  /* write parameters */
  file.write((char*)&params, sizeof(param_t)); 

  /* write data */
  file.write((char*)data, sizeof(gr_complex) * params.channel_ct * params.data_ct); 

  file.close();
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
  if( !data ) 
    throw NoDataError;
  if( i<0 || i>(params.data_ct * params.channel_ct) ) 
    throw IndexError; 
  return data[i];
}


float pulse_data::real(int i) {
  if( !data ) 
    throw NoDataError;
  if( i<0 || i>(params.data_ct * params.channel_ct) ) 
    throw IndexError; 
  return data[i].real();
}

float pulse_data::imag(int i) {
  if( !data ) 
    throw NoDataError;
  if( i<0 || i>(params.data_ct * params.channel_ct) ) 
    throw IndexError; 
  return data[i].imag();
}

void pulse_data::set_real(int i, float val) {
  if( !data ) 
    throw NoDataError;
  if( i<0 || i>(params.data_ct * params.channel_ct) ) 
    throw IndexError; 
  data[i].real(val);
}

void pulse_data::set_imag(int i, float val) {
  if( !data ) 
    throw NoDataError;
  if( i<0 || i>(params.data_ct * params.channel_ct) ) 
    throw IndexError; 
  data[i].imag(val);
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
    for( int i = 0; i < pd().data_ct; i++ ) 
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
