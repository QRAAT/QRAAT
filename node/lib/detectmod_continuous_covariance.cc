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
#include <detectmod_continuous_covariance.h>
#include <gr_io_signature.h>
#include <cstdio>
//#include <sys/types.h>
//#include <sys/stat.h>
#include <fcntl.h>
#include <stdexcept>
#include <sys/time.h>
#include <string.h>
//#include <math.h>
#include <errno.h>
#include "boost/filesystem.hpp"


#ifndef O_BINARY
#define	O_BINARY 0
#endif 

RMG_API detectmod_continuous_covariance_sptr 
detectmod_make_continuous_covariance (
    int num_channels, 
    int cov_len)
/**
 * Public constructor used by Gnu Radio 
 */
{
  return detectmod_continuous_covariance_sptr (
    new detectmod_continuous_covariance (num_channels, 
                          cov_len)
  );
}

int output_vector_length(int num_channels){
  int count = 0;
  for (int j = 1; j < num_channels; j++) count += j;
  return num_channels + count*2;
};


detectmod_continuous_covariance::detectmod_continuous_covariance (
    int _num_channels, 
    int _cov_len)
  : gr_sync_block ("continuous_covariance",
    gr_make_io_signature (_num_channels, _num_channels, _cov_len * sizeof (gr_complex)),
    gr_make_io_signature (1,1,output_vector_length(_num_channels)*sizeof(float)))
/**
 * Private constructor used internally 
 */
{
  num_ch = _num_channels;
  cov_len = _cov_len;
}


detectmod_continuous_covariance::~detectmod_continuous_covariance(){

}

int 
detectmod_continuous_covariance::work (int noutput_items,
			       gr_vector_const_void_star &input_items,
			       gr_vector_void_star &output_items)
{

  int count = 0;
  int j, first_channel, second_channel;
  gr_complex *ch1;
  gr_complex *ch2;
  double real_part, imag_part;
  float *out = (float *)output_items[0];
  while (count++ < noutput_items)
  {
    for (first_channel = 0; first_channel < num_ch; first_channel++){
      ch1 = (gr_complex*)input_items[first_channel] + count*cov_len;
      real_part = 0.0;
      for (j = 0; j < cov_len; j++){
        real_part += ch1[j].real() * ch1[j].real() + ch1[j].imag() * ch1[j].imag();
      }
      *out = real_part;
      out++;
      for (second_channel = first_channel+1; second_channel < num_ch; second_channel++){
        ch2 = (gr_complex*)input_items[second_channel] + count*cov_len;
        real_part = 0.0;
        imag_part = 0.0;
        for (j = 0; j < cov_len; j++){
          real_part += ch1[j].real() * ch2[j].real() + ch1[j].imag() * ch2[j].imag();
          imag_part += ch1[j].imag() * ch2[j].real() - ch1[j].real() * ch2[j].imag();
        }
        *out = real_part;
        out++;
        *out = imag_part;
        out++;
      }
    }
  }

  return noutput_items;
}

int detectmod_continuous_covariance::get_output_vector_length (){
  return output_vector_length(num_ch);
}

