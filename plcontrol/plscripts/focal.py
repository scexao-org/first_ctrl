#coding: utf8
from plscripts.base import Base
import time
from astropy.io import fits
import numpy as np
from plscripts.geometry import Geometry
from astropy.coordinates import SkyCoord
from astropy import units
import subprocess



TRIGGERED = "TRIGGERED"
ROLLING = "ROLLING"

class Focalcamera(Base):
    def __init__(self, *args, **kwargs):
        super(Focalcamera, self).__init__(*args, **kwargs)
        self.mode = None
        self._ins = None
        self._acq = None
        self.camera_started = True
        # self.stop()

    def start(self, silent=False):

        if self.camera_started == True:
            if not silent:
                print("Focal camera is already started")
        else:
            print("Moving in focal camera")
            self._fcam.start_frame_taker_and_dependents()
            # insert  mirror on conex on the beam
            subprocess.run(["firstpl_fp", "in"], check=True)
            time.sleep(1)
            self.camera_started = True
            if not silent:
                print("Focal camera started")

    def stop(self,silent=False):


        if self.camera_started == True:    
            print("Moving out focal camera")
            self._fcam.kill_taker_and_dependents()
            # remove mirror on conex on the beam
            subprocess.run(["firstpl_fp", "out"], check=True)
            self.camera_started = False

            if not silent:
                print("Focal camera stopped")
        else:
            if not silent:
                print("Focal camera is already stopped")

    def get_images(self, nimages = 100, ncubes = 1, tint = 0.008): 
        """
        take a cube using the logger in rolling mode
        param nimages: number of images to take in each cube
        param ncubes: number of cubes to acquire 
        param tint: integration time
        """    
        print("Setting up focal plane camera")
        self.start(silent=True)
        self._fcam.set_tint(tint) # intergation time in s        
        # get ready to save files
        print("Getting ready to save files")
        self.prepare_fitslogger(nimages = nimages, ncubes = ncubes, fpupcam = True)  
        print("Started integration")
        return None
    
    def get_images_triggered(self, nimages = 190, ncubes = 2, tint = 0.1, mod_sequence = 7, mod_scale = 500):
        """
        starts the acquisition of a series of cubes, with given dit time and following a given modulation pattern
        param nimages: number of images to take in each cube. If None, this will be set to equal 1 modulation cycle
        param ncubes: number of cubes to acquire 
        param tint: integration time
        param mod_sequence: the modulation sequence to use (1 to 7).
        param mod_scale: the modulation scale (multiplicative factor)
        param limit_triggers: true or false to limit the number of triggers from the electronics to the number of frames
        param delay: the delay between a modulation shift and the start of exposure (in ms)
        param objX: offset of the modulation pattern along RA axis (in mas)
        param objY:  offset of the modulation pattern along DEC axis (in mas)
        param data_typ: the data type for the fits header
        """

        self.start(silent=True)

        self._acq.get_images(nimages = nimages, ncubes = ncubes, tint = tint, mod_sequence = mod_sequence, mod_scale = mod_scale, limit_triggers = True, data_typ = "TEST")

        duration = nimages * ncubes * (tint + 0.01)

        tint_fcam = 0.00828
        nimages_fcam = 500
        ncubes_fcam = int(duration/(nimages_fcam*tint_fcam))
        if ncubes_fcam < 1:
            ncubes_fcam = 1

        self.get_images(nimages = nimages_fcam, ncubes = ncubes_fcam, tint = tint_fcam)

        return None

    def center_PL(self, tint = 0.05, init_scale = 200, n_iterations = 2):
        """
        perform a series of scans to find the maximum injection and recenter the zabers
        """
        # scales = [init_scale] + [75]*(n_iterations - 1)
        # for k in range(n_iterations):
        #     print("Iteration number {}/{}".format(k+1, n_iterations))
        #     self.get_acquisition_scan(wait_until_done = True, tint = tint, mod_scale = scales[k])
        #     x, y = self._ins.opti_flux(plot_it = False)
        #     print("Found maximum at x={:.2f} mas, y={:.2f} mas".format(x, y))
        #     xzab, yzab = Geometry.tt_to_zab(x, y)
        #     self._zab.delta_move(-xzab, -yzab)
        # # last scan for checking
        # self.get_acquisition_scan(wait_until_done = True, tint = tint, mod_scale = 75)            
        return None
