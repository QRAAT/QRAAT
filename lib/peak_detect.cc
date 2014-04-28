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
#include <stdexcept>

peak_detect::peak_detect(float rise_in, int confirmation_time_in, int time_constant_in){

  if (rise_in > 1){
    rise=rise_in;
  }
  else{
    throw std::invalid_argument("rise must be greater than 1");
  }
  if (confirmation_time_in >= 0){
    confirmation_time=confirmation_time_in;
  }
  else{
    throw std::invalid_argument("confirmation_time must not be negative");
  }
  if (time_constant_in > 0){
    alpha=1/(float)time_constant_in;
    time_constant = time_constant_in;
  }
  else{
    throw std::invalid_argument("time constant must be greater than 0");
  }
  state=BELOW_THRESHOLD;
  noise_floor=0.0;
  peak_value=0.0;
  confirmation_counter = 0;
  samples_in_noise_floor=0;
  
}

void peak_detect::set_rise(float rise_in){

  if (rise_in > 1){
    rise=rise_in;
  }
  else{
    throw std::invalid_argument("rise must be greater than 1");
  }

}


void peak_detect::set_confirmation_time(int confirmation_time_in){

  if (confirmation_time_in >= 0){
    confirmation_time=confirmation_time_in;
  }
  else{
    throw std::invalid_argument("confirmation_time must not be negative");
  }

}

void peak_detect::set_alpha(float alpha_in){

  if (alpha_in >= 0 && alpha_in <= 1){
    alpha=alpha_in;
    time_constant = (int)(1/alpha);
  }
  else{
    throw std::invalid_argument("alpha must be between 0 and 1 inclusive");
  }

}

void peak_detect::set_time_constant(int time_constant_in){

  if (time_constant_in > 0){
    alpha=1/(float)time_constant;
    time_constant = time_constant;
  }
  else{
    throw std::invalid_argument("time constant must be greater than 0");
  }

}


void peak_detect::set_noise_floor(float noise_floor_in, int samples){

  if (noise_floor_in > 0.0){
    noise_floor=noise_floor_in;
  }
  else{
    throw std::invalid_argument("noise_floor must be greater than zero");
  }
  if (samples > 0){
    samples_in_noise_floor = samples;
  }
  else{
    throw std::invalid_argument("samples must be a positive integer");
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

    case BELOW_THRESHOLD:

      if(data > noise_floor*rise){    //possible peak
        state=PEAK;
        peak_value=data;
      }
      else{                   //update noise_floor
        if (samples_in_noise_floor < time_constant){
          noise_floor = noise_floor*samples_in_noise_floor/(samples_in_noise_floor + 1.0) + data/(samples_in_noise_floor + 1.0);
          samples_in_noise_floor++;
        }
        else{
          noise_floor=alpha*data+(1-alpha)*noise_floor;
        }
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

    case TRIGGER:

      state = POST_TRIGGER;
      //continue to post_trigger code

    case POST_TRIGGER:

      if(data < noise_floor*rise*FALL_RATIO){
        state = BELOW_THRESHOLD;
      }

      if (samples_in_noise_floor < time_constant){
        noise_floor = noise_floor*samples_in_noise_floor/(samples_in_noise_floor + 1.0) + data/(samples_in_noise_floor + 1.0);
        samples_in_noise_floor++;
      }
      else{
        noise_floor=alpha*data+(1-alpha)*noise_floor;
      }
    break;

  }
  return state;
}




