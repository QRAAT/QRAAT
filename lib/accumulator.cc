/* accumulator.cc 
 * Implementation of the accumulator class. This file is part of QRAAT, 
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

