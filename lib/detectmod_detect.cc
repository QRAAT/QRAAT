/**
 * Implementation of peak detector block
 * input - data stream
 * output - .det files storing individual detected pulses
 * Todd Borrowman ECE-UIUC 01/30/08~02/2010
 * TAB 01/2012 added enable/disable
 *
 * TODO Chris 7/24/12
 * clarify the file outputting  (status.txt, .det's). There should be 
 * two file descriptors for the debug info (status.txt) and pulse 
 * data respectively.
 */

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include <detectmod_detect.h>
#include <gr_io_signature.h>
#include <cstdio>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <stdexcept>
#include <sys/time.h>
#include <string.h>
#include <math.h>

#ifndef O_BINARY
#define	O_BINARY 0
#endif 

detectmod_detect_sptr 
detectmod_make_detect (int pulse_width, int save_width, int channels, char *filename, float rate, float center_freq, char use_psd)
/**
 * Public constructor used by Gnu Radio 
 */
{
  return detectmod_detect_sptr (new detectmod_detect (pulse_width, save_width, channels, filename, rate, center_freq, use_psd));
}

detectmod_detect::detectmod_detect (int pulse_width, int save_width, int channels,char *filename, float r, float center_freq, char use_psd)
  : gr_sync_block ("detectmod_detect",
	      gr_make_io_signature (channels, channels, sizeof (gr_complex)),
	      gr_make_io_signature (0,0,0))
/**
 * Private constructor used internally 
 */
{
  rate = r;
  c_freq = center_freq;
  ch = channels;
  acc_length = pulse_width;//size of the accumulator
  
  
  /** 
   * length of the file needs to be at least 3 times as long as 
   * the pulse to accomidate the noise covariance calculation
   */
  if(save_width < 3*acc_length){
    save_length = 3*acc_length;
  }
  else{
    save_length = save_width;
  }
  int l = strlen(filename)+1;
  fileprefix = (char *)malloc(l*sizeof(char));
  strcpy(fileprefix,filename);

  state = FILL_ACCUMULATOR;
  fill_counter = -7;
  fill_length = ((int)(0.5*acc_length));
  d_fp = 0;
  acc = new accumulator *[ch-1];
  for(int j=0;j<ch-1;j++){
    acc[j] = new accumulator(acc_length);
  }
  save_holder = new circ_buffer(ch, save_length);
  peak_holder = new circ_buffer(ch, save_length);
  pkdet = new peak_detect(1.1,1.05,.05);

  psd = use_psd;
  enable_detect = 0;
}

detectmod_detect::~detectmod_detect(){

  close();
  free(fileprefix);
  delete[] acc;
  delete save_holder;
  delete peak_holder;
  delete pkdet;
}

int 
detectmod_detect::work (int noutput_items,
			       gr_vector_const_void_star &input_items,
			       gr_vector_void_star &output_items)
{
  
  gr_complex *current_sample; 
  //float r,i,sample_pwr,acc_total;
  float acc_total;
  gr_complex acc_value;
  detect_state_t det_state = BELOW_THRESHOLD;
  int sh_index;

  //added enable
  if (enable_detect==1){

    //Loop through all of the samples
    for (int j=0;j<noutput_items;j++){
      
          //Calculate total power received
      //sample_pwr=0.0;
      acc_total = 0.0;
      current_sample = save_holder->get_sample();
      current_sample[0] = ((gr_complex *) input_items[0])[j];
      for (int m=1;m<ch;m++){
        current_sample[m] = ((gr_complex *) input_items[m])[j];
        //r = current_sample[m].real();
        //i = current_sample[m].imag();
        //sample_pwr += (r*r) + (i*i);
        acc_value = acc[m-1]->add(current_sample[m]*conj(current_sample[0]));
        acc_total += real(acc_value*conj(acc_value));
      }
      save_holder->inc_index();
      //acc_total = acc->add(sample_pwr);

      switch(state){
        
            //initialize the time-matched filter and circular buffer
        case FILL_ACCUMULATOR:

          sh_index = save_holder->get_index();
          if (sh_index == (save_length-1)){
            state = DETECT;
                    //initial estimate of the noise floor for detector
            pkdet->avg = acc_total;
            printf("%s Seed: %e\n",fileprefix,acc_total);
          }
        break;
      
            //Run detector
        case DETECT:

          det_state = pkdet->detect(acc_total);
          if(det_state == PEAK){//new temporary peak found
            fill_counter = fill_length+1;
          }
          else if(det_state == TRIGGER){
            state = FILL_BUFFER;
          }
        
          fill_counter--;
                  //if the buffer is full but the peak isn't confirmed, save buffer state and confirm peak
          if (fill_counter == 0 && state!=FILL_BUFFER){
            *peak_holder = *save_holder;
            state = CONFIRM_PEAK;
          }

        break;      

        //buffer is full, wait for the detector to trigger
        case CONFIRM_PEAK:

          det_state = pkdet->detect(acc_total);
          if(det_state == PEAK){//new temporary peak found
            state = DETECT;
            fill_counter = fill_length;
          }
          else if(det_state == TRIGGER){//peak confirmed
            if(psd == 0 || pulse_shape_discriminator(peak_holder)){
              write_data(peak_holder);
            }
            state = DETECT;
          }

        break;

            //confirmed peak, fill the buffer
        case FILL_BUFFER:

          fill_counter--;
          if (fill_counter <= 0){
            if(psd == 0 || pulse_shape_discriminator(save_holder)){
              write_data(save_holder);
            }
            state = DETECT;
          }

        break;

      }//switch
    }//for
  }//enable if statement

  //Continuous record
  else if(enable_detect == 2 && d_fp){

    gr_complex *value_addr;
      
    for (int i = 0; i < noutput_items; i++){
      for (int n = 0; n < ch; n++){
        value_addr = ((gr_complex *)input_items[n]) + i;
        fwrite(value_addr,sizeof(gr_complex),1,(FILE *)d_fp);
      }
    }

  }

  return noutput_items;
}


void detectmod_detect::write_data(circ_buffer *data_holder){
/** 
 * Writes the pulse data as a .det file
 */



  //Get time
  struct timeval *tp = (struct timeval *)malloc(sizeof(struct timeval));
  gettimeofday(tp, NULL);
  void *temp;
  struct tm *time_struct = gmtime(&(tp->tv_sec));
  char *time_string = (char *)malloc(40*sizeof(char));
  strftime(time_string,40,"%Y%m%d%H%M%S",time_struct);
  char *u_sec = (char *)malloc(10*sizeof(char));
  sprintf(u_sec,"%.6d",(unsigned int)tp->tv_usec);
  strncat(time_string,u_sec,6);
  int len = strlen(fileprefix)+strlen(time_string)+10;
  
  //filename is the given prefix and the time to the microsecond (false precision)
  char *filename = (char *)malloc(len*sizeof(char));
  sprintf(filename,"%s%s.det",fileprefix,time_string);

  //open .det file
  if(!open_file(filename))
    return;
  if (!d_fp)
    return;

  //write time as a timeval
  fwrite(tp,sizeof(struct timeval),1,(FILE *)d_fp);
  float snr = 10.0*log10(pkdet->peak_value/pkdet->avg);
  float noise_db = 10.0*log10(pkdet->avg/1e-5);
  strftime(time_string,40,"%H:%M:%S %d %b %Y",time_struct);
  printf("%s\n\t%s\n\t\tNoise Floor: %.2f dB, SNR: %.2f dB\n",time_string, filename, noise_db, snr);

  //get data buffer and index from data_holder
  gr_complex *data = data_holder->get_buffer();
  int index = data_holder->get_index();

  //unwrap circular buffer and write data to file
  if (index != 0){
    temp = data + (index)*ch;
    fwrite(temp,sizeof(gr_complex),(save_length-index)*ch, (FILE *)d_fp);
    fwrite(data,sizeof(gr_complex),(index)*ch, (FILE *)d_fp);
  }
  else
    fwrite(data,sizeof(gr_complex),index*ch, (FILE *)d_fp);

  //close file and free string variables
  close();
  free(time_string);
  free(filename);
  free(u_sec);
  free(tp);

  return;
}

bool
detectmod_detect::open(const char *filename)
/** 
 * opens a file, mostly copied from gnuradio
 */
{


  int fd;
  if ((fd = ::open (filename,
		    O_WRONLY|O_CREAT|O_TRUNC|O_LARGEFILE|O_BINARY, 0664)) < 0){
    perror (filename);
    return false;
  }

  if (d_fp){		// if we've already got a new one open, close it
    fclose((FILE *) d_fp);
    d_fp = 0;
  }
  
  if ((d_fp = fdopen (fd, "wb")) == NULL){
    perror (filename);
    ::close(fd);		// don't leak file descriptor if fdopen fails.
  }

  return d_fp != 0;
}

void
detectmod_detect::close()
{
  /* close file */

  if (d_fp){
    fclose((FILE *) d_fp);
    d_fp = 0;
  }
  
}

bool detectmod_detect::open_file(const char *filename)
/** 
 * opens a .det file and writes the header information
 */
{
    
  if(!open(filename)){
    printf("Can't open file \"%s\"\n",filename);
    return 0;
  }
  else{
    fwrite(&ch,sizeof(int),1,(FILE *)d_fp);
    fwrite(&save_length,sizeof(int),1,(FILE *)d_fp);
    fwrite(&acc_length,sizeof(int),1,(FILE *)d_fp);
    int pulse_start = save_length - acc_length-fill_length;
    fwrite(&pulse_start,sizeof(int),1,(FILE *)d_fp);
    fwrite(&rate,sizeof(float),1,(FILE *)d_fp);
    fwrite(&c_freq,sizeof(float),1,(FILE *)d_fp);
  return 1;
  }

}


bool detectmod_detect::pulse_shape_discriminator(circ_buffer *data_holder){
/** 
 * determines whether the detected pulse looks like a rectangle or not
 */

  const float MAX_PERCENTAGE = 0.20;
  const int SHAPE_THREASHOLD = 14;

  gr_complex *pulse_buffer = data_holder->get_buffer();
  int index = data_holder->get_index();

  float *pulse_pwr = new float[acc_length];
  int pulse_start = save_length - acc_length-fill_length;
  int j,k;
  float r,i;
  float max_value = 0;
  int count = 0;
  bool result = false;
  for(j = 0; j < acc_length; j++){
    pulse_pwr[j] = 0;
    for(k = 0; k < ch; k++){
      r = pulse_buffer[((j+pulse_start+index)%save_length)*ch+k].real();
      i = pulse_buffer[((j+pulse_start+index)%save_length)*ch+k].imag();
      pulse_pwr[j] += r*r+i*i;
    }
    if(pulse_pwr[j] > max_value)
      max_value = pulse_pwr[j];
  }
  max_value = max_value*MAX_PERCENTAGE;
  for(j = 0; j < acc_length; j++){
    if(pulse_pwr[j] > max_value)
      count++;
  }
  if(count>SHAPE_THREASHOLD)
    result = true;

  delete pulse_pwr;
  return result;

}


void detectmod_detect::rise_factor(float r)
/** 
 * Public call for gnuradio to set the rise factor in the detector
 */
{
  pkdet->rise = r;

  return;
}

void detectmod_detect::fall_factor(float f)
/**
 * public call for gnuradio to set the fall factor in the detector
 */
{
  pkdet->fall = f;

  return;
}

void detectmod_detect::alpha_factor(float a)
/** 
 * public call for gnuradio to set the noise floor filter coefficient in the detector
 */
{
  pkdet->alpha = a;

  return;
}

void detectmod_detect::reset()
/**
 * Public call for gnuradio to reset the detector
 */
{
  //write data out if state = FILL_BUFFER or CONFIRM_PEAK
  if (state == CONFIRM_PEAK){
    if(psd == 0 || pulse_shape_discriminator(peak_holder)){
      write_data(peak_holder);
    }
  }
  else if (state == FILL_BUFFER){
    //psd won't look at correct place so just write out data
    write_data(save_holder);
  }

  state = FILL_ACCUMULATOR;
  fill_counter = -7;

  return;
}

void detectmod_detect::enable()
{
  //enable detector
  reset();
  enable_detect = 1;
  return;
}

void detectmod_detect::enable(int pulse_width, int save_width,char *filename, float center_freq, char use_psd)
{
  free(fileprefix);
  //delete[] acc;
  delete save_holder;
  delete peak_holder;

  c_freq = center_freq;
  
  acc_length = pulse_width;//size of the accumulator
  
  /** 
   * length of the file needs to be at least 3 times as long as the
   * pulse to accomidate the noise covariance calculation 
   */
  if(save_width < 3*acc_length){
    save_length = 3*acc_length;
  }
  else{
    save_length = save_width;
  }
  int l = strlen(filename)+1;

  state = FILL_ACCUMULATOR;
  fill_counter = -7;
  fill_length = ((int)(0.5*acc_length));

  psd = use_psd;

  fileprefix = (char *)malloc(l*sizeof(char));
  strcpy(fileprefix,filename);
  //acc = new accumulator(acc_length);
  //acc = new accumulator *[ch-1];
  for(int j=0;j<ch-1;j++){
    delete acc[j];
    acc[j] = new accumulator(acc_length);
  }
  save_holder = new circ_buffer(ch, save_length);
  peak_holder = new circ_buffer(ch, save_length);

  enable_detect = 1;
  return;
}

void detectmod_detect::enable_cont(char *filename)
{
  enable_detect = 2;
  if(!open(filename)){
    printf("Can't open file \"%s\"\n",filename);
    enable_detect = 0;
  }
  else{
    printf("Opened file \"%s\" for continuous recording\n",filename);
  }

  return;
}

void detectmod_detect::disable()
/** 
 * disable detector and close continuous record
 */
{

  if (enable_detect == 2){
    close();
  }
  enable_detect = 0;

  return;
}
