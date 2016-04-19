/* -*- c++ -*- */
/* 
 * Copyright 2015 <+YOU OR YOUR COMPANY+>.
 * 
 * This is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3, or (at your option)
 * any later version.
 * 
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License
 * along with this software; see the file COPYING.  If not, write to
 * the Free Software Foundation, Inc., 51 Franklin Street,
 * Boston, MA 02110-1301, USA.
 */

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include <gnuradio/io_signature.h>
#include "pulse_sink_c_impl.h"
#include <boost/filesystem.hpp>
#include <sys/time.h>
#include <stdio.h>

namespace gr {
  namespace rmg {

    pulse_sink_c::sptr
    pulse_sink_c::make(unsigned int num_channels)
    {
      return gnuradio::get_initial_sptr
        (new pulse_sink_c_impl(num_channels));
    }

    /*
     * The private constructor
     */
    pulse_sink_c_impl::pulse_sink_c_impl(unsigned int num_channels)
      : gr::sync_block("pulse_sink_c",
              gr::io_signature::make(num_channels, num_channels, sizeof(gr_complex)),
              gr::io_signature::make(0, 0, 0))
    {
      if (num_channels > 0) {
        d_num_channels = num_channels;
      }
      else{
        throw std::out_of_range("num_channels");
      }
      enable_detect = 0;
    }

    /*
     * Our virtual destructor.
     */
    pulse_sink_c_impl::~pulse_sink_c_impl()
    {

    }

    void 
    pulse_sink_c_impl::enable(
        const unsigned int pulse_width, 
        const unsigned int save_width, 
        const float center_freq,
        const float rate,
        const char *directory, 
        const char *tx_name,
        const float rise,
        const float alpha)
    {
      gr::thread::scoped_lock guard(d_mutex);

      d_acc_length = pulse_width;//size of the accumulator
  
      /* 
       * length of the file needs to be at least 3 times as long as 
       * the pulse to accomidate the noise covariance calculation
       */
      if(save_width > d_acc_length){
        d_save_length = save_width;
      }
      else{
        d_save_length = 3*d_acc_length;
      }

      d_clipping_factor = (2.0*rise-1)/(float)d_acc_length;

      d_directory = directory;
      d_txID = tx_name;
      d_ctr_freq = center_freq;

      state = FILL_ACCUMULATOR;

      if (d_save_length < 2*d_acc_length){
        d_fill_length = (int)(0.5*(d_save_length - d_acc_length));
      }
      else if (d_save_length < 3*d_acc_length){
        d_fill_length = (int)(0.5*d_acc_length);
      }
      else {
        d_fill_length = ((int)(0.5*(d_save_length - 2*d_acc_length)));
      }

      acc.reset(
               new accumulator(boost::accumulators::tag::rolling_window::window_size = d_acc_length));


      save_holder.reset(
               new pulse_data(d_num_channels, d_save_length, d_acc_length, rate, center_freq));
      
      int time_constant;
      if (alpha < 1){
        time_constant = (int)(1.0/alpha);
      }
      else{
        time_constant = alpha*rate;
      }

      pkdet.reset( 
               new peak_detect(rise, d_fill_length, time_constant));

      enable_detect = 1;

    }

    void
    pulse_sink_c_impl::disable(){
      enable_detect = 0;
    }

    void
    pulse_sink_c_impl::write_data(){
    /** 
     * Internal function, writes the pulse data as a .det file
     */

      //Get time
      struct timeval tp;
      gettimeofday(&tp, NULL);
      save_holder->set_time(tp);
      struct tm *time_struct = gmtime(&(tp.tv_sec));
      int int_seconds = (int)tp.tv_sec;
      int int_useconds = (int)tp.tv_usec;

      // Create directory tree. 
      std::string filename = d_directory;
      char directory_time_string[24];
      strftime(directory_time_string, 24, "/%Y/%m/%d/%H/%M/", time_struct);
      filename.append(directory_time_string);
      boost::filesystem::create_directories(filename);

      // Create file name.
      char time_string[40];
      strftime(time_string,10,"%S",time_struct);
      char u_sec[7];
      sprintf(u_sec,"%.6d",int_useconds);
      strncat(time_string,u_sec,6);
      filename.append(d_txID); 
      filename.append("_"); 
      filename.append(time_string); 
      filename.append(".det"); 
      
      if (save_holder->write(filename.c_str()) == -1)
      {
        printf("Can't open file \"%s\"\n",filename.c_str());
        return;
      }

      // Print some stuff. 
      float snr = 10.0*log10(pkdet->get_peak()/pkdet->get_noise_floor());
      float noise_db = 10.0*log10(pkdet->get_noise_floor()/1e-5);

      strftime(time_string,40,"%H:%M:%S %d %b %Y",time_struct);
      
      printf("pulse %s,%d,%f,%f\n", d_txID.c_str(), int_seconds, noise_db, snr);  
      printf("%s\n\t%s\n\t\tNoise Floor: %.2f dB, SNR: %.2f dB\n",time_string, filename.c_str(), noise_db, snr);
      
    }


    //internal function to update acc and pkdet
    detect_state_t
    pulse_sink_c_impl::update_peak_detect(
        const float sample_pwr, const float noise_floor)
    {
      float max_pwr = d_clipping_factor*noise_floor;
      if (sample_pwr > max_pwr){
        (*acc)(max_pwr);
      }
      else{
        (*acc)(sample_pwr);  
      }
      return pkdet->detect(boost::accumulators::rolling_sum(*acc));
    }

    int
    pulse_sink_c_impl::work(int noutput_items,
			  gr_vector_const_void_star &input_items,
			  gr_vector_void_star &output_items)
    {

      //added enable
      if (enable_detect==1){
        gr::thread::scoped_lock guard(d_mutex);

        gr_complex current_sample; 
        float r,i;
        float sample_pwr,acc_total,noise_floor,max_pwr;
        detect_state_t det_state = BELOW_THRESHOLD;
        unsigned int save_holder_index;

        //Loop through all of the samples
        for (int j=0;j<noutput_items;j++){
          
              //Calculate total power received
          sample_pwr=0.0;
          //current_sample = save_holder->get_sample();
          for (int m=0;m<d_num_channels;m++){
            current_sample = ((const gr_complex *) input_items[m])[j];
            r = current_sample.real();
            i = current_sample.imag();
            sample_pwr += (r*r) + (i*i);
            save_holder->append((my_complex *)&current_sample);
          }
          //save_holder->inc_index();



          switch(state){
            
                //initialize the time-matched filter and circular buffer
            case FILL_ACCUMULATOR:
              (*acc)(sample_pwr);
              //save_holder_index = save_holder->get_index();
              if (save_holder->buffer_full()){
                state = DETECT;
                        //initial estimate of the noise floor for detector
                pkdet->set_noise_floor(boost::accumulators::rolling_sum(*acc),d_acc_length);
                printf("%s %.3fMHz Seed: %e\n", d_txID.c_str(), d_ctr_freq/1.0e6, boost::accumulators::rolling_sum(*acc));
              }

            break;
          
                //Run detector
            case DETECT:
              det_state = update_peak_detect(sample_pwr, pkdet->get_noise_floor());
              if(det_state == PEAK){
                save_holder->set_pulse_index(d_save_length - d_acc_length);
                state = CONFIRM_PEAK;
              }

            break;

            case CONFIRM_PEAK:
              det_state = update_peak_detect(sample_pwr, pkdet->get_noise_floor());
              if(det_state == TRIGGER){
                write_data();
                state = DETECT;
              }
              else if(det_state == PEAK){
                save_holder->set_pulse_index(d_save_length - d_acc_length);
              }

            break;
          }//switch
        }//for
      }//enable if statement

      // Tell runtime system how many output items we produced.
      return noutput_items;
    }

  } /* namespace rmg */
} /* namespace gr */

