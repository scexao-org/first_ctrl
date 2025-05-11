#coding: utf8
from plscripts import links
from plscripts.inspect import Inspect
from plscripts.acq import Acquisition
from plscripts.startup import Startup
from plscripts.modulation import Modulation
from plscripts.stopup import Eon

# no need to link those
mod = Modulation

# need to link those
ins = None # data visualization
acq = None # data acquisition
bon = None # begnning of night
eon = None # end of night

def _linkit(*args, **kwargs):
    global acq
    global ins
    global bon
    global eon
    links.init(*args, **kwargs)
    ins = Inspect()    
    acq = Acquisition()
    bon = Startup()
    eon = Eon()
    # some links between components are required for smooth operations
    bon._acq = acq
    acq._ins = ins

