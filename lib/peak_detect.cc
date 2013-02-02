/* peak_detect.cc
 * Implementation of the peak_detect class. This file is part of QRAAT, 
 * an automated animal tracking system based on GNU Radio. 
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




