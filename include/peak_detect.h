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
  TRIGGER,         //!< trigger
  POST_TRIGGER     //!< post trigger
} detect_state_t;

static float FALL_RATIO = 0.9;

class detectmod_detect;

/*!
 * \brief Peak detection state machine. 
 */
class peak_detect
{

private:

  float rise;       //! Rise trigger
  int confirmation_time;  //! Number of samples after peak to wait before triggering
  float alpha;      //! Alpha factor
  int time_constant;  //! Time constant in samples, =1/alpha
  int samples_in_noise_floor; //! Number of samples in noise_floor estimation
  float peak_value; //! Current peak value
  float noise_floor;        //! Noise floor running average
  int confirmation_counter; //! Number of samples since event

  detect_state_t state; //! Current state. 

public:

  /*! 
   * \brief Constructor.
   * \param rise_in - Rise trigger
   * \param confirmation_time_in - period to wait to confirm peak
   * \param wait_time_in - period to wait to restart detect
   * \param time_constant_in - time constant for exponential filter
   */
  peak_detect(float rise_in, int confirmation_time_in, int time_constant_in);

  /*!
   * \brief Run state machine. 
   * \param data - Next datum. 
   */
  detect_state_t detect(const float data);

  /*!
   * \brief Get rise value
   *
   */ 
  float get_rise() { return rise; }

  /*!
   * \brief Get confirmation time value
   *
   */ 
  int get_confirmation_time() { return confirmation_time; }

  /*!
   * \brief Get alpha value
   *
   */
  float get_alpha() { return alpha; }

  /*!
   * \brief Get time constant value
   *
   */
  int get_time_constant() { return time_constant; }

  /*!
   * \brief Get noise floor value
   *
   */
  float get_noise_floor() { return noise_floor; }

  /*!
   * \brief Get peak value
   *
   */
  float get_peak() { return peak_value; }

  /*!
   * \brief Set rise value
   * \param rise_in - New rise value.
   */
  void set_rise(float rise_in);

  /*!
   * \brief Set confirmation time value
   * \param confirmation_time_in - New confirmation_time value.
   */
  void set_confirmation_time(int confirmation_time_in);

  /*!
   * \brief Set alpha value
   * \param alpha_in - New alpha value.
   */
  void set_alpha(float alpha_in);

  /*!
   * \brief Set time constant value
   * \param time_constant_in - New time constant value.
   */
  void set_time_constant(int time_constant_in);


  /*!
   * \brief Set noise floor value
   * \param noise_floor_in - New noise_floor estimate.
   */
  void set_noise_floor(float noise_floor_in, int samples);

};
