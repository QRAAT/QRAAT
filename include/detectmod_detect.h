/* detectmod_detect.h
 * A pulse detector block for GNU Radio. Input a four channel signal from 
 * a USRP device (uhd_source). Output a .det file when a pulse is detected. 
 * This file is part of QRAAT, an automated animal tracking system based 
 * on GNU Radio. 
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

#ifndef INCLUDED_detectmod_detect_H
#define INCLUDED_detectmod_detect_H

#include <rmg_api.h>
#include <gr_block.h>
#include <peak_detect.h>
#include <accumulator.h>
#include <pulse_data.h>
#include <gr_sync_block.h>


class detectmod_detect;

typedef enum {FILL_ACCUMULATOR, DETECT, CONFIRM_PEAK, FILL_BUFFER} module_state_t;

typedef boost::shared_ptr<detectmod_detect> detectmod_detect_sptr;

RMG_API detectmod_detect_sptr detectmod_make_detect (
    int pulse_width, 
    int save_width, 
    int channels, 
    const char *f, 
    const char *tx_name,
    float, float, char);

class RMG_API detectmod_detect : public gr_sync_block
{
private:

  friend RMG_API detectmod_detect_sptr detectmod_make_detect (
     int pulse_width, 
     int save_width, 
     int channels,
     const char *directory,
     const char *tx_name,
     float, float, char);
  
  int acc_length;
  int save_length;
  int ch;
  int fill_length;
  accumulator *acc;
  pulse_data *save_holder;
  pulse_data *peak_holder;
  peak_detect *pkdet;
  float rate;
  float c_freq;
  char *directory;
  char *tx_name; 
  int fill_counter;
  module_state_t state;
  void	       *d_fp;
  char psd;

  bool pulse_shape_discriminator(pulse_data *);
  void write_data(pulse_data *data_holder);
  bool open(const char *filename);
  void close();

//added enable to eliminate reconfig
  char enable_detect;

protected:

  detectmod_detect (int pulse_width, 
                    int save_width, 
                    int channels,
                    const char *filename,
                    const char *tx_name, 
                    float rate, 
                    float c_freq, 
                    char psd);
 
public:
  ~detectmod_detect ();	// public destructor

  void rise_factor(float r);
  void fall_factor(float f);
  void alpha_factor(float a);
  void reset();
  void enable();
  void enable(int pulse_width, 
              int save_width, 
              const char *directory, 
              const char *tx_name, 
              float,char);

  void enable_cont(char *filename);
  void disable();

  int work (int noutput_items,
		    gr_vector_const_void_star &input_items,
		    gr_vector_void_star &output_items);

};

#endif /* INCLUDED_detectmod_detect_h*/
