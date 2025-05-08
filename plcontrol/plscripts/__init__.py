#coding: utf8
from plscripts import links
from plscripts.inspect import Inspect
from plscripts.acq import Acquisition
from plscripts.startup import Startup
from plscripts.modulation import Modulation

# no need to link those
mod = Modulation

# need to link those
ins = None # data visualization
acq = None # data acquisition
bon = None # begnning of night
end = None # end of night

def _linkit(*args, **kwargs):
    global acq
    global ins
    global bon
    links.init(*args, **kwargs)
    ins = Inspect()    
    acq = Acquisition()
    bon = Startup()

