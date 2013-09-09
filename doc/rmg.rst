.. qraat API documentation master file, created by
   sphinx-quickstart on Wed Aug 14 10:57:27 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

The RMG module (``qraat.rmg``) 
==============================

.. automodule:: qraat.rmg

.. toctree::
   :maxdepth: 2 



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

.. autodata:: qraat.rmg.params.usrp_sampling_rate

.. autodata:: qraat.rmg.params.usrp_max_decimation

class ``backend``
^^^^^^^^^^^^^^^^^

.. autoclass:: qraat.rmg.params.backend
   :members: lo_calc, backend_calc, tunings, pa_min, pa_max, high_lo, if1_cf, if1_bw, lo2, if2_cf, if2_bw, pv_min, pv_max, pv_step, pv_offset

class ``tuning``
^^^^^^^^^^^^^^^^

.. autoclass:: qraat.rmg.params.tuning
   :members:

class ``band``
^^^^^^^^^^^^^^

.. autoclass:: qraat.rmg.params.band
   :members:


The PIC interface
-----------------

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

.. doxygenstruct:: param_t

.. doxygenclass:: accumulator
   :members:

.. doxygenclass:: peak_detect
   :members:

