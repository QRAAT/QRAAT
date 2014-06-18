/* detectmod_detect.cc
 * Implementation of the detectmod_detect class, the peak detector and 
 * main component of this work. This file is part of QRAAT, an automated 
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

#include <detectmod_detect.h>
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

#include "../../qraat-base/include/pulse_data.h" // FIXME!!

#ifndef O_BINARY
#define	O_BINARY 0
#endif 

RMG_API detectmod_detect_sptr 
detectmod_make_detect (
    int num_channels, 
    float rate, 
    int pulse_width, 
    int save_width, 
    float band_center_freq,
    const char *directory, 
    const char *tx_name,
    float rise,
    float alpha)
/**
 * Public constructor used by Gnu Radio 
 */
{
  return detectmod_detect_sptr (
    new detectmod_detect (num_channels, 
                          rate, 
                          pulse_width, 
                          save_width, 
                          band_center_freq,
                          directory, 
                          tx_name,
                          rise,
                          alpha)
  );
}

RMG_API detectmod_detect_sptr detectmod_make_detect (
    int num_channels, 
    float rate)
/**
 * Public constructor used by Gnu Radio 
 */
{
  return detectmod_detect_sptr (
    new detectmod_detect (num_channels, 
                          rate, 
                          160, 
                          480, 
                          0.0,
                          "", 
                          "",
                          1.5,
                          0.01)
  );
}




detectmod_detect::detectmod_detect (
    int _num_channels, 
    float _rate, 
    int _pulse_width, 
    int _save_width, 
    float _band_center_freq,
    const char *_directory, 
    const char *_tx_name,
    float _rise,
    float _alpha)
  : gr_sync_block ("detectmod_detect",
    gr_make_io_signature (_num_channels, _num_channels, sizeof (gr_complex)),
    gr_make_io_signature (0,0,0))
/**
 * Private constructor used internally 
 */
{
  rate   = _rate;
  ch     = _num_channels;
  initialize_variables(_pulse_width,
                       _save_width,
                       _band_center_freq,
                       _directory, 
                       _tx_name,
                       _rise,
                       _alpha);

}


void detectmod_detect::initialize_variables(
    int _pulse_width, 
    int _save_width, 
    float _band_center_freq,
    const char *_directory, 
    const char *_tx_name,
    float _rise,
    float _alpha)
{
  c_freq = _band_center_freq;
  acc_length = _pulse_width;//size of the accumulator
  
  /* 
   * length of the file needs to be at least 3 times as long as 
   * the pulse to accomidate the noise covariance calculation
   */
  if(_save_width < 3*acc_length){
    save_length = 3*acc_length;
  }
  else{
    save_length = _save_width;
  }

  clipping_factor = (2.0*_rise-1)/(float)acc_length;

  directory = new char[strlen(_directory) + 1];
  strcpy(directory, _directory);

  tx_name = new char[strlen(_tx_name) + 1]; 
  strcpy(tx_name, _tx_name); 

  state = FILL_ACCUMULATOR;
  fill_length = ((int)(0.5*(save_length - 2*acc_length)));
  d_fp = 0;
  
  acc = new accumulator(acc_length);
  save_holder = new pulse_data(ch, save_length, acc_length, rate, c_freq);

  int time_constant;
  if (_alpha < 1){
    time_constant = (int)(1.0/_alpha);
  }
  else{
    time_constant = _alpha*rate;
  }

  pkdet = new peak_detect(_rise, fill_length, time_constant);

  enable_detect = 0;

}

detectmod_detect::~detectmod_detect(){

  close();
  free_dynamic_memory();
}

void detectmod_detect::free_dynamic_memory()
{
  delete[] directory; 
  delete[] tx_name;
  delete acc;
  delete save_holder;
  delete pkdet;
}

int 
detectmod_detect::work (int noutput_items,
			       gr_vector_const_void_star &input_items,
			       gr_vector_void_star &output_items)
{
  
  gr_complex *current_sample; 
  float r,i,sample_pwr,acc_total,noise_floor,max_pwr;
  detect_state_t det_state = BELOW_THRESHOLD;
  int save_holder_index;

  //added enable
  if (enable_detect==1){

    //Loop through all of the samples
    for (int j=0;j<noutput_items;j++){
      
          //Calculate total power received
      sample_pwr=0.0;
      current_sample = save_holder->get_sample();
      for (int m=0;m<ch;m++){
        current_sample[m] = ((gr_complex *) input_items[m])[j];
        r = current_sample[m].real();
        i = current_sample[m].imag();
        sample_pwr += (r*r) + (i*i);
      }
      save_holder->inc_index();



      switch(state){
        
            //initialize the time-matched filter and circular buffer
        case FILL_ACCUMULATOR:
          acc_total = acc->add(sample_pwr);
          save_holder_index = save_holder->get_index();
          if (save_holder_index == (save_length-1)){
            state = DETECT;
                    //initial estimate of the noise floor for detector
            pkdet->set_noise_floor(acc_total,acc_length);
            printf("%s Seed: %e\n",directory,acc_total);
          }
        break;
      
            //Run detector
        case DETECT:
          
          noise_floor = pkdet->get_noise_floor();
          max_pwr = clipping_factor*noise_floor;
          if (sample_pwr > max_pwr){
            acc_total = acc->add(max_pwr);
          }
          else{
            acc_total = acc->add(sample_pwr);  
          }
          det_state = pkdet->detect(acc_total);
          if(det_state == PEAK){
            save_holder->params.pulse_index = save_length - acc_length;
            state = CONFIRM_PEAK;
          }
        
        break;

        case CONFIRM_PEAK:
          noise_floor = pkdet->get_noise_floor();
          max_pwr = clipping_factor*noise_floor;
          if (sample_pwr > max_pwr){
            acc_total = acc->add(max_pwr);
          }
          else{
            acc_total = acc->add(sample_pwr);  
          }
          det_state = pkdet->detect(acc_total);
          save_holder->params.pulse_index--;
          if(det_state == TRIGGER){
            write_data(save_holder);
            state = DETECT;
          }
          else if(det_state == PEAK){
            save_holder->params.pulse_index = save_length - acc_length;
          }

        break;
      }//switch
    }//for
  }//enable if statement

  //Continuous record
  else if(enable_detect == 2 && d_fp){

    gr_complex *value_addr;
      
    for (int i = 0; i < noutput_items; i++){
      for (int n = 0; n < ch; n++){
        value_addr = ((gr_complex *)input_items[n]) + i;
        fwrite(value_addr,sizeof(gr_complex),1,(FILE *)d_fp);
      }
    }

  }

  return noutput_items;
}

/*
 * Write pulse data as a .det file. 
 */
void detectmod_detect::write_data(pulse_data *data_holder){
/** 
 * Writes the pulse data as a .det file
 */

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
  strcat(filename, ".det"); 
  
  data_holder->params.t_sec = int_seconds; 
  data_holder->params.t_usec = int_useconds; 

  if (data_holder->write(filename) == -1)
  {
    printf("Can't open file \"%s\"\n",filename);
    return;
  }

  // Print some stuff. 
  float snr = 10.0*log10(pkdet->get_peak()/pkdet->get_noise_floor());
  float noise_db = 10.0*log10(pkdet->get_noise_floor()/1e-5);
  strftime(time_string,40,"%H:%M:%S %d %b %Y",time_struct);
  
  printf("pulse %s,%d,%f,%f\n", tx_name, int_seconds, noise_db, snr);  
  printf("%s\n\t%s\n\t\tNoise Floor: %.2f dB, SNR: %.2f dB\n",time_string, filename, noise_db, snr);
  

}

bool
detectmod_detect::open(const char *filename)
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
detectmod_detect::close()
{
  /* close file */

  if (d_fp){
    fclose((FILE *) d_fp);
    d_fp = 0;
  }
  
}


void detectmod_detect::set_rise_factor(float rise_in)
{
  pkdet->set_rise(rise_in);
}

void detectmod_detect::set_alpha_factor(float alpha_in)
{
  float temp_alpha;
  if (alpha_in < 1){
    pkdet->set_alpha(alpha_in);
  }
  else{
    pkdet->set_time_constant((int)(alpha_in*rate));
  }
}

void detectmod_detect::reset()
{
  //write data out if state = FILL_BUFFER or CONFIRM_PEAK
  if (state == CONFIRM_PEAK){
    write_data(save_holder);
  }
  state = FILL_ACCUMULATOR;
}

void detectmod_detect::enable()
{
  //enable detector
  reset();
  enable_detect = 1;
  return;
}

void detectmod_detect::enable(int _pulse_width, 
                              int _save_width, 
                              const char *_directory, 
                              const char *_tx_name,
                              float _center_freq, 
                              float _rise,
                              float _alpha)
{
  reset();

  free_dynamic_memory();
  initialize_variables(_pulse_width, 
                       _save_width, 
                       _center_freq,
                       _directory, 
                       _tx_name,
                       _rise,
                       _alpha);
  
  enable_detect = 1;
}

void detectmod_detect::enable_cont(char *filename)
{
  reset();
  enable_detect = 2;
  if(!open(filename)){
    printf("Can't open file \"%s\"\n",filename);
    enable_detect = 0;
  }
  else{
    printf("Opened file \"%s\" for continuous recording\n",filename);
  }
}

void detectmod_detect::disable()
{
  reset();
  if (enable_detect == 2){
    close();
  }
  enable_detect = 0;
}
