#coding: utf8
import plscripts.links
import os

# defines some shell commands to interact with other processes
SAVE_CUBES_COMMAND = "milk-streamFITSlog -z {nimages} -c {ncubes} {camname} on"
SET_DIRNAME_COMMAND = "setval streamFITSlog-firstpl.dirname {dirname}"
GET_DIRNAME_COMMAND = "getval streamFITSlog-firstpl"
SET_TIMEOUT_COMMAND = "setval streamFITSlog-firstpl.procinfo.triggertimeout {timeout}"


class Base(object):
    def __init__(self):
        self._cam = plscripts.links.cam
        self._ld = plscripts.links.ld
        self._scripts = plscripts.links.scripts
        self._db = plscripts.links.db
        self._config = plscripts.links.config

    def prepare_fitslogger(self, nimages = None, ncubes = None):
        """
        send shell command to the fits logger to prepare for saving ncubes with nimages in each
        """
        if (nimages is None) or (ncubes is None):
            return None 
        os.system(SAVE_CUBES_COMMAND.format(nimages = nimages, ncubes = ncubes, camname = self._config["camname"]))
        return None
    
    def _send_command_fitslogger(self, command):
        """
        send the given string command to the fifo of the fits logger
        """
        os.system('echo "{}" > {}'.format(command, self._config["fitslogger_fifo"]))
        return None
    
    def _getval_from_fifo(self, command):
        """
        get the returned value from a given command from the FIFO by parsing it
        """
        self.content = os.system('cat {} | grep GETVAL | grep {}'.format(self._config["fitslogger_outputlog"], command))
        return self.content
    
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
        self._send_command_fitslogger(SET_DIRNAME_COMMAND.format(dirname = dirname))
        return None                                      

    def get_fitslogger_logdir(self):
        """
        interacts with the fits logger to get the path where data are currently saved
        """
        self._send_command_fitslogger(GET_DIRNAME_COMMAND)
        return self._getval_from_fifo(GET_DIRNAME_COMMAND)