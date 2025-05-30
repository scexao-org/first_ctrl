#coding: utf8
import glob
from astropy.io import fits
import ruamel.yaml as yaml
from lantern.utils import StoppableThread
import os.path
import time
from pyMilk.interfacing.fps import FPS
import numpy as np

class Merger(StoppableThread):
    def __init__(self, config = None, target_dir = None, *args, **kwargs):
        super(Merger, self).__init__(*args, **kwargs)
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
                    except:
                        print("Unable to write {}".format(filename))
                    self.processed_files.append(filename)
                except:
                    print("Unable to open {}".format(filename))
            except:
                print("Warning: unable to open modulation file when processing {}".format(filename))
        else:
            print("No modulation file to merge with {}".format(filename))
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
    # create the parser for command lines arguments
    #parser = argparse.ArgumentParser(description="rautomatically merge modulation aux table in newly created fits files")
    #parser.add_argument('target_dir', type=str, help="the path to the directory where fits files are saved")

    #args = parser.parse_args()
    #dargs = vars(args) # to treat as a dictionnary

    pl_config = os.environ['HOME']+"/src/firstctrl/first_ctrl/plcontrol/config_plcontrol.yml"
    loader = yaml.YAML()
    config = loader.load(open(pl_config).read())

    # Create and start the threads
    logger = FPS('streamFITSlog-firstpl')  
    target_dir = logger.get_param("dirname")
    merger = Merger(config = config, target_dir=target_dir)
    print("starting merger targetting {}".format(merger.target_dir))
    merger.start()


  