#coding: utf8
import glob
from astropy.io import fits
import ruamel.yaml as yaml
from lantern.utils import StoppableThread
import os.path
import time
from pyMilk.interfacing.fps import FPS
import numpy as np
from pyMilk.interfacing.isio_shmlib import SHM as shm

class Merger(StoppableThread):
    def __init__(self, config = None, target_dir = None, *args, **kwargs):
        super(Merger, self).__init__(*args, **kwargs)
        self.shm_var = None
        if config is None:
            raise Exception("Please provide a valid configuration dictionnary")
        if target_dir is None:
            raise Exception("Please provide a target directory")        
        self.config = config
        self.target_dir = target_dir
        filenames = glob.glob(self.target_dir+"/*.fits")
        self.processed_files = filenames  
        self.nfiles = 0    
        self.logger = FPS('streamFITSlog-firstpl')     
        self.check_ndits = True
        return None

    def process_file(self, filename, check_ndits = False):
        """
        Processing a new file
        """
        status = self.shm_var.get_keywords()
        new_status = {"f_last": filename.split("firstpl_")[1].split(".fits")[0].replace(":", ""),
                      "busy": True,
                      "last_done": False,
                      "f_prev": status["f_last"],
                      "prev_done": status["last_done"],
                      "nfiles": status["nfiles"]+1,
                      "nfiles_done": status["nfiles_done"]
                    }        
        self.shm_var.set_keywords(new_status)
        if os.path.isfile(self.config["modulation_fits_path"]):
            try:
                hdu_mod = fits.open(self.config["modulation_fits_path"])
                try:
                    hdu = fits.open(filename)
                    if check_ndits:
                        ndits_expected = self.logger.get_param("cubesize")
                        ndits = np.shape(hdu[0].data)[0]
                        if ndits != ndits_expected:
                            print("WARNING: file {} has {} dits, but {} seem expected from logger".format(filename, ndits, ndits_expected))
                    hdu.append(hdu_mod[1])
                    try:
                        hdu.writeto(filename, overwrite = True)
                        new_status["last_done"] = True
                    except:
                        print("Unable to write {}".format(filename))
                    self.processed_files.append(filename)
                except:
                    print("Unable to open {}".format(filename))
            except:
                print("Warning: unable to open modulation file when processing {}".format(filename))
        else:
            print("No modulation file to merge with {}".format(filename))
        new_status["nfiles_done"] = new_status["nfiles_done"]+1
        new_status["busy"] = False
        self.shm_var.set_keywords(new_status)
        return None
    
    def change_target_dir(self, target_dir = None):
        """
        Change the current target directory
        """
        if target_dir is None:
            logger = FPS('streamFITSlog-firstpl')  
            target_dir = logger.get_param("dirname")
        print("Setting target_dir to {}".format(target_dir))
        self.target_dir = target_dir
        return None        
        
    def run(self):
        while not(self.stopped()):
            time.sleep(0.1) # breathing room
            filenames = glob.glob(self.target_dir+"/*.fits")
            if len(filenames) != self.nfiles:
                print("Merger detected {} fits files".format(len(filenames)))
                self.nfiles = len(filenames)
            for filename in filenames:
                if not(filename in self.processed_files):
                    print("Processing {}".format(filename))
                    self.process_file(filename, check_ndits = self.check_ndits)
        print("Merger stopped")
        return None

def stop():
    merger.stop()   
    return None 

if __name__ == "__main__":
    pl_config = os.environ['HOME']+"/src/firstctrl/first_ctrl/plcontrol/config_plcontrol.yml"
    loader = yaml.YAML()
    config = loader.load(open(pl_config).read())

    # setup the shm for the fitsmerger
    shm_var = shm('firstpl_merger_status', None, location=-1, shared=1)
    init_dict = {"f_last": "",
                "busy": False,
                "last_done": False,
                "f_prev": "",
                "prev_done": False,
                "nfiles": 0,
                "nfiles_done": 0
                }
    shm_var.set_keywords(init_dict)
    
    # Create and start the threads
    logger = FPS('streamFITSlog-firstpl')  
    target_dir = logger.get_param("dirname")
    merger = Merger(config = config, target_dir=target_dir)
    merger.shm_var = shm_var
    print("starting merger targetting {}".format(merger.target_dir))
    merger.start()


  