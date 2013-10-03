.. qraat API documentation master file, created by
   sphinx-quickstart on Wed Aug 14 10:57:27 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Data types
==========

The classes described in this section encapsulate pulse data at the various 
stages of processing. Pulse records (``.det`` files) are written to file by 
the pulse detector, then read by :class:`qraat.det` where various signal 
features are calculated. These are passed to :class:`qraat.est`, where the 
est's are either written to a CSV-formatted file or inserted into the 
database. These signal features represent the pulse in signal space. 
The following data, calculated by :class:`qraat.det` for each set of pulse 
samples, are also maintained in the database: 

  * ``frequency`` -- Frequency of tag transmitter. 
  * ``center`` -- Center frequency of receiver band which recorded the pulse. 
  * [``fd1r``, ``fd1i``, ``fd2r``, ``fd2i``, ``fd3r``, ``fd3i``, ``fd4r``, ``fd4i``] -- 
    Fourier decomposition of signal for each channel.
  * ``fdsp`` -- Fourier decomposition signal power. 
  * ``fdsnr`` -- Fourider decomposition signal-noise ratio (SNR) (dB).
  * ``band3`` / ``band10`` -- (?)
  * [``ed1r``, ``ed1i``, ``ed2r``, ``ed2i``, ``ed3r``, ``ed3i``, ``ed4r``, ``ed4i``] --
    Eigenvalue decomposition of signal.
  * ``edsp`` -- Eigenvalue decomposition signal power. 
  * ``edsnr`` -- Eigenvalue decomposition SNR (dB). 
  * ``ec`` -- Eigenvalue confidence (?)
  * ``tnp`` -- Total noise power. 
  * | [ (``nc11r``, ``nc11i``) (``nc12r``, ``nc12i``) (``nc13r``, ``nc13i``) (``nc14r``, ``nc14i``) 
    |  (``nc21r``, ``nc21i``) (``nc22r``, ``nc22i``) (``nc23r``, ``nc23i``) (``nc24r``, ``nc24i``) 
    |  (``nc31r``, ``nc31i``) (``nc32r``, ``nc32i``) (``nc33r``, ``nc33i``) (``nc34r``, ``nc34i``) 
    |  (``nc41r``, ``nc41i``) (``nc42r``, ``nc42i``) (``nc43r``, ``nc43i``) (``nc44r``, ``nc44i``) ] 
    | The noise covariance matrix for the four channels. 

Note that the names given correspond to the column names in the database 
schema [ref]. 

Pulse sample (class ``qraat.det``)
----------------------------------

.. automodule:: qraat.det

.. autoclass:: qraat.det.det
   :members:
   :show-inheritance: 

Pulse in signal space (class ``qraat.est``)
-------------------------------------------

.. automodule:: qraat.est

.. autoclass:: qraat.est.est
   :members:
   :show-inheritance:



**NOTE**: the following classes will be deprecated soon, replaced by ``qraat.est``. 

.. autoclass:: qraat.est.est_data 
   :members: 

.. autoclass:: qraat.est.data_arrays
   :members:

