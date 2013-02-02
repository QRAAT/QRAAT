/* accumulator.h
 * Maintain a running sum of the USRP input signal. This is treated as 
 * a time-matched filter for use by the detector class. This file is part 
 * of QRAAT, an automated animal tracking system based on GNU Radio. 
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

class accumulator
{
private:
  int size;
  float *buffer;
  double total_sum;
  int index;

  
public:
  accumulator(int s);
  ~accumulator();
  float add(float in);
  float value();
};
