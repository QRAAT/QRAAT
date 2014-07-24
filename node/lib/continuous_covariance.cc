/* continuous_covariance.cc
 * Implementation of the continuous_covariance class.
 * This file is part of QRAAT, an automated 
 * animal tracking system  based on GNU Radio. 
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

//#include <qraat/pulse_data.h>
#include <continuous_covariance.h>
#include <gr_io_signature.h>
#include <cstdio>
//#include <sys/types.h>
//#include <sys/stat.h>
//#include <fcntl.h>
#include <stdexcept>
#include <sys/time.h>
#include <string.h>
//#include <math.h>
#include <errno.h>
#include "boost/filesystem.hpp"


#ifndef O_BINARY
#define	O_BINARY 0
#endif 

RMG_API continuous_covariance_sptr 
make_continuous_covariance (
    int num_channels, 
    int cov_len, 
    const char *directory, 
    const char *tx_name)
/**
 * Public constructor used by Gnu Radio 
 */
{
  return continuous_covariance_sptr (
    new continuous_covariance (num_channels, 
                          cov_len, 
                          directory, 
                          tx_name)
  );
}



continuous_covariance::continuous_covariance (
    int _num_channels, 
    int _cov_len, 
    const char *_directory, 
    const char *_tx_name)
  : gr_sync_block ("continuous_covariance",
    gr_make_io_signature (_num_channels, _num_channels, _cov_len * sizeof (gr_complex)),
    gr_make_io_signature (0,0,0))
/**
 * Private constructor used internally 
 */
{
  num_ch = _num_channels;
  cov_len = _cov_len;
  directory = new char[strlen(_directory) + 1];
  strcpy(directory, _directory);

  tx_name = new char[strlen(_tx_name) + 1]; 
  strcpy(tx_name, _tx_name); 


  //Get time
  struct timeval tp;
  gettimeofday(&tp, NULL);
  void *temp;
  struct tm *time_struct = gmtime(&(tp.tv_sec));
  int int_seconds = (int)tp.tv_sec;
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
  strcat(filename, ".cov"); 

  if (!open(filename)) throw std::runtime_error ("can't open file");

  //TODO write header?

}


continuous_covariance::~continuous_covariance(){

  close();
  delete[] directory;
  delete[] tx_name;
}

int 
continuous_covariance::work (int noutput_items,
			       gr_vector_const_void_star &input_items,
			       gr_vector_void_star &output_items)
{
  
  int count = 0;
  int j, first_channel, second_channel;
  gr_complex *ch1;
  gr_complex *ch2;
  double real_part, imag_part;
  float* real_f, imag_f;
  while (count++ < noutput_items)
  {
    for (first_channel = 0; first_channel < num_ch; first_channel++){
      ch1 = input_items[first_channel] + count;
      real_part = 0.0;
      for (j = 0; j < cov_len; j++){
        real_part += ch1[j].real() * ch1[j].real() + ch1[j].imag() * ch1[j].imag();
      }
      real_f* = (float)real_part;
      fwrite(real_f,sizeof(float),1,fd);
      for (second_channel = first_channel+1; second_channel < num_ch; second_channel++){
        ch2 = input_items[second_channel] + count;
        real_part = 0.0;
        imag_part = 0.0;
        for (j = 0; j < cov_len; j++){
          real_part += ch1[j].real() * ch2[j].real() + ch1[j].imag() * ch2[j].imag();
          imag_part += ch1[j].imag() * ch2[j].real() - ch1[j].real() * ch2[j].imag();
        }
        real_f* = (float)real_part;
        imag_f* = (float)imag_part;
        fwrite(real_f,sizeof(float),1,fd);
        fwrite(imag_f,sizeof(float),1,fd);
      }
    }
  }

  return noutput_items;
}

bool
continuous_covariance::open(const char *filename)
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
continuous_covariance::close()
{
  /* close file */

  if (d_fp){
    fclose((FILE *) d_fp);
    d_fp = 0;
  }
  
}


