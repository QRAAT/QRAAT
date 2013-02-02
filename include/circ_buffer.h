/* circ_buffer.h
 * Specification for a circular buffer that stores the input signal
 * from the USRP block. This file is part of QRAAT, an automated animal 
 * tracking system based on GNU Radio. 
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

#include <gr_complex.h>

class circ_buffer
{
private:
  int size;
  gr_complex *buffer;
  int index;
  int ch;
  
public:
  circ_buffer(int c, int s);
  circ_buffer(const circ_buffer &cb);
  circ_buffer &operator=(const circ_buffer &cb);
  ~circ_buffer();
  void add(gr_complex *in);
  int get_index();
  gr_complex *get_buffer();
  gr_complex *get_sample();
  void inc_index();

};
