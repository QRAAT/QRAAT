from distutils.core import setup, Extension
from distutils.command.install import install as _install
import os, sys

# Post install trigger for source tree clean up. Swig produces files 
# pulse_data.py and pulse_data_wrap.cpp as a side-effect and leaves 
# them in the source tree. 
def _post_install(build_dir):
  pass
  target = os.getcwd() + "/python/pulse_data.py"
  print "Removing", target, "...", 
  try: 
    os.remove(target)
    print "ok."
  except OSError, e:
    if e.errno == 2:
      print "not found."
    else: print e

  target = os.getcwd() + "/python/pulse_data_wrap.cpp"
  print "Removing", target, "...", 
  try: 
    os.remove(target)
    print "ok."
  except OSError, e:
    if e.errno == 2:
      print "not found."
    else: print e

class install(_install):
  def run(self):
    _install.run(self)
    self.execute(_post_install, (self.install_lib,), 
                 msg="Running post install trigger.")

setup(name='QRAAT-base',
  version='1.0',
  description='QRAAT base Python package',
  packages=['qraat'],
  ext_modules=[Extension('qraat._pulse_data', 
                         sources=['python/pulse_data.i', 'lib/pulse_data.cc'],
                         swig_opts = ['-c++'], 
                         include_dirs=['include'])],
  #py_modules=['qraat.pulse_data'],
  package_dir={'qraat' : 'python'},
  cmdclass={"install" : install},
)
