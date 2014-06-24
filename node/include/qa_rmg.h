/* qa_rmg.h 
 * Directly borrowed from the GNU Radio how-to-write-a-block example. 
 * Eventually we will learn how to use it. This file is part of QRAAT, an 
 * automated animal tracking system based on GNU Radio. 
 *
 * Copyright (C) 2009 Free Software Foundation
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

#ifndef INCLUDED_QA_HOWTO_H
#define INCLUDED_QA_HOWTO_H

#include <cppunit/TestSuite.h>

//! collect all the tests for the example directory

class qa_rmg {
 public:
  //! return suite of tests for all of example directory
  static CppUnit::TestSuite *suite ();
};

#endif /* INCLUDED_QA_HOWTO_H */
