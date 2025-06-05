#coding: utf8
from plscripts import links
from plscripts.inspect import Inspect
from plscripts.acq import Acquisition
from plscripts.startup import Startup
from plscripts.modulation import Modulation
from plscripts.stopup import Eon
from plscripts.geometry import Geometry

# no need to link those
mod = Modulation
geo = Geometry

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
    ins._linkit()    
    acq._linkit()
    bon._linkit()
    eon._linkit()
    # some links between components are required for smooth operations
    bon._acq = acq
    eon._acq = acq
    acq._ins = ins

