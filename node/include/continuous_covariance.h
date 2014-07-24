/* continuous_covariance.h
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

#ifndef INCLUDED_continuous_covariance_H
#define INCLUDED_continuous_covariance_H

#include <qraat/rmg_api.h>
#include <gr_sync_block.h>


class continuous_covariance;

/*
 * GNU Radio uses boost smart pointers for all access to signal processing
 * blocks. The shared_ptr gets us transparent reference coutning, which 
 * greatly simplifies storage management issues. This is especially helpful
 * in our hypric C++ / Python system. 
 */
typedef boost::shared_ptr<continuous_covariance> continuous_covariance_sptr;

/*!
 * \brief Return a shared_ptr to a new instance of continuous_covariance.
 *
 * This routine provides access to the object. To avoid using raw
 * pointers, the object's constructor is declared private. This is the 
 * public interface.
 */
RMG_API continuous_covariance_sptr make_continuous_covariance (
    int num_channels, 
    int cov_len, 
    const char *directory, 
    const char *tx_name);

/*!
 * A pulse detector block for GNU Radio. Input a four channel signal from   
 * a USRP device (uhd_source). Output a .det file when a pulse is detected. 
 */
class RMG_API continuous_covariance : public gr_sync_block
{
private:

  friend RMG_API continuous_covariance_sptr make_continuous_covariance (
    int num_channels, 
    int cov_len, 
    const char *directory, 
    const char *tx_name);

  //! Number of input channels.
  int num_ch;

  //! Length of covariance calculation
  int cov_len;

  //! Root directory where output files are to be stored. 
  char *directory;

  /*! 
   * \brief Transmitter identifier. 
   * This will also be used as the file prefix for pulse data records.  
   */
  char *tx_name;


  //! A file descriptor used for data output (pulses or continuous). 
  void	       *d_fp;

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
  continuous_covariance (
    int num_channels, 
    int cov_len, 
    const char *directory, 
    const char *tx_name);

public:

  //! Public destructor.
  ~continuous_covariance ();	

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

#endif /* INCLUDED_continuous_covariance_h*/
