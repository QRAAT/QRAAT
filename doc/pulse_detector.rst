.. qraat API documentation master file, created by
   sphinx-quickstart on Wed Aug 14 10:57:27 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

The pulse detector (``qraat.rmg.detect``)
=========================================

.. autoclass:: qraat.rmg.detect

.. automodule:: qraat.rmg.rmg_swig

.. doxygenclass:: detectmod_detect
   :members:


Data encapsulation
------------------

.. automodule:: qraat.pulse_swig

.. autoclass:: qraat.pulse_swig.pulse_data

.. doxygenclass:: pulse_data
   :members:

.. doxygenstruct:: param_t


Helper classes
--------------

These classes implement functionality for the pulse detector and don't 
require a SWIG Python interface. 

.. doxygenclass:: accumulator
   :members:

.. doxygenclass:: peak_detect
   :members:




