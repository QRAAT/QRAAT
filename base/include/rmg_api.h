/* rmg_api.h
 * Defines our code's API. It is for making the pulse detector work 
 * within the wider GNU Radio C++/Python context. This file is part of 
 * QRAAT, an automated animal tracking system based on GNU Radio. 
 *
 * Copyright (C) 2012 Christopher Patton
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

#ifndef INCLUDED_RMG_API_H
#define INCLUDED_RMG_API_H

/* Defined in gruel/attributes.h in the Gnu Radio source. */ 
#  define __GR_ATTR_EXPORT   __attribute__((visibility("default")))
#  define __GR_ATTR_IMPORT   __attribute__((visibility("default")))

#ifdef gnuradio_rmg_EXPORTS
#  define RMG_API __GR_ATTR_EXPORT
#else
#  define RMG_API __GR_ATTR_IMPORT
#endif

#endif /* INCLUDED_RMG_API_H */
