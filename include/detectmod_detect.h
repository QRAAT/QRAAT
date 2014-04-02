/* detectmod_detect.h
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

//! The states of the pulse detector. 
typedef enum 
{
  FILL_ACCUMULATOR, //!< fill accumulator
  DETECT,           //!< detect
  CONFIRM_PEAK,     //!< confirm peak
  FILL_BUFFER       //!< fill buffer
} module_state_t;

/*
 * GNU Radio uses boost smart pointers for all access to signal processing
 * blocks. The shared_ptr gets us transparent reference coutning, which 
 * greatly simplifies storage management issues. This is especially helpful
 * in our hypric C++ / Python system. 
 */
typedef boost::shared_ptr<detectmod_detect> detectmod_detect_sptr;

/*!
 * \brief Return a shared_ptr to a new instance of detectmod_detect.
 *
 * This routine provides access to the pulse detector. To avoid using raw
 * pointers, the detector's constructor is declared private. This is the 
 * public interface.
 */
RMG_API detectmod_detect_sptr detectmod_make_detect (
    int num_channels, 
    float rate, 
    int pulse_width, 
    int save_width, 
    float c_freq,
    const char *directory, 
    const char *tx_name,
    char psd,
    float rise,
    float alpha);

/*!
 * \brief Return a shared_ptr to a new instance of detectmod_detect using default parameters.
 *
 * This routine provides access to the pulse detector. To avoid using raw
 * pointers, the detector's constructor is declared private. This is the 
 * public interface.
 */
RMG_API detectmod_detect_sptr detectmod_make_detect (
    int num_channels, 
    float rate);

/*!
 * A pulse detector block for GNU Radio. Input a four channel signal from   
 * a USRP device (uhd_source). Output a .det file when a pulse is detected. 
 */
class RMG_API detectmod_detect : public gr_sync_block
{
private:

  friend RMG_API detectmod_detect_sptr detectmod_make_detect (
    int num_channels, 
    float rate, 
    int pulse_width, 
    int save_width, 
    float c_freq,
    const char *directory, 
    const char *tx_name,
    char psd,
    float rise,
    float alpha);
  
  //! Size, in samples, of the time-matched signal filter.  
  int acc_length;

  //! Numbers of samples to save per pulse.
  int save_length;

  //! Number of input channels.
  int ch;

  //! Amount of samples between the start of a pulse and the end of the file
  int fill_length;

  //! Time-matched filter. 
  accumulator *acc;
  
  //! State machine to detect peaks in accumulator sum (filtered data).
  peak_detect *pkdet;

  //! Stored pulse samples. 
  pulse_data *save_holder;
  
  //! Input sample rate. 
  float rate;

  //! Center frequency for this detector. 
  float c_freq;

  //! Root directory where output files are to be stored. 
  char *directory;

  /*! 
   * \brief Transmitter identifier. 
   * This will also be used as the file prefix for pulse data records.  
   */
  char *tx_name; 

  //! Current state of detector. 
  module_state_t state;

  //! A file descriptor used for data output (pulses or continuous). 
  void	       *d_fp;

  //! Use pulse discriminator flag.
  char psd;
  
  //! Enable detector flag.
  char enable_detect;

  /*!
   * filter based on the shape of the pulse
   */ 
  bool pulse_shape_discriminator(pulse_data *);

  /*!
   * \brief Output a pulse data record to file. 
   * \param data_holder - either the save_holder or peak_holder. 
   */ 
  void write_data(pulse_data *data_holder);

  /*!
   * \brief Open a file for writing in binary mode. 
   * Once upon a time, the detetor class wrote det files directly. 
   * This routine is now only used for status.txt. Store file 
   * descriptor in d_fp. 
   */ 
  bool open(const char *filename);

  /*!
   * \brief close d_fp.
   */ 
  void close();

  //! Private constructor. 
  detectmod_detect (int num_channels, 
                    float rate, 
                    int pulse_width, 
                    int save_width, 
                    float c_freq,
                    const char *directory, 
                    const char *tx_name,
                    char psd,
                    float rise,
                    int confirmation_time,
                    float alpha);

  void initialize_variables(
    int _pulse_width, 
    int _save_width, 
    float _band_center_freq,
    const char *_directory, 
    const char *_tx_name,
    char _psd,
    float _rise,
    float _alpha);

  void free_dynamic_memory();

public:

  //! Public destructor.
  ~detectmod_detect ();	

  //! Set rise trigger factor.
  void set_rise_factor(float rise_in);

  //! Set alpha factor.
  void set_alpha_factor(float alpha_in);

  /*!
   * Reset the pulse detector. (Reinitialize state machine)
   */ 
  void reset();
  
  /*!
   * Enable pulse detector with previous parameters. 
   */
  void enable();
  
  /*!
   * Enable pulse detector with new parameters. 
   */ 
  void enable(int _pulse_width, 
              int _save_width, 
              const char *_directory, 
              const char *_tx_name,
              float _center_freq, 
              char _use_psd,
              float _rise,
              float _alpha);

  /*!
   * Enable continuous recording of baseband. 
   */ 
  void enable_cont(char *filename);
  
  /*!
   * Disable pulse detector or continuous recorder. 
   */ 
  void disable();

  /*! 
   * Work function for signal processing block. This is the meat 
   * of any GR block. Read buffered signal run the pulse detector,
   * and output pulse records (dets). This function makes use of the
   * peak_detect and accumulator classes. 
   */
  int work (int noutput_items,
            gr_vector_const_void_star &input_items,
            gr_vector_void_star &output_items);

};

#endif /* INCLUDED_detectmod_detect_h*/
