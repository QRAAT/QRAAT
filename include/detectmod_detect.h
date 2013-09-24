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
    int pulse_width, 
    int save_width, 
    int channels, 
    const char *directory, 
    const char *tx_name,
    float rate, float c_freq, char psd);

/*!
 * A pulse detector block for GNU Radio. Input a four channel signal from   
 * a USRP device (uhd_source). Output a .det file when a pulse is detected. 
 */
class RMG_API detectmod_detect : public gr_sync_block
{
private:

  friend RMG_API detectmod_detect_sptr detectmod_make_detect (
     int pulse_width, 
     int save_width, 
     int channels,
     const char *directory,
     const char *tx_name,
     float rate, float c_freq, char psd);
  
  //! Size of the time-matched signal filter.  
  int acc_length;

  //! Numbers of samples to save per pulse.
  int save_length;

  //! Number of input channels.
  int ch;

  //! What is this? 
  int fill_length;

  //! Time-matched filter. 
  accumulator *acc;
  
  //! State machine based for rise and fall triggers, base on accumulator sum.
  peak_detect *pkdet;

  //! Stored pulse samples. 
  pulse_data *save_holder;
  
  //! Stored pulse samples. 
  pulse_data *peak_holder;

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

  //! What is this? 
  int fill_counter;

  //! Current state of detector. 
  module_state_t state;

  //! A file descriptor used for status.txt output. 
  void	       *d_fp;

  //! Use pulse discriminator flag. (Why char?) 
  char psd;
  
  //! Enable detector flag. (Why char?) 
  char enable_detect;

  /*!
   * \brief What is this? 
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
  detectmod_detect (int pulse_width, 
                    int save_width, 
                    int channels,
                    const char *filename,
                    const char *tx_name, 
                    float rate, 
                    float c_freq, 
                    char psd);
 
public:

  //! Public destructor.
  ~detectmod_detect ();	

  //! Set rise trigger factor.
  void rise_factor(float r);

  //! Set fall trigger factor.
  void fall_factor(float f);

  //! Set alpha factor.
  void alpha_factor(float a);

  /*!
   * Reset the pulse detector. (Explanation)
   */ 
  void reset();
  
  /*!
   * Enable pulse detector with previous parameters. 
   */
  void enable();
  
  /*!
   * Enable pulse detector with new parameters. 
   */ 
  void enable(int pulse_width, 
              int save_width, 
              const char *directory, 
              const char *tx_name, 
              float center_freq,
              char use_pid);

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
