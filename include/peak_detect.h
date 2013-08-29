/* peak_detect.h. This file is part of QRAAT, an automated animal tracking 
 * system based on GNU Radio. 
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

/*! States for peak detector. */
typedef enum 
{
  BELOW_THRESHOLD, //!< below threshold
  ABOVE_THRESHOLD, //!< above threshold
  PEAK,            //!< peak
  TRIGGER          //!< trigger
} detect_state_t;

class detectmod_detect;

/*!
 * \brief Peak detection state machine. 
 */
class peak_detect
{

friend class detectmod_detect; 

private:

  float rise;       //! Rise trigger
  float fall;       //! Fall trigger
  float alpha;      //! Alpha factor
  float peak_value; //! Previous peak value?
  float avg;        //! What is this? 

  detect_state_t state; //! Current state. 

public:

  /*! 
   * \brief Constructor.
   * \param rise_in - Rise trigger
   * \param fall_in - Fall trigger
   * \param alpha_in - Alpha factor
   */
  peak_detect(float rise_in, float fall_in, float alpha_in);

  /*!
   * \brief Run state machine. 
   * \param data - Next datum. 
   */
  detect_state_t detect(const float data);

};
