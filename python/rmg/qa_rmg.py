#!/usr/bin/env python
#
# Copyright 2004 Free Software Foundation, Inc.
# 
# This file is part of GNU Radio
# 
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
# 
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.
# 

#editted by Todd Borrowman ECE-UIUC 01/18/08~02/2010

from gnuradio import gr, gr_unittest, blks2
import qraat.rmg, sys

tx_name = "test"
test_data = "unit_test.tdat"

class qa_rmg (gr_unittest.TestCase):

    def setUp (self):
        self.fg = gr.top_block ()

    def tearDown (self):
        self.fg = None

    def test_001_detect (self):
        src_file = gr.file_source(gr.sizeof_gr_complex, test_data)
    #src_file = gr.file_source(gr.sizeof_gr_complex, "data_backup20070423/20070208164806.tdat")
        #src_file = gr.file_source(gr.sizeof_gr_complex, "20080911161545.tdat")
        di = gr.deinterleave(gr.sizeof_gr_complex)
        
        self.fg.connect(src_file, di)
        pd = qraat.rmg.detect(4,8000,160,480,0,"results", tx_name, 0,1.5,10)
        pd.enable()
        self.fg.connect((di,0),(pd,0))
        self.fg.connect((di,1),(pd,1))
        self.fg.connect((di,2),(pd,2))
        self.fg.connect((di,3),(pd,3))
        self.fg.run();
        #self.assertFloatTuplesAlmostEqual ([1],[1],1)


if __name__ == '__main__':
    gr_unittest.main ()
