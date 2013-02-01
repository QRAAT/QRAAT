/**
 * Accumulator class implements a circular buffer with a stored value for the 
 * sum of the buffer's contents This is treated as a time-matched filter for 
 * use by the detector class.
 * Todd Borrowman ECE-UIUC 2-21-08
 */

#include <accumulator.h>
#include <stdlib.h>
#include <stdio.h>


accumulator::accumulator(int s){

  size = s;
  buffer = (float *)calloc(size,sizeof(float));
  index = 0;
  total_sum = 0.0;

}

accumulator::~accumulator(){
  free(buffer);
}

float accumulator::add(float in){
/** 
 * Adds a new value to the buffer and adjuts the total sum
 */

  total_sum += in - buffer[index];
  buffer[index]=in;
  index++;
  if(index >= size){
    index = 0;
  }
  
  return (float)total_sum;
}

float accumulator::value(){
  return (float)total_sum;
}

