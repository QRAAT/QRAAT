/* detectmod_file_sink.cc
 * Implementation of the detectmod_file_sink class. This file is part 
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

#include <detectmod_file_sink.h>
#include <gr_io_signature.h>
#include <cstdio>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <stdexcept>
#include <sys/time.h>
#include <string.h>
#include <math.h>
#include <errno.h>
#include "boost/filesystem.hpp"


#ifndef O_BINARY
#define	O_BINARY 0
#endif 

RMG_API detectmod_file_sink_sptr 
detectmod_make_file_sink (
    size_t _size,
    const char *_directory, 
    const char *_tx_name,
    const char *_file_extension,
    const char *_header_data,
    const int _header_len)
/**
 * Public constructor used by Gnu Radio 
 */
{
  return detectmod_file_sink_sptr (
    new detectmod_file_sink (_size,
                             _directory, 
                             _tx_name,
                             _file_extension,
                             _header_data,
                             _header_len)
  );
}


detectmod_file_sink::detectmod_file_sink ( 
    size_t _size,
    const char *_directory, 
    const char *_tx_name,
    const char *_file_extension,
    const char *_header_data,
    const int _header_len)
  : gr_sync_block ("detectmod_file_sink",
    gr_make_io_signature (1, -1, _size),
    gr_make_io_signature (0,0,0))
/**
 * Private constructor used internally 
 */
{
  size = _size;
  initialize_variables(_directory, 
                       _tx_name,
                       _file_extension,
                       _header_data,
                       _header_len);

}


void detectmod_file_sink::initialize_variables(
    const char *_directory, 
    const char *_tx_name,
    const char *_file_extension,
    const char *_header_data,
    const int _header_len)
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
  enable_record = 0;
  staged_close = 0;

}

detectmod_file_sink::~detectmod_file_sink(){

  close();
  free_dynamic_memory();
}

void detectmod_file_sink::free_dynamic_memory()
{
  delete[] directory; 
  delete[] tx_name;
  delete[] file_extension;
  delete[] header_data;
}

int 
detectmod_file_sink::work (int noutput_items,
			       gr_vector_const_void_star &input_items,
			       gr_vector_void_star &output_items)
{
  int ch = input_items.size();
  if (enable_record > 0){
    if (!d_fp) {
      gen_file_ptr();
    }
    for (int j = 0; j < noutput_items; j++){
      for (int k = 0; k < ch; k++){
        fwrite((char*)input_items[k]+j*size, size, 1, (FILE *)d_fp);
      }
    }
  }
  if (staged_close > 0) close();
  return noutput_items;
}

/*
 * generate directory and file structure. 
 */
void detectmod_file_sink::gen_file_ptr(){
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
detectmod_file_sink::open(const char *filename)
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
detectmod_file_sink::close()
{
  /* close file */

  if (d_fp){
    fclose((FILE *) d_fp);
    d_fp = 0;
  }
  staged_close = 0;
  
}


void detectmod_file_sink::enable()
{
  //enable detector
  if (enable_record > 0){
    staged_close = 1;
  }
  enable_record = 1;
  return;
}

void detectmod_file_sink::enable(const char *_directory, 
                                 const char *_tx_name,
                                 const char *_file_extension,
                                 const char *_header_data,
                                 const int _header_len)
{
  disable();
  free_dynamic_memory();
  initialize_variables(_directory, 
                       _tx_name,
                       _file_extension,
                       _header_data,
                       _header_len);
  
  enable_record = 1;
}

void detectmod_file_sink::disable()
{
  if (enable_record > 0){
    staged_close = 1;
  }
  enable_record = 0;
}
