#coding: utf8
from plscripts.base import Base
import datetime
import os

class Startup(Base):
    def __init__(self, *args, **kwargs):
        super(Startup, self).__init__(*args, **kwargs)

    def startup_fitslogger(self, dirname = None, timeout = None):
        """
        Stuff that needs to happen to the fits logger at startup, i.e. setting dirname and timeout.
        By default, dirname will be set to today's dir in the root dir, and timeout to config value 
        """
        if dirname is None:
            tnow = datetime.datetime.now(datetime.timezone.utc)
            dirname = self._config["datadir"].format(today = tnow.strftime("%Y%m%d"))
        if timeout is None:
            timeout = self._config["fitslogger_timeout"]
        print("Setting fitslogger dirname to {}".format(dirname))
        if not os.path.exists(dirname):
            os.makedirs(dirname)        
        self.set_fitslogger_logdir(dirname)
        print("Setting fitslogger timeout to {}".format(timeout))
        self.set_fitslogger_timeout(timeout)
        return None