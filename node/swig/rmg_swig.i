/* -*- c++ -*- */

#define RMG_API

%include "gnuradio.i"			// the common stuff

//load generated python docstrings
//%include "rmg_swig_doc.i"

%{
#include "rmg/pulse_sink_c.h"
%}


%include "rmg/pulse_sink_c.h"
GR_SWIG_BLOCK_MAGIC2(rmg, pulse_sink_c);
