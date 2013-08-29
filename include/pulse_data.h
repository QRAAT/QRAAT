/* pulse_data.h - This file is part of QRAAT, an automated animal tracking 
 * system based on GNU Radio. 
 *
 * Copyright (C) 2012 Christopher Patton
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

#ifndef pulse_data_h
#define pulse_data_h

#include <rmg_api.h>
#include <iostream> 
#include <fstream> 
#include <sys/time.h>
#include <ctime>
#include <gr_complex.h>

using namespace std;

//! Error handling. 
typedef enum { FileReadError, NoDataError, IndexError } PulseDataError; 

/*! 
 * \brief Pulse data metadata paramters. 
 * 
 * This is the legacy header for .det files. In the future, we plan to 
 * extend this header information to include database identifiers for the
 * source transmitter and receiver site. To do this, we'll specify in the
 * pulse_data's constructor the header version to use, which will
 * correspond to to a particular struct. pulse_data::read() will determine 
 * if a .det's header is versioned or legacy by looking at the first four 
 * bytes. I.e., file.read((char*)&version, sizeof(int)); if version != 0, 
 * then use param_t.  
 */
typedef struct {
  int channel_ct,      //! Number of input channels.
      sample_ct,       //! Number of signal samples.
      pulse_sample_ct, //! Number of samples corresponding to the pulse. 
      pulse_index;     //! Index of the start of pulse in samples. 
  float sample_rate,   //! Rate which the samples were prdocued (units?) 
        ctr_freq;      //! Center frequency used by detector. 
  int t_sec, t_usec;   //! Timestamp of pulse (seconds since epcoh, milliseconds) 
} param_t; 

/*!
 * \brief Stream outputter for pulse metadata. 
 */ 
ostream& operator<< ( ostream &out, const param_t &p );

class detectmod_detect;

/*!
 * \brief Container for pulse data. 
 *
 * This class is used directly by the pulse detector for data storage
 * as well as for encapsulation in the Python API (see Swig interface 
 * in swig/rmg_swig.i). As the data buffer is used to store a continuous
 * signal in the detector, this class implements routines for circular 
 * buffer manipulation. However, the Python interface only has read/write
 * accessors for the data and read access for the metadata. 
 */ 
class RMG_API pulse_data {
friend class detectmod_detect; 

  param_t params;   //! Record metadata. 
  gr_complex *data; //! Data array, size = params.channel_ct * params.sample_ct. 
  char *filename;   //! Name of input file.  
  
  int index; //! Point to start of the circular buffer (oldest sample). 

public:
  
  /*!
   * \brief Constructor for the Python API. 
   *
   * Throws PulseDataErr.
   * \param fn - Input file name. 
   * */ 
  pulse_data (const char *fn=NULL); 
  
  /*! 
   * \brief Constructor for pulse detector. 
   *
   * The parameters provided remain constant for the life of the pulse
   * detector instance. The missing paramters - pulse_index, t_sec, and 
   * t_usec - are calcluated on the fly. 
   */ 
  pulse_data(
   int channel_ct,
   int sample_ct,
   int pulse_sample_ct,
   float sample_rate, 
   float ctr_freq
  );
  
  /*! 
   * \brief Default cosntructor. 
   */ 
  pulse_data(const pulse_data &det);

  /*! 
   * \brief Destructor.
   */ 
  ~pulse_data ();
  
  /*!
   * \brief Assignment operator. 
   */ 
  pulse_data& operator=(const pulse_data &det);

  /*!
   * \brief Rad pulse data from file. 
   */
  int read(const char *fn); 

  /*!
   * \brief Write pulse data to file. 
   *
   * Unwrap circular buffer if necessary. 
   */
  int write(const char *fn="");

  /* Accessors - throw PulseDataErr */

  /*!
   * \brief Get metadata.
   */
  const param_t& param() const; 

  /*!
   * \brief Arbitrary access over data array. 
   *
   * To get the jth channel of the ith sample, 
   * do det[(i * det.param().channel_ct) + j].
   */
  gr_complex& operator[] (int i); 

  /*!
   * \brief Get the real part of an arbitrary datum. 
   */
  float real(int i); 
  
  /*!
   * \brief Get the imaginary part of an arbitrary datum. 
   */
  float imag(int i); 

  /*!
   * \brief Set the real part of an arbitrary datum. 
   */
  void set_real(int i, float val);

  /*!
   * \brief Set the imaginary part of an arbitrary datum. 
   */
  void set_imag(int i, float val);

  /* Routines for the circular buffer. */

  /*!
   * \brief Add sample to circular buffer and increment index. 
   *
   * \param in - next sample. 
   */ 
  void add(gr_complex *in);

  /*! 
   * \brief Get current index.
   *
   * Obsolete, since pulse_data is a friend of class detectmod_detect.
   */ 
  int get_index();

  /*!
   * \brief Return pointer to front of buffer. 
   */
  gr_complex *get_buffer();

  /*!
   * \brief Return sample at current index (oldest sample.) 
   */
  gr_complex *get_sample();

  /*!
   * \brief Return current index. 
   */
  void inc_index();


};

#endif
