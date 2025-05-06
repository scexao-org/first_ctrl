#coding: utf8
from plscripts import links
from plscripts.example import Example
from plscripts.acq import Acquisition

example = None
acq = None

def _linkit(*args, **kwargs):
    global acq
    global example
    links.init(*args, **kwargs)
    example = Example()    
    acq = Acquisition()


