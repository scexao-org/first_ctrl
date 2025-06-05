
#coding: utf8
from lantern.utils import StoppableThread
import numpy as np
import glob
import os
import runPL_library_basic as basic
from pyMilk.interfacing.isio_shmlib import SHM as shm
import time
import argparse
import matplotlib.pyplot as plt
plt.ion()
from plscripts.base import Base
import os
from astropy.io import fits
from scipy.interpolate import griddata
from scipy.optimize import curve_fit
import threading
from pyMilk.interfacing.fps import FPS
from plscripts import inspect

class LiveOptiFlux(StoppableThread, inspect.Inspect):
    """
    Real time display of the reconstructed images.
    """
    def __init__(self, vmin = None, vmax = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vmin = vmin
        self.vmax = vmax 
        self.logger = FPS('streamFITSlog-firstpl')
        self.data_path = None
        self.filename = None
        map_void = np.zeros((500, 500), dtype=np.float32)
        self.shm_var = shm('first_opti', map_void, location=-1, shared=1)
        #self.shm_var.set_keywords({"X_FIRMSC": 10})        
    
    def setting_milk(self):
        #data = self.plot_detector()

        try :
            self.opti_flux(perform_fit = False, plot_it=False)
            image = self.flux_map.T[::-1, :]
            keywords = dict(self.flux_keywords)
            short_header_dict = {str(k)[:15]: str(v)[:15] for k, v in keywords.items()}
            filtered_dict = {key: value for key, value in short_header_dict.items() if key.startswith("X_FIR")}
            #print(filtered_dict)
        except:
            print("Failed to load fits")
            return None
        if self.vmin is not None:
            image[1,1]=self.vmin
        if self.vmax is not None:
            image[99,99]=self.vmax

        self.shm_var.set_data(image.astype(np.float32))
        self.shm_var.set_keywords(filtered_dict)
        return None
    
    def run(self):
        while not(self.stopped()):
            self.setting_milk()
            time.sleep(1)  # Adjust the delay as needed #0.1
        print("Exiting...")        
        return None



parser = argparse.ArgumentParser(description="Pick min and max color scale values")
parser.add_argument('--vmin', type=int, required=False, help='Min scale value', default=None)
parser.add_argument('--vmax', type=int, required=False, help='Max scale value', default=None)

if __name__ == "__main__":
    args = parser.parse_args()

    # Create an instance of the class
    opti = LiveOptiFlux(vmin = args.vmin, vmax = args.vmax)

    # Load the calibration files
    opti.opti_flux(perform_fit = False, plot_it=False)

    # Continuously plot images as new data comes in
    opti.start()