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

#include <iostream> 
#include <complex>
#include <string>
#include <sys/time.h>
#include <boost/circular_buffer.hpp>

/* Warning: we expect that the Gnu Radio `gr_complex` type matches this
 * typedef. This is the case as of version 3.7.3, and this is unlikely 
 * to change down the road. */
typedef std::complex<float> my_complex;

//! Error handling. 
typedef enum { FileReadError, NoDataError, IndexError } PulseDataError; 


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
class pulse_data {
private:

  //! Data array as a circular buffer
  boost::circular_buffer<my_complex> *data; 
  
  /*! Name of input file. */
  std::string filename;   
  
  //! Number of input channels.
  int channel_ct;      

  //! Number of signal samples.
  int sample_ct;       
  
  //! Number of samples corresponding to the pulse. 
  int pulse_sample_ct; 
  
  //! Index of the start of pulse in samples. 
  int pulse_index;     
  
  //! Rate which the samples were produced (samples per second) 
  float sample_rate;   
  
  //! Center frequency used by detector. 
  float ctr_freq;      
  
  //! Timestamp of pulse (seconds since epoch) 
  int t_sec;    

  //! Timestamp of pulse (milliseconds) 
  int t_usec;   
  
public:
  
  /*!
   * Constructor for the Python interface. Throws PulseDataErr.
   * \param fn Input file name. 
   */ 
  pulse_data (const char *fn=NULL); 
  
  /*! 
   * Constructor for detectmod_detect. The parameters provided remain constant 
   * for the life of the pulse detector instance. The missing paramters - 
   * pulse_index, t_sec, and t_usec - are calcluated on the fly. 
   */ 
  pulse_data(
   int channel_ct,
   int sample_ct,
   int pulse_sample_ct,
   float sample_rate, 
   float ctr_freq
  );
  
  /*! 
   * Constructor from another pulse_data instance. 
   */ 
  pulse_data(const pulse_data &det);

  /*! 
   * Destructor.
   */ 
  ~pulse_data ();
  
  /*!
   * Assignment operator. 
   */ 
  pulse_data& operator=(const pulse_data &det);

  std::string str() const;

  /*!
   * Read pulse data from file. 
   * \returns The number of bytes read. -1 if the file doesn't 
   *          exists or is corrupted. 
   */
  int read(const char *fn); 

  /*!
   * Write pulse data to file. Unwrapping circular buffer as necessary. 
   */
  int write(const char *fn);

  void set_pulse_index(const int pi);

  void set_time(const struct timeval tp);

  void set_time(const int sec, const int usec);


    /* accessors */ 


  //! Return value at given index.
  my_complex& operator[] (const int i); 

  /*!
   * Return pointer to the unwrapped data buffer.
   */
  my_complex *get_data(); 


    /* Routines for the circular buffer */

  /*!
   * Append sample to circular buffer. 
   */ 
  void append(my_complex *in);

  //! Returns True if buffer is full.
  bool buffer_full();


};


/*!
 * \brief Stream outputter for pulse metadata. 
 */ 
std::ostream& operator<< ( std::ostream &out, const pulse_data &p );


#endif
