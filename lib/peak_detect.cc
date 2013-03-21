/**
 * Peak_detect class implements the peak detection state machine to determine 
 * pulse locations. State is returned to df_detect.
 * Todd Borrowman ECE-UIUC 01/30/08
 */

#include <peak_detect.h>

peak_detect::peak_detect(float rise_in, float fall_in, float alpha_in){

  /**
   * TODO add error checking. What sort? Should an exception be thrown? 
   */

  rise=rise_in;
  fall=fall_in;
  alpha=alpha_in;
  state=BELOW_THRESHOLD;
  avg=0.0;
  peak_value=0.0;
  
}



detect_state_t peak_detect::detect(const float data){
/** 
 * states are
 * 0-below threashold, 
 * 1-above threashold, 
 * 2-peak, and 
 * 3-trigger.
 */

  switch(state){

    case TRIGGER:

      state = BELOW_THRESHOLD;
      //continue to below_threshold code

    case BELOW_THRESHOLD:

      if(data > avg*rise){    //possible peak
        state=PEAK;
        peak_value=data;
      }
      else{                   //update avg
        avg=alpha*data+(1-alpha)*avg;
      }
    break;
  
    case PEAK:

      state = ABOVE_THRESHOLD;
      //continue to above_threshold code

    case ABOVE_THRESHOLD:

      if(data>peak_value){    //possible peak
        state=PEAK;
        peak_value=data;
      }
      else if(data<avg*fall){ //confirmed peak
        state=TRIGGER;
      }
    
    break;

  }
  return state;
}




