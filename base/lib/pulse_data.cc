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
#include <fstream>
#include <sys/stat.h>
#include <errno.h>

#include "../include/pulse_data.h"


std::ostream& operator<< ( std::ostream &out, const pulse_data &p ) {
  out << p.str();
  return out;
}


/**
 * class pulse_data. 
 */
pulse_data::pulse_data( const char *fn ) 
{
  data = NULL;
  if( fn && read(fn)==-1 ) 
    throw FileReadError;
} // constructor for Python interface


pulse_data::pulse_data(
   int _channel_ct,
   int _sample_ct,
   int _pulse_sample_ct,
   float _sample_rate, 
   float _ctr_freq)
{
  channel_ct = _channel_ct;
  sample_ct = _sample_ct;
  pulse_sample_ct = _pulse_sample_ct;
  sample_rate = _sample_rate; 
  ctr_freq = _ctr_freq; 

  //default values so code doesn't access uninitialized variables
  pulse_index = -1;
  t_sec = 0;
  t_usec = 0;

  filename = ""; 
  data = new boost::circular_buffer<my_complex>(channel_ct * sample_ct);
} // constructor for pulse detector

//Copy constructor. Deep copy of circular buffer.
pulse_data::pulse_data(const pulse_data &det)
{
  filename = det.filename;
  channel_ct = det.channel_ct;
  sample_ct = det.sample_ct;
  pulse_sample_ct = det.pulse_sample_ct;
  pulse_index = det.pulse_index;
  sample_rate = det.sample_rate;
  ctr_freq = det.ctr_freq;
  t_sec = det.t_sec;
  t_usec = det.t_usec;
  //data = new boost::circular_buffer<my_complex>();
  *data = *(det.data);
} // constructor from pulse_data instance

pulse_data::~pulse_data() 
{
  if( data ) 
    delete data;
} // destructor


/*
 * Assignment operator. Shallow copy of circular buffer. 
 */ 
pulse_data& pulse_data::operator=(const pulse_data &det)
{
  filename = det.filename;
  channel_ct = det.channel_ct;
  sample_ct = det.sample_ct;
  pulse_sample_ct = det.pulse_sample_ct;
  pulse_index = det.pulse_index;
  sample_rate = det.sample_rate;
  ctr_freq = det.ctr_freq;
  t_sec = det.t_sec;
  t_usec = det.t_usec;
  data = det.data;
  return *this;
} // operator=

std::string pulse_data::str() const
{
  std::stringstream output;

  time_t pulse_time = t_sec + (t_usec * 0.000001);
  output << "channel_ct      " << channel_ct << std::endl;
  output << "sample_ct       " << sample_ct << std::endl;
  output << "pulse_sample_ct " << pulse_sample_ct << std::endl;
  output << "pulse_index     " << pulse_index << std::endl;
  output << "sample_rate     " << sample_rate << std::endl;
  output << "ctr_freq        " << ctr_freq << std::endl;
  output << "pulse_time      " << asctime(gmtime(&pulse_time)) << std::endl;
  output << "stored_data_ct  " << data->size() << std::endl;

  return output.str();
}

/* 
 * Read a pulse record file (.det). 
 */
int pulse_data::read(const char *fn) 
{

  int res = -1;
  filename = fn;
  if (data){
    delete data;
  }

  /* Check file integrity. */ 
  struct stat results; 
  if( stat(filename.c_str(), &results) != 0 ) 
    return -1; 

  /* Get parameters. */
  std::fstream file( filename.c_str(), std::ios::in | std::ios::binary ); 
  file.read((char*)&channel_ct, sizeof(int));
  if (channel_ct > 0) { //backward compatable det file
    file.read((char*)&sample_ct, sizeof(int));
    file.read((char*)&pulse_sample_ct, sizeof(int));
    file.read((char*)&pulse_index, sizeof(int));
    file.read((char*)&sample_rate, sizeof(float));
    file.read((char*)&ctr_freq, sizeof(float));
    file.read((char*)&t_sec, sizeof(int));
    file.read((char*)&t_usec, sizeof(int));
  }
  else {  //new det file format
    return -1;
  }

  if (file.eof()) { //no data
    file.close();
    res = -1;
  }
  else {
    int size = sample_ct * channel_ct;
    my_complex *file_data = new my_complex[size];
  
    /* Get data. */
    file.read((char*)file_data, sizeof(my_complex)*size);
    data = new boost::circular_buffer<my_complex>(file_data, file_data+size);
    delete[] file_data;
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
  if( fn == NULL || fn[0] == '\0' ) {
    if( filename == "" ) {
      return -1;
    }
    //else use filename string in "filename"
  }
  else {
    filename = fn;
  }

  std::fstream file( filename.c_str(), std::ios::out | std::ios::trunc | std::ios::binary );
  if (!file.is_open())
    return -1; 
  
  /* write parameters */
  file.write((char*)&channel_ct, sizeof(int));
  file.write((char*)&sample_ct, sizeof(int));
  file.write((char*)&pulse_sample_ct, sizeof(int));
  file.write((char*)&pulse_index, sizeof(int));
  file.write((char*)&sample_rate, sizeof(float));
  file.write((char*)&ctr_freq, sizeof(float));
  file.write((char*)&t_sec, sizeof(int));
  file.write((char*)&t_usec, sizeof(int));


  /* Unwrap circular buffer and write data */
  boost::circular_buffer<my_complex>::const_array_range range = data->array_one();
  file.write((char*)range.first, sizeof(my_complex)*range.second);

  range = data->array_two();
  if (range.second > 0){
    file.write((char*)range.first, sizeof(my_complex)*range.second);
  }
  file.close();

  return 0; 
} // write() 

void pulse_data::set_pulse_index(const int pi){
  pulse_index = pi;
}

void pulse_data::set_time(const struct timeval tp){
  t_sec = (int)tp.tv_sec;
  t_usec = (int)tp.tv_usec;
}

void pulse_data::set_time(const int sec, const int usec){
  t_sec = sec;
  t_usec = usec;
}


  /* Circular buffer methods */ 

my_complex& pulse_data::operator[] (const int i) {
  return (*data)[i*channel_ct]; 
}

my_complex* pulse_data::get_data()
{
  return data->linearize();
}

void pulse_data::append(my_complex *in)
{
  data->push_back(*in);
  if (pulse_index >= 0){
    pulse_index--;
  }
}

bool pulse_data::buffer_full()
{
  return data->full();
}
