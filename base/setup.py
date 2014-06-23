from distutils.core import setup, Extension

setup(name='QRAAT-base',
  version='1.0',
  description='QRAAT base Python package',
  packages=['qraat'],
  ext_modules=[Extension('qraat._pulse_data', 
                         sources=['python/pulse_data.i', 'lib/pulse_data.cc'],
                         swig_opts = ['-c++'], 
                         include_dirs=['include'])],
  #@py_modules=['qraat.rmg', 'qraat.srv', 'qraat.pulse_data'],
  package_dir={'qraat' : 'python'},
)
