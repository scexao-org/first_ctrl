#coding: utf8
import plscripts.links
import os

# defines some shell commands to interact with other processes
SAVE_CUBES_COMMAND = "milk-streamFITSlog -z {nimages} -c {ncubes} {camname} on"

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