#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Copyright 2015 <+YOU OR YOUR COMPANY+>.
# 
# This is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this software; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
# 

from gnuradio import gr, gr_unittest
from gnuradio import blocks
import rmg_swig as rmg

class qa_pulse_sink_c (gr_unittest.TestCase):

    def setUp (self):
        self.tb = gr.top_block ()
        src_file = blocks.file_source(gr.sizeof_gr_complex, "unit_test.tdat")
        di = blocks.deinterleave(gr.sizeof_gr_complex)
        self.tb.connect(src_file, di)
        pd = rmg.pulse_sink_c(4)
        pd.enable(160, 480, 0, 8000, "/tmp/qa_results", str(0), 1.1, 10)
        self.tb.connect((di,0),(pd,0))
        self.tb.connect((di,1),(pd,1))
        self.tb.connect((di,2),(pd,2))
        self.tb.connect((di,3),(pd,3))

    def tearDown (self):
        self.tb = None

    def test_001_t (self):
        # set up fg
        self.tb.run()
        # check data
        return True


if __name__ == '__main__':
    gr_unittest.run(qa_pulse_sink_c, "qa_pulse_sink_c.xml")
