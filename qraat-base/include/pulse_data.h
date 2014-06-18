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
#include <complex>

using namespace std;

/* Warning: we expect that the Gnu Radio `gr_complex` type matches this
 * typedef. This is the case as of version 3.7.3, and this is unlikely 
 * to change down the road. */
typedef complex<float> my_complex;

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
 * bytes. I.e., ``file.read((char*)&version, sizeof(int));`` if version != 0, 
 * then use param_t.  
 */
typedef struct {
  //! Number of input channels.
  int channel_ct;      

  //! Number of signal samples.
  int sample_ct;       
  
  //! Number of samples corresponding to the pulse. 
  int pulse_sample_ct; 
  
  //! Index of the start of pulse in samples. 
  int pulse_index;     
  
  //! Rate which the samples were prdocued (units?) 
  float sample_rate;   
  
  //! Center frequency used by detector. 
  float ctr_freq;      
  
  //! Timestamp of pulse (seconds since epoch) 
  int t_sec;    

  //! Timestamp of pulse (milliseconds) 
  int t_usec;   
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
protected:

  //! Data array, size = params.channel_ct * params.sample_ct. 
  my_complex *data; 
  
  //! Point to start of the circular buffer (oldest sample). 
  int index; 

  int size; // Store the size of the data array.

public:
  
  /*! Name of input file. Declared as public for the Python interface. */
  char *filename;   
  
  /*!
   * Record metadata. Declared as public so that it's accessible
   * in the Python interface. 
   */
  param_t params;   
  
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

  /*!
   * Read pulse data from file. 
   * \returns The number of bytes read. -1 if the file doesn't 
   *          exists or is corrupted. 
   */
  int read(const char *fn); 

  /*!
   * Write pulse data to file. Unwrap circular buffer if necessary. 
   */
  int write(const char *fn="");


    /* accessors */ 

  /*!
   * Get metadata.
   */
  const param_t& param() const; 

  /*!
   * Arbitrary access over data array. To get the jth channel of the 
   * ith sample, do "det[(i * det.params.channel_ct) + j]". \b NOTE: in 
   * Python, \a my_complex is cast as a tuple (\a real, \a imag).  
   */
  my_complex& sample(int i); 

  //! Same as pulse_data::sample().
  my_complex& operator[] (int i); 

  //! Get the real part of an arbitrary datum. 
  float real(int i); 
  
  //! Get the imaginary part of an arbitrary datum. 
  float imag(int i); 

  /*!
   * \brief Set the real part of an arbitrary datum. 
   */
  void set_real(int i, float val);

  /*!
   * \brief Set the imaginary part of an arbitrary datum. 
   */
  void set_imag(int i, float val);

  /*!
   * Return pointer to the data buffer. Note that 
   * the buffer is not unwrapped. 
   */
  my_complex *get(); 


    /* Routines for the circular buffer */

  /*!
   * Add sample to circular buffer and increment index. 
   */ 
  void add(my_complex *in);

  /*! TODO deprecate */
  int get_index();

  /*! TODO deprecate */
  my_complex *get_buffer();

  /*!
   * Return sample at current index (oldest sample.) 
   */
  my_complex *get_sample();

  /*!
   * \brief Increment index. 
   */
  void inc_index();

};

#endif
