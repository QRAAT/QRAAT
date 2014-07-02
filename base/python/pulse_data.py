# This file was automatically generated by SWIG (http://www.swig.org).
# Version 2.0.4
#
# Do not make changes to this file unless you know what you are doing--modify
# the SWIG interface file instead.


"""

  ``pulse_data`` is a class used by the pulse detector for data storage and 
  for writing pulse records out to disk. It's also the parent class :mod:`qraat.det.det`. 

"""


from sys import version_info
if version_info >= (2,6,0):
    def swig_import_helper():
        from os.path import dirname
        import imp
        fp = None
        try:
            fp, pathname, description = imp.find_module('_pulse_data', [dirname(__file__)])
        except ImportError:
            import _pulse_data
            return _pulse_data
        if fp is not None:
            try:
                _mod = imp.load_module('_pulse_data', fp, pathname, description)
            finally:
                fp.close()
            return _mod
    _pulse_data = swig_import_helper()
    del swig_import_helper
else:
    import _pulse_data
del version_info
try:
    _swig_property = property
except NameError:
    pass # Python < 2.2 doesn't have 'property'.
def _swig_setattr_nondynamic(self,class_type,name,value,static=1):
    if (name == "thisown"): return self.this.own(value)
    if (name == "this"):
        if type(value).__name__ == 'SwigPyObject':
            self.__dict__[name] = value
            return
    method = class_type.__swig_setmethods__.get(name,None)
    if method: return method(self,value)
    if (not static):
        self.__dict__[name] = value
    else:
        raise AttributeError("You cannot add attributes to %s" % self)

def _swig_setattr(self,class_type,name,value):
    return _swig_setattr_nondynamic(self,class_type,name,value,0)

def _swig_getattr(self,class_type,name):
    if (name == "thisown"): return self.this.own()
    method = class_type.__swig_getmethods__.get(name,None)
    if method: return method(self)
    raise AttributeError(name)

def _swig_repr(self):
    try: strthis = "proxy of " + self.this.__repr__()
    except: strthis = ""
    return "<%s.%s; %s >" % (self.__class__.__module__, self.__class__.__name__, strthis,)

try:
    _object = object
    _newclass = 1
except AttributeError:
    class _object : pass
    _newclass = 0


class param_t(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, param_t, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, param_t, name)
    __repr__ = _swig_repr
    __swig_setmethods__["channel_ct"] = _pulse_data.param_t_channel_ct_set
    __swig_getmethods__["channel_ct"] = _pulse_data.param_t_channel_ct_get
    if _newclass:channel_ct = _swig_property(_pulse_data.param_t_channel_ct_get, _pulse_data.param_t_channel_ct_set)
    __swig_setmethods__["sample_ct"] = _pulse_data.param_t_sample_ct_set
    __swig_getmethods__["sample_ct"] = _pulse_data.param_t_sample_ct_get
    if _newclass:sample_ct = _swig_property(_pulse_data.param_t_sample_ct_get, _pulse_data.param_t_sample_ct_set)
    __swig_setmethods__["pulse_sample_ct"] = _pulse_data.param_t_pulse_sample_ct_set
    __swig_getmethods__["pulse_sample_ct"] = _pulse_data.param_t_pulse_sample_ct_get
    if _newclass:pulse_sample_ct = _swig_property(_pulse_data.param_t_pulse_sample_ct_get, _pulse_data.param_t_pulse_sample_ct_set)
    __swig_setmethods__["pulse_index"] = _pulse_data.param_t_pulse_index_set
    __swig_getmethods__["pulse_index"] = _pulse_data.param_t_pulse_index_get
    if _newclass:pulse_index = _swig_property(_pulse_data.param_t_pulse_index_get, _pulse_data.param_t_pulse_index_set)
    __swig_setmethods__["sample_rate"] = _pulse_data.param_t_sample_rate_set
    __swig_getmethods__["sample_rate"] = _pulse_data.param_t_sample_rate_get
    if _newclass:sample_rate = _swig_property(_pulse_data.param_t_sample_rate_get, _pulse_data.param_t_sample_rate_set)
    __swig_setmethods__["ctr_freq"] = _pulse_data.param_t_ctr_freq_set
    __swig_getmethods__["ctr_freq"] = _pulse_data.param_t_ctr_freq_get
    if _newclass:ctr_freq = _swig_property(_pulse_data.param_t_ctr_freq_get, _pulse_data.param_t_ctr_freq_set)
    __swig_setmethods__["t_sec"] = _pulse_data.param_t_t_sec_set
    __swig_getmethods__["t_sec"] = _pulse_data.param_t_t_sec_get
    if _newclass:t_sec = _swig_property(_pulse_data.param_t_t_sec_get, _pulse_data.param_t_t_sec_set)
    __swig_setmethods__["t_usec"] = _pulse_data.param_t_t_usec_set
    __swig_getmethods__["t_usec"] = _pulse_data.param_t_t_usec_get
    if _newclass:t_usec = _swig_property(_pulse_data.param_t_t_usec_get, _pulse_data.param_t_t_usec_set)
    def __str__(self): return _pulse_data.param_t___str__(self)
    def __init__(self): 
        this = _pulse_data.new_param_t()
        try: self.this.append(this)
        except: self.this = this
    __swig_destroy__ = _pulse_data.delete_param_t
    __del__ = lambda self : None;
param_t_swigregister = _pulse_data.param_t_swigregister
param_t_swigregister(param_t)

class pulse_data(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, pulse_data, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, pulse_data, name)
    __repr__ = _swig_repr
    __swig_setmethods__["params"] = _pulse_data.pulse_data_params_set
    __swig_getmethods__["params"] = _pulse_data.pulse_data_params_get
    if _newclass:params = _swig_property(_pulse_data.pulse_data_params_get, _pulse_data.pulse_data_params_set)
    __swig_setmethods__["filename"] = _pulse_data.pulse_data_filename_set
    __swig_getmethods__["filename"] = _pulse_data.pulse_data_filename_get
    if _newclass:filename = _swig_property(_pulse_data.pulse_data_filename_get, _pulse_data.pulse_data_filename_set)
    def __init__(self, *args): 
        this = _pulse_data.new_pulse_data(*args)
        try: self.this.append(this)
        except: self.this = this
    __swig_destroy__ = _pulse_data.delete_pulse_data
    __del__ = lambda self : None;
    def read(self, *args): return _pulse_data.pulse_data_read(self, *args)
    def write(self, *args): return _pulse_data.pulse_data_write(self, *args)
    def param(self): return _pulse_data.pulse_data_param(self)
    def imag(self, *args): return _pulse_data.pulse_data_imag(self, *args)
    def real(self, *args): return _pulse_data.pulse_data_real(self, *args)
    def set_imag(self, *args): return _pulse_data.pulse_data_set_imag(self, *args)
    def set_real(self, *args): return _pulse_data.pulse_data_set_real(self, *args)
    def sample(self, *args): return _pulse_data.pulse_data_sample(self, *args)
pulse_data_swigregister = _pulse_data.pulse_data_swigregister
pulse_data_swigregister(pulse_data)

# This file is compatible with both classic and new-style classes.


