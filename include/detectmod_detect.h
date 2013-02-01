/**
 * Pulse detector blcok for Gnu Radio
 * input  - data stream (UHD source)
 * output - .det files storing individual detected pulses
 * Todd Borrowman ECE-UIUC 01/30/08~02/2010
 */


#ifndef INCLUDED_detectmod_detect_H
#define INCLUDED_detectmod_detect_H

#include <rmg_api.h>
#include <gr_block.h>
#include <peak_detect.h>
#include <accumulator.h>
#include <circ_buffer.h>
#include <gr_sync_block.h>


class detectmod_detect;

typedef enum {FILL_ACCUMULATOR, DETECT, CONFIRM_PEAK, FILL_BUFFER} module_state_t;

typedef boost::shared_ptr<detectmod_detect> detectmod_detect_sptr;

RMG_API detectmod_detect_sptr detectmod_make_detect (
    int pulse_width, 
    int save_width, 
    int channels, 
    const char *fileprefix, 
    const char *tx_name,
    float, float, char);

class RMG_API detectmod_detect : public gr_sync_block
{
private:

  friend RMG_API detectmod_detect_sptr detectmod_make_detect (
     int pulse_width, 
     int save_width, 
     int channels,
     const char *fileprefix,
     const char *tx_name,
     float, float, char);
  
  int acc_length;
  int save_length;
  int ch;
  int fill_length;
  accumulator *acc;
  circ_buffer *save_holder;
  circ_buffer *peak_holder;
  peak_detect *pkdet;
  float rate;
  float c_freq;
  char *fileprefix;
  char *tx_name; 
  int fill_counter;
  module_state_t state;
  void	       *d_fp;
  char psd;

  bool pulse_shape_discriminator(circ_buffer *);
  void write_data(circ_buffer *data_holder);
  bool open(const char *filename);
  bool open_file(const char *filename);
  void close();

//added enable to eliminate reconfig
  char enable_detect;

protected:

  detectmod_detect (int pulse_width, 
                    int save_width, 
                    int channels,
                    const char *filename,
                    const char *tx_name, 
                    float rate, 
                    float c_freq, 
                    char psd);
 
public:
  ~detectmod_detect ();	// public destructor

  void rise_factor(float r);
  void fall_factor(float f);
  void alpha_factor(float a);
  void reset();
  void enable();
  void enable(int pulse_width, 
              int save_width, 
              const char *fileprefix, 
              const char *tx_name, 
              float,char);

  void enable_cont(char *filename);
  void disable();

  int work (int noutput_items,
		    gr_vector_const_void_star &input_items,
		    gr_vector_void_star &output_items);

};

#endif /* INCLUDED_detectmod_detect_h*/
