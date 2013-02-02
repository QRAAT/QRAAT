/* circ_buffer.cc
 * Implementation of the circ_buffer class. This file is part of QRAAT, 
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

#include <circ_buffer.h>
#include <stdlib.h>
#include <string.h>

circ_buffer::circ_buffer(int c,int s){

  ch = c;
  size = s;
  buffer = (gr_complex *)calloc(size*ch,sizeof(gr_complex));
  index = 0;

}

circ_buffer::circ_buffer(const circ_buffer &cb){

  ch = cb.ch;
  size = cb.size;
  buffer = (gr_complex *)malloc(size*ch*sizeof(gr_complex));
  memcpy(buffer,cb.buffer,ch*size*sizeof(gr_complex));
  index = cb.index;

}

circ_buffer& circ_buffer::operator=(const circ_buffer &cb){

  if (ch == cb.ch && size == cb.size){
    memcpy(buffer,cb.buffer,ch*size*sizeof(gr_complex));
    index = cb.index;
  }
  else if (ch*size == cb.ch*cb.size){
    ch = cb.ch;
    size = cb.size;
    memcpy(buffer,cb.buffer,ch*size*sizeof(gr_complex));
    index = cb.index;
  }
  else{
    ch = cb.ch;
    size = cb.size;
    free(buffer);
    buffer = (gr_complex *)malloc(size*ch*sizeof(gr_complex));
    memcpy(buffer,cb.buffer,ch*size*sizeof(gr_complex));
    index = cb.index;
  }
  return *this;
}

circ_buffer::~circ_buffer(){
  free(buffer);
}

void circ_buffer::add(gr_complex *in){
/** 
 * Adds new values to the buffer
 */

  memcpy(buffer + index*ch, in, ch*sizeof(gr_complex));
  index ++;
  if(index >= size){
    index = 0;
  }
  
  return;
}

int circ_buffer::get_index(){
  return index;
}

gr_complex* circ_buffer::get_buffer(){
/** 
 * Returns the current buffer contents
 * The contents are not re-ordered before the return
 */

  return buffer;
}

gr_complex* circ_buffer::get_sample(){
//Returns address to the current sample to be replaced when adding data

  return buffer + index*ch;
}

void circ_buffer::inc_index(){
//increments index

  index++;
  if(index >= size){
    index = 0;
  }
  
  return;
}

