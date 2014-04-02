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
#include <exception>

peak_detect::peak_detect(float rise_in, int confirmation_time_in, float alpha_in){

  if (rise_in > 1){
    rise=rise_in;
  }
  else{
    throw invalid_argument("rise must be greater than 1");
  }
  if (confirmation_time_in >= 0){
    confirmation_time=confirmation_time_in;
  }
  else{
    throw invalid_argument("confirmation_time must not be negative");
  }
  if (alpha_in >= 0 && alpha_in <= 1){
    alpha=alpha_in;
  }
  else{
    throw invalid_argument("alpha must be between 0 and 1 inclusive");
  }
  state=BELOW_THRESHOLD;
  noise_floor=0.0;
  peak_value=0.0;
  confirmation_counter = 0;
  
}

void set_rise(float rise_in){

  if (rise_in > 1){
    rise=rise_in;
  }
  else{
    throw invalid_argument("rise must be greater than 1");
  }

}


void set_confirmation_time(int confirmation_time_in){

  if (confirmation_time_in >= 0){
    confirmation_time=confirmation_time_in;
  }
  else{
    throw invalid_argument("confirmation_time must not be negative");
  }

}


void set_alpha(float alpha_in){

  if (alpha_in >= 0 && alpha_in <= 1){
    alpha=alpha_in;
  }
  else{
    throw invalid_argument("alpha must be between 0 and 1 inclusive");
  }

}


void set_noise_floor(float noise_floor_in){

  if (noise_floor_in > 0.0){
    noise_floor=noise_floor_in;
  else{
    throw invalid_argument("noise_floor must be greater than zero");
  }
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
      confirmation_counter = 0;
      //continue to above_threshold code

    case ABOVE_THRESHOLD:

      confirmation_counter++;
      if(data>peak_value){    //possible peak
        state=PEAK;
        peak_value=data;
      }
      else if(confirmation_counter >= confirmation_time){ //confirmed peak
        state=TRIGGER;
      }
    
    break;

  }
  return state;
}




