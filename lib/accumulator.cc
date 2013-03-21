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
  buffer = (std::complex<float> *)calloc(size,sizeof(std::complex<float>));
  index = 0;
  total_sum = 0.0;

}

accumulator::~accumulator(){
  free(buffer);
}

std::complex<float> accumulator::add(std::complex<float> in){
/** 
 * Adds a new value to the buffer and adjuts the total sum
 */

  total_sum += in - buffer[index];
  buffer[index]=in;
  index++;
  if(index >= size){
    index = 0;
  }
  
  return (std::complex<float>)total_sum;
}

std::complex<float> accumulator::value(){
  return (std::complex<float>)total_sum;
}

