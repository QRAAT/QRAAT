.. qraat API documentation master file, created by
   sphinx-quickstart on Wed Aug 14 10:57:27 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

The RMG module 
==============

.. automodule:: qraat.rmg

The pulse detector array 
------------------------

.. automodule:: qraat.rmg.run

.. autoclass:: qraat.rmg.run.detector_array

  
Signal processing blocks
------------------------

.. automodule:: qraat.rmg.blocks

.. autodata:: qraat.rmg.blocks.USE_PSD

.. autoclass:: qraat.rmg.blocks.usrp_top_block
   :show-inheritance:
   :members:

.. autoclass:: qraat.rmg.blocks.no_usrp_top_block
   :show-inheritance:
   :members:

.. autoclass:: qraat.rmg.blocks.software_backend
   :show-inheritance: 
   :members:


Parameters
----------

.. automodule:: qraat.rmg.params

.. autoclass:: qraat.rmg.params.backend
   :members:

.. autoclass:: qraat.rmg.params.band
   :members:

.. autoclass:: qraat.rmg.params.tuning
   :members:


PIC interface
-------------

.. automodule:: qraat.rmg.pic_interface

.. autoclass:: qraat.rmg.pic_interface.pic_interface
   :members:


C++ stuff
---------

I need to organize this, but there you go. 

.. doxygenclass:: detectmod_detect
   :members:

.. doxygenclass:: pulse_data
   :members:

.. doxygenclass:: accumulator
   :members:

.. doxygenclass:: peak_detect
   :members:

.. doxygenstruct:: param_t
