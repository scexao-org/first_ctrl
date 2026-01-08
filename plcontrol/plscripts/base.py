#coding: utf8
import plscripts.links
import os
import time
from pyMilk.interfacing.fps import FPS
from swmain import redis
import glob
from astropy.io import fits
from pyMilk.interfacing.isio_shmlib import SHM as shm

# defines some shell commands to interact with other processes
SET_TIMEOUT_COMMAND = "setval streamFITSlog-firstpl.procinfo.triggertimeout {timeout}"

# helper to remake proper filename from truncated/compressed stuff in the shm
def _remake_filename(truncated):
    filename = "firstpl_"+truncated[0:2]+":"+truncated[2:4]+":"+truncated[4:]+".fits"
    return filename
class Base(object):
    def __init__(self):
        self._cam = None
        self._ld = None
        self._scripts = None
        self._db = None
        self._config = None
        self._zab = None
        self.logger = FPS('streamFITSlog-firstpl')
        self._shm_var = shm("firstpl_merger_status")

    def _linkit(self):
        self._cam = plscripts.links.cam
        self._ld = plscripts.links.ld
        self._scripts = plscripts.links.scripts
        self._db = plscripts.links.db
        self._config = plscripts.links.config
        self._zab = plscripts.links.zab

    def _set_with_check(self, key, value, timeout = 5):
        """
        attempt to set given key with given value in fits logger multiple times until
        the logger returns the correct state
        """
        self.logger.set_param(key, value)
        t0 = time.time()
        while (self.logger.get_param(key) != value):
            time.sleep(0.1)
            if time.time() - t0 > timeout:
                raise Exception("timeout when setting {} to {} in logger".format(key, value))
            self.logger.set_param(key, value)
            time.sleep(0.1)
        return None
    
    @staticmethod
    def get_keyword(keyword):
        """
        retrieve a telescope keyword from the redis server
        """
        return redis.get_values([keyword])[keyword]
    
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

        # remove any existing shm logbuffers
        if os.path.isfile('/milk/shm/firstpl_logbuff0.im.shm') is True:
            os.system('rm /milk/shm/firstpl_logbuff0.im.shm')
        if os.path.isfile('/milk/shm/firstpl_logbuff1.im.shm') is True:
            os.system('rm /milk/shm/firstpl_logbuff1.im.shm')

        self.switch_fitslogger(True)
        time.sleep(3)   # to give it enough time to build the 2 logbuffers
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
            time.sleep(0.1)
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
    
    def wait_for_file_ready(self, validate_file = True, timeout = 10):
        """
        pool the content of a directory (by default from the logger) until a new file appears.
        Can also wait until the new file as a valid content
        """
        status = self._shm_var.get_keywords()  
        nfiles_processed_before = status["nfiles_done"]
        nfiles_processed = nfiles_processed_before
        t0 = time.time()
        while not(nfiles_processed > nfiles_processed_before):
            time.sleep(0.1)
            status = self._shm_var.get_keywords()  
            nfiles_processed = status["nfiles_done"]            
            if (time.time() - t0) > timeout:
                raise Exception("Timeout!")  
        if validate_file:        
            return status["last_done"]
        else:
            return True

    def _verify_files_are_done(self, folder, expected_number_of_files, expected_time_taken=10):
        """ 
        Verify in a folder is all the expected cubes have been created. Timeout after expected_time_taken in seconds.
        """
        folder = str(folder)
        filenames_start = glob.glob(folder + "/*.fits")
        filenames = glob.glob(folder + "/*.fits")
        t0 = time.time()
        timeout = expected_time_taken * expected_number_of_files
        while len(filenames) < len(filenames_start) + expected_number_of_files:
            time.sleep(0.1)        
            filenames = glob.glob(folder + "/*.fits")
            if (time.time() - t0) > timeout:
                continue   
        nb_files_done = len(filenames) - len(filenames_start)               
        if nb_files_done == expected_number_of_files:
            return True
        else : 
            print(f"Timeout, {nb_files_done} created instead of {expected_number_of_files}")
            return False
    
