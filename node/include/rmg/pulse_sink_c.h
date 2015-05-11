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


#ifndef INCLUDED_RMG_PULSE_SINK_C_H
#define INCLUDED_RMG_PULSE_SINK_C_H

#include <rmg/api.h>
#include <gnuradio/sync_block.h>

namespace gr {
  namespace rmg {

    /*!
     * \brief <+description of block+>
     * \ingroup rmg
     *
     */
    class RMG_API pulse_sink_c : virtual public gr::sync_block
    {
     public:
      typedef boost::shared_ptr<pulse_sink_c> sptr;

      /*!
       * \brief Return a shared_ptr to a new instance of rmg::pulse_sink_c.
       *
       * To avoid accidental use of raw pointers, rmg::pulse_sink_c's
       * constructor is in a private implementation
       * class. rmg::pulse_sink_c::make is the public interface for
       * creating new instances.
       */
      static RMG_API sptr make(unsigned int num_channels);

      /*!
      * \brief Enable pulse detection
      * \param pulse_width unsigned int number of samples in a pulse
      * \param save_width unsigned int number of samples to be written to det file
      * \param center_freq float center frequency of this band in Hz
      * \param rate float sampling rate in samples/second
      * \param directory char* directory to write det files to
      * \param tx_name char* transmitter name/identifier, used in det file name
      * \param rise float rise trigger parameter, must be greater than 1
      * \param alpha float alpha parameter for the peak detector exponential filter, if below 1 assumed to be weight to be applied to new sample, if above 1 assumed to be time constant is seconds
      */
      virtual void enable(
        const unsigned int pulse_width, 
        const unsigned int save_width, 
        const float center_freq,
        const float rate,
        const char *directory, 
        const char *tx_name,
        const float rise,
        const float alpha) = 0;

      /*!
      * \brief Disable pulse detection, drop input, do nothing
      */
      virtual void disable() = 0;


    };

  } // namespace rmg
} // namespace gr

#endif /* INCLUDED_RMG_PULSE_SINK_C_H */

