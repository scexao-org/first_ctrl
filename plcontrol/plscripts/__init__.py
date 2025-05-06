#coding: utf8
from plscripts import links
from plscripts.inspect import Inspect
from plscripts.acq import Acquisition
from plscripts.startup import Startup

ins = None
acq = None
stp = None

def _linkit(*args, **kwargs):
    global acq
    global ins
    global stp
    links.init(*args, **kwargs)
    ins = Inspect()    
    acq = Acquisition()
    stp = Startup()

