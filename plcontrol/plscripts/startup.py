#coding: utf8
from plscripts.base import Base
import datetime
import time

class Startup(Base):
    def __init__(self, *args, **kwargs):
        super(Startup, self).__init__(*args, **kwargs)

    def startup_fitslogger(self, dirname = None, timeout = None):
        """
        Stuff that needs to happen to the fits logger at startup, i.e. setting dirname and timeout.
        By default, dirname will be set to today's dir in the root dir, and timeout to config value 
        """
        # send this twice as it is required for some reason
        self.switch_fitslogger(False)
        if dirname is None:
            tnow = datetime.datetime.now(datetime.timezone.utc)
            dirname = self._config["datadir"].format(today = tnow.strftime("%Y%m%d"))
        if timeout is None:
            timeout = self._config["fitslogger_timeout"]
        print("Setting fitslogger dirname to {}".format(dirname))       
        self.set_fitslogger_logdir(dirname)
        print("Setting fitslogger timeout to {}".format(timeout))
        self.set_fitslogger_timeout(timeout)
        self.switch_fitslogger(True)
        self._acq = None # link to acquisition scripts
        return None
    
    def startup_electronics(self, config_id = None):
        """
        Put the electronics in a state ready to start integrating
        @param confg_id: id of the configuration to use (1 to 3)
        """
        if not(self._acq is None):
            self._acq.mode = None # mode is undefined after startup
        if not(config_id is None):
            print("Changing to config {}".format(config_id))
            self._ld.use_config_on_next_boot(config_id = config_id)
        print("Software reboot")
        self._ld.software_reboot()
        time.sleep(1)
        self._ld.get_version()
        self._db.validate_last_tc()
        version_reply = self._db.tcs[-1].reply[0]["data"]["tc_reply_data"]
        print("Setting the clock.")
        self._scripts.set_lstnow(location = "subaru")
        self._scripts.set_utcnow()
        print("Moving piezo to (0, 0)")
        self._ld.move_piezo(0, 0)
        self._db.validate_last_tc()
        print("Closing the loop")
        self._ld.switch_control_loop(True)
        self._db.validate_last_tc()        
        self._ld.switch_closed_loop(True)
        self._db.validate_last_tc()        
        keywords = {"X_FIRVER": "{};{}".format(version_reply["version"], version_reply["config"].decode()),
                    "X_FIRTRG": "UNDEFINED"}
        self.update_keywords(keywords=keywords)
        print("Running verion {version} with config {config}\nReady to go!".format(version = version_reply["version"], config = version_reply["config"].decode()))
        return None