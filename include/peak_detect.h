/* peak_detect.h
 * Peak detection state machine to determine pulse locations. 
 * This file is part of QRAAT, an automated animal tracking system 
 * based on GNU Radio. 
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

typedef enum {BELOW_THRESHOLD, ABOVE_THRESHOLD, PEAK, TRIGGER} detect_state_t;

class detectmod_detect;

class peak_detect
{

friend class detectmod_detect; 

private:

  float rise;
  float fall;
  float alpha;
  float peak_value;
  float avg;

  detect_state_t state;

public:

  peak_detect(float rise_in, float fall_in, float alpha_in);
  detect_state_t detect(const float data);
};
