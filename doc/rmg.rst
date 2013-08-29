.. qraat API documentation master file, created by
   sphinx-quickstart on Wed Aug 14 10:57:27 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

The RMG module 
==============

.. automodule:: qraat.rmg

The pulse detector array 
------------------------

.. automodule:: qraat.rmg.rmg_run

.. autoclass:: qraat.rmg.rmg_run.detector_array

  
Signal processing blocks
------------------------

.. automodule:: qraat.rmg.rmg_graphs

.. autodata:: qraat.rmg.rmg_graphs.USE_PSD

.. autoclass:: qraat.rmg.rmg_graphs.usrp_top_block
   :show-inheritance:
   :members:

.. autoclass:: qraat.rmg.rmg_graphs.no_usrp_top_block
   :show-inheritance:
   :members:

.. autoclass:: qraat.rmg.rmg_graphs.software_backend
   :show-inheritance: 
   :members:


Parameters
----------

.. automodule:: qraat.rmg.rmg_param

.. autoclass:: qraat.rmg.rmg_param.backend
   :members:

.. autoclass:: qraat.rmg.rmg_param.band
   :members:

.. autoclass:: qraat.rmg.rmg_param.tuning
   :members:


PIC interface
-------------

.. automodule:: qraat.rmg.rmg_pic_interface

.. autoclass:: qraat.rmg.rmg_pic_interface.rmg_pic_interface
   :members:


rmg_setup
---------

.. automodule:: qraat.rmg.rmg_setup

rmg_editors
-----------

.. automodule:: qraat.rmg.rmg_editors

rmg_validators
--------------

.. automodule:: qraat.rmg.rmg_validators 


C++ stuf
--------

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
