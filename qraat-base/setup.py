
from distutils.core import setup, Extension

setup(name='QRAAT-base',
  version='1.0',
  description='QRAAT base Python package',
  packages=['qraat'],
  ext_modules=[Extension('qraat._pulse_data', 
                         sources=['swig/pulse_data.i', 'lib/pulse_data.cc'],
                         swig_opts = ['-c++'], 
                         include_dirs=['include'])],
  py_modules=['qraat.pulse_data'],
  package_dir={'qraat' : 'python'},
)

# TODO swig produces necessary 'pulse_data.py' as a side-affect and leaves it 
# in swig/. Figure out how to make this staging happen in build/, and modify 
# swig/CMakeLists.txt appropriately. 
# file python/pulse_data.py (for module qraat.pulse_data) not found
# file python/pulse_data.py (for module qraat.pulse_data) not found
