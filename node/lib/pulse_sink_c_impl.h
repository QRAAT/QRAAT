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

#ifndef INCLUDED_RMG_PULSE_SINK_C_IMPL_H
#define INCLUDED_RMG_PULSE_SINK_C_IMPL_H

#include <rmg/pulse_sink_c.h>
#include <boost/thread.hpp>
#include <boost/scoped_ptr.hpp>
#include <boost/accumulators/accumulators.hpp>
#include <boost/accumulators/statistics.hpp>
#include <boost/accumulators/statistics/rolling_sum.hpp>
#include <boost/circular_buffer.hpp>

#include "qraat/pulse_data.h"
#include "peak_detect.h"

namespace gr {
  namespace rmg {

    //! The states of the pulse detector. 
    typedef enum 
    {
      FILL_ACCUMULATOR, //!< fill accumulator
      DETECT,           //!< detect
      CONFIRM_PEAK,     //!< confirm peak
    } module_state_t;

    typedef boost::accumulators::accumulator_set<float, boost::accumulators::stats<boost::accumulators::tag::rolling_sum> > accumulator;

    class RMG_API pulse_sink_c_impl : public pulse_sink_c
    {
     private:

      //! Number of input channels.
      unsigned int d_num_channels;

      //! Size, in samples, of the time-matched signal filter.  
      unsigned int d_acc_length;

      //! Numbers of samples to save per pulse.
      unsigned int d_save_length;

      //! Amount of samples between the start of a pulse and the end of the file
      unsigned int d_fill_length;

      //! Coefficient of noise_floor for maximum allowable power into accumulator
      float d_clipping_factor;

      //! Current state of detector. 
      module_state_t state;
  
      //! Enable detector flag.
      char enable_detect;

      //! Time-matched filter. 
      boost::scoped_ptr<accumulator> acc;
  
      //! State machine to detect peaks in accumulator sum (filtered data).
      boost::scoped_ptr<peak_detect> pkdet;

      //! Stored pulse samples. 
      boost::scoped_ptr<pulse_data> save_holder;

      //! Directory for det files.
      std::string d_directory;

      //! Transmitter ID
      std::string d_txID;

      //! Mutex to stop processing when changing variables
      boost::mutex d_mutex;

      void write_data();

      detect_state_t update_peak_detect(const float sample_pwr, const float noise_floor);



     public:
      pulse_sink_c_impl(unsigned int num_channels);
      ~pulse_sink_c_impl();

      void enable(
        const unsigned int pulse_width, 
        const unsigned int save_width, 
        const float center_freq,
        const float rate,
        const char *directory, 
        const char *tx_name,
        const float rise,
        const float alpha);

      void disable();

      // Where all the action really happens
      int work(int noutput_items,
	       gr_vector_const_void_star &input_items,
	       gr_vector_void_star &output_items);
    };

  } // namespace rmg
} // namespace gr

#endif /* INCLUDED_RMG_PULSE_SINK_C_IMPL_H */

