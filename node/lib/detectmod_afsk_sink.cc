/* detectmod_afsk_sink.cc
 * Implementation of the detectmod_afsk_sink class. This file is part 
 * of QRAAT, an automated animal tracking system based on GNU Radio. 
 * 
 * Copyright (C) 2012 Todd Borrowman, Christopher Patton
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

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include <detectmod_afsk_sink.h>
#include <gr_io_signature.h>
#include <cstdio>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <stdexcept>
#include <sys/time.h>
#include <string.h>
//#include <math.h>
#include <errno.h>
#include "boost/filesystem.hpp"
#include <gr_math.h>

#ifndef O_BINARY
#define	O_BINARY 0
#endif 

RMG_API detectmod_afsk_sink_sptr 
detectmod_make_afsk_sink (
    const char *_directory, 
    const char *_tx_name,
    const char *_file_extension,
    const char *_header_data,
    const unsigned int _header_len,
    const float _threshold,
    const unsigned int _threshold_timeout,
    const unsigned int _sample_timeout)
/**
 * Public constructor used by Gnu Radio 
 */
{
  return detectmod_afsk_sink_sptr (
    new detectmod_afsk_sink (_directory, 
                             _tx_name,
                             _file_extension,
                             _header_data,
                             _header_len,
                             _threshold,
                             _threshold_timeout,
                             _sample_timeout)
  );
}


detectmod_afsk_sink::detectmod_afsk_sink ( 
    const char *_directory, 
    const char *_tx_name,
    const char *_file_extension,
    const char *_header_data,
    const unsigned int _header_len,
    const float _threshold,
    const unsigned int _threshold_timeout,
    const unsigned int _sample_timeout)
  : gr_sync_block ("detectmod_afsk_sink",
    gr_make_io_signature (1, 1, sizeof(gr_complex)),
    gr_make_io_signature (0,0,0))
/**
 * Private constructor used internally 
 */
{
  set_history (2);	// we need to look at the previous value
  threshold = _threshold;
  threshold_timeout = _threshold_timeout;
  sample_timeout = _sample_timeout;
  initialize_variables(_directory, 
                       _tx_name,
                       _file_extension,
                       _header_data,
                       _header_len);

}


void detectmod_afsk_sink::initialize_variables(
    const char *_directory, 
    const char *_tx_name,
    const char *_file_extension,
    const char *_header_data,
    const unsigned int _header_len)
{
  directory = new char[strlen(_directory) + 1];
  strcpy(directory, _directory);

  tx_name = new char[strlen(_tx_name) + 1]; 
  strcpy(tx_name, _tx_name); 

  file_extension = new char[strlen(_file_extension) + 1];
  strcpy(file_extension, _file_extension);

  header_len = _header_len;
  header_data = new char[header_len];
  memcpy(header_data, _header_data, header_len);

  d_fp = 0;
  enable_demod = 0;
  enable_record = 0;
  below_count = 0;
  total_count = 0;

}

detectmod_afsk_sink::~detectmod_afsk_sink(){

  close();
  free_dynamic_memory();
}

void detectmod_afsk_sink::free_dynamic_memory()
{
  delete[] directory; 
  delete[] tx_name;
  delete[] file_extension;
  delete[] header_data;
}

int 
detectmod_afsk_sink::work (int noutput_items,
			       gr_vector_const_void_star &input_items,
			       gr_vector_void_star &output_items)
{
  gr_complex *input_buffer = (gr_complex*)input_items[0];
  input_buffer++;//advance to new value
  gr_complex product;
  float demod_signal;
  for (int j = 0; j < noutput_items; j++){
    product = input_buffer[j]*conj(input_buffer[j-1]);
    if (enable_demod > 0){
      demod_signal = gr_fast_atan2f(imag(product), real(product));
      if (demod_signal*demod_signal < 0.5){//below demod_signal threashold
          below_count++;
        }
      else{
        below_count = 0;
        enable_record = 1;
      }
      if (enable_record > 0){
        if (below_count > threshold_timeout){
          close();//close file
          enable_record = 0;
        }
        else{
          if (!d_fp){
            gen_file_ptr();
          }
          fwrite(&demod_signal, sizeof(float), 1, (FILE *)d_fp);
          total_count++;
          if (total_count > sample_timeout){
            close();
            gen_file_ptr();
            total_count = 0;
          }
        }
      }
    }
    else{
      //if (!d_fp) {
      //if above threshold and !d_fp
      if (abs(product) > threshold) {//above carrier threshold
        enable_demod = 1;
        total_count = 0;
      }
    }
  }

  return noutput_items;
}

/*
 * generate directory and file structure. 
 */
void detectmod_afsk_sink::gen_file_ptr(){
/** 
 * Writes the pulse data as a .det file
 */

  //Get time
  struct timeval tp;
  gettimeofday(&tp, NULL);
  struct tm *time_struct = gmtime(&(tp.tv_sec));
  long long ll_seconds = (long long)tp.tv_sec;
  int int_useconds = (int)tp.tv_usec;

  // Create diretory tree. 
  char filename[256];
  char directory_time_string[24];
  strftime(directory_time_string, 24, "/%Y/%m/%d/%H/%M/", time_struct);
  strcpy(filename, directory);
  strcat(filename,directory_time_string);
  boost::filesystem::create_directories(filename);

  // Create file name.
  char time_string[40];
  strftime(time_string,40,"%S",time_struct);
  char u_sec[10];
  sprintf(u_sec,"%.6d",int_useconds);
  strncat(time_string,u_sec,6);
  strcat(filename, tx_name); 
  strcat(filename, "_"); 
  strcat(filename, time_string); 
  strcat(filename, file_extension); 
  
  if (open(filename)){
    fwrite(&ll_seconds, sizeof(long long), 1, (FILE *)d_fp);
    fwrite(&int_useconds, sizeof(int), 1, (FILE *)d_fp);
    fwrite(header_data, sizeof(char), header_len, (FILE *)d_fp);
  }
  else{
    throw std::runtime_error("could not open file");
  }
}

bool
detectmod_afsk_sink::open(const char *filename)
/** 
 * opens a file, mostly copied from gnuradio
 */
{


  int fd;
  if ((fd = ::open (filename,
		    O_WRONLY|O_CREAT|O_TRUNC|O_LARGEFILE|O_BINARY, 0664)) < 0){
    perror (filename);
    return false;
  }

  if (d_fp){		// if we've already got a new one open, close it
    fclose((FILE *) d_fp);
    d_fp = 0;
  }
  
  if ((d_fp = fdopen (fd, "wb")) == NULL){
    perror (filename);
    ::close(fd);		// don't leak file descriptor if fdopen fails.
  }

  return d_fp != 0;
}

void
detectmod_afsk_sink::close()
{
  /* close file */

  if (d_fp){
    fclose((FILE *) d_fp);
    d_fp = 0;
  }
  
}

