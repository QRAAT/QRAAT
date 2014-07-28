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

#ifndef INCLUDED_detectmod_continuous_covariance_H
#define INCLUDED_detectmod_continuous_covariance_H

#include <qraat/rmg_api.h>
#include <gr_sync_block.h>


class detectmod_continuous_covariance;

/*
 * GNU Radio uses boost smart pointers for all access to signal processing
 * blocks. The shared_ptr gets us transparent reference coutning, which 
 * greatly simplifies storage management issues. This is especially helpful
 * in our hypric C++ / Python system. 
 */
typedef boost::shared_ptr<detectmod_continuous_covariance> detectmod_continuous_covariance_sptr;

/*!
 * \brief Return a shared_ptr to a new instance of continuous_covariance.
 *
 * This routine provides access to the object. To avoid using raw
 * pointers, the object's constructor is declared private. This is the 
 * public interface.
 */
RMG_API detectmod_continuous_covariance_sptr detectmod_make_continuous_covariance (
    int num_channels, 
    int cov_len);

/*!
 * A pulse detector block for GNU Radio. Input a four channel signal from   
 * a USRP device (uhd_source). Output a .det file when a pulse is detected. 
 */
class RMG_API detectmod_continuous_covariance : public gr_sync_block
{
private:

  friend RMG_API detectmod_continuous_covariance_sptr detectmod_make_continuous_covariance (
    int num_channels, 
    int cov_len);

  //! Number of input channels.
  int num_ch;

  //! Length of covariance calculation
  int cov_len;

  //! Private constructor. 
  detectmod_continuous_covariance (
    int num_channels, 
    int cov_len);

public:

  //! Public destructor.
  ~detectmod_continuous_covariance ();	

  //! Output vector length.
  int get_output_vector_length ();

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

#endif /* INCLUDED_detectmod_continuous_covariance_h*/
