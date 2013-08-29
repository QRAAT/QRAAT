/** \file accumulator.h
 * his file is part of QRAAT, an automated animal tracking system based 
 * on GNU Radio. 
 *
 * Copyright (C) 2012 Todd Borrowman
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

/*!
 * Maintain a running sum of the USRP input signal. This is treated as 
 * a time-matched filter for use by the detector class. The signal 
 * itself is stored in a circular buffer. 
 */ 
class accumulator
{
private:

  //! Signal buffer. 
  float *buffer;

  //! Size of the buffer
  int size;

  //! The running sum. 
  double total_sum;

  //! Index of the front of the circular buffer. 
  int index;
  
public:

  /*!
   * accumulator constructor
   */
  accumulator(int s);

  /*!
   * accumulator destructor
   */
  ~accumulator();

  /*! 
   * Add a new datum to buffer. 
   * \param in - the new datum
   * \return The running sum 
   */ 
  float add(float in);

  /*! 
   * Get the current total. 
   */ 
  float value();
};
