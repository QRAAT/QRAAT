/* detectmod_afsk_sink.h
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

#ifndef INCLUDED_detectmod_afsk_sink_H
#define INCLUDED_detectmod_afsk_sink_H

#include <qraat/rmg_api.h>
#include <gr_block.h>
#include <gr_sync_block.h>


class detectmod_afsk_sink;

/*
 * GNU Radio uses boost smart pointers for all access to signal processing
 * blocks. The shared_ptr gets us transparent reference coutning, which 
 * greatly simplifies storage management issues. This is especially helpful
 * in our hypric C++ / Python system. 
 */
typedef boost::shared_ptr<detectmod_afsk_sink> detectmod_afsk_sink_sptr;

/*!
 * \brief Return a shared_ptr to a new instance of detectmod_afsk_sink.
 *
 */
RMG_API detectmod_afsk_sink_sptr detectmod_make_afsk_sink (
    const char *_directory, 
    const char *_tx_name,
    const char *_file_extension,
    const char *_header_data,
    const unsigned int _header_len,
    const float _threshold,
    const unsigned int _threshold_timeout,
    const unsigned int _sample_timeout);


/*!
 * A pulse detector block for GNU Radio. Input a four channel signal from   
 * a USRP device (uhd_source). Output a .det file when a pulse is detected. 
 */
class RMG_API detectmod_afsk_sink : public gr_sync_block
{
private:

  friend RMG_API detectmod_afsk_sink_sptr detectmod_make_afsk_sink (
    const char *_directory, 
    const char *_tx_name,
    const char *_file_extension,
    const char *_header_data,
    const unsigned int _header_len,
    const float _threshold,
    const unsigned int _threshold_timeout,
    const unsigned int _sample_timeout);

  //! Root directory where output files are to be stored. 
  char *directory;

  /*! 
   * \brief Transmitter identifier. 
   * This will also be used as the file prefix for pulse data records.  
   */
  char *tx_name; 

  char *file_extension;
  char *header_data;
  unsigned int header_len;
  float threshold;
  unsigned int threshold_timeout;
  unsigned int sample_timeout;

  //! A file descriptor used for data output (pulses or continuous). 
  void	       *d_fp;
  
  //! Enable record flag.
  char enable_record;

  //! Counter variables
  unsigned int below_count;
  unsigned int total_count;

  /*!
   * \brief Generate file structure by time.
   *
   */ 
  void gen_file_ptr();

  /*!
   * \brief Open a file for writing in binary mode.  
   */ 
  bool open(const char *filename);

  /*!
   * \brief close d_fp.
   */ 
  void close();

  //! Private constructor. 
  detectmod_afsk_sink (
    const char *_directory, 
    const char *_tx_name,
    const char *_file_extension,
    const char *_header_data,
    const unsigned int _header_len,
    const float _threshold,
    const unsigned int _threshold_timeout,
    const unsigned int _sample_timeout);

  void initialize_variables(
    const char *_directory, 
    const char *_tx_name,
    const char *_file_extension,
    const char *_header_data,
    const unsigned int _header_len);


  void free_dynamic_memory();

public:

  //! Public destructor.
  ~detectmod_afsk_sink();	

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

#endif /* INCLUDED_detectmod_afsk_sink_h*/
