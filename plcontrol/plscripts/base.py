#coding: utf8
import plscripts.links
import os
import time
from pyMilk.interfacing.fps import FPS
from swmain import redis

# defines some shell commands to interact with other processes
SET_TIMEOUT_COMMAND = "setval streamFITSlog-firstpl.procinfo.triggertimeout {timeout}"

class Base(object):
    def __init__(self):
        self._cam = plscripts.links.cam
        self._ld = plscripts.links.ld
        self._scripts = plscripts.links.scripts
        self._db = plscripts.links.db
        self._config = plscripts.links.config
        self.logger = FPS('streamFITSlog-firstpl')

    def _set_with_check(self, key, value, timeout = 5):
        """
        attempt to set given key with given value in fits logger multiple times until
        the logger returns the correct state
        """
        self.logger.set_param(key, value)
        t0 = time.time()
        while (self.logger.get_param(key) != value):
            if time.time() - t0 > timeout:
                raise Exception("timeout when setting {} to {} in logger".format(key, value))
            self.logger.set_param(key, value)
            time.sleep(0.1)
        return None

    def update_keywords(self, keywords):
        """
        update the keywords given as a dict {"keyword": value}, both in redis and in camera
        """
        redis.update_keys(**keywords)
        for key in keywords.keys():
            self._cam.set_keyword(key, keywords[key])   
        return None     

    def prepare_fitslogger(self, nimages = None, ncubes = None):
        """
        send shell command to the fits logger to prepare for saving ncubes with nimages in each
        """
        if (nimages is None) or (ncubes is None):
            return None 
        self.switch_fitslogger(False)
        self._set_with_check("cubesize", nimages)
        self._set_with_check("maxfilecnt", ncubes)
        self.switch_fitslogger(True)
        self._set_with_check("saveON", True)
        return None
    
    def _send_command_fitslogger(self, command):
        """
        send the given string command to the fifo of the fits logger
        """
        os.system('echo "{}" > {}'.format(command, self._config["fitslogger_fifo"]))
        return None
    
    def set_fitslogger_timeout(self, timeout):
        """
        change the timeout for the loop of the fits logger to avoid exiting without doing anything
        """
        self._send_command_fitslogger(SET_TIMEOUT_COMMAND.format(timeout = timeout))
        return None

    def set_fitslogger_logdir(self, dirname):
        """
        change the dirname where FITS are saved in the fits logger
        """    
        if not os.path.exists(dirname):
            os.makedirs(dirname)         
        self._set_with_check("dirname", dirname)
        return None                                      

    def get_fitslogger_logdir(self):
        """
        interacts with the fits logger to get the path where data are currently saved
        """
        dirname = self.logger.get_param("dirname")
        return dirname
    
    def switch_fitslogger(self, state, timeout = 5):
        """
        Turn on/off the fits logger
        """
        t0 = time.time()
        while (self.logger.run_isrunning() != state):
            if time.time() - t0 > timeout:
                raise Exception("Timeout while switching the fitslogger to {}".format(state))
            if state:
                self.logger.run_start()
            else:
                self.logger.run_stop()
            time.sleep(0.1)
        if not(state):
            self._set_with_check("saveON", False)
        return None
