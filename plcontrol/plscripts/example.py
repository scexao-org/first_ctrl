#coding: utf8
from plscripts.base import Base

class Example(Base):
    def __init__(self, *args, **kwargs):
        super(Example, self).__init__(*args, **kwargs)
    
    def hello(self):
        self._ld.get_version()
        return None
    