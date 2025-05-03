#coding: utf8
# import standard stuff 
import time
import numpy as np
import os
from astropy.io import fits
import glob

# defines some shell commands to interact with other processes
SAVE_CUBES_COMMAND = "milk-streamFITSlog -z {nimages} -c {ncubes} heecam on"

class PlController(object):
    def __init__(self, ld = None, cam = None, scripts = None, db = None, config = None):
        self.config = config
        self._ld = ld
        self._cam = cam
        self._scripts = scripts
        self._db = db
        return None

    def save_modulation_extension(self, xmod, ymod):
        """
        saves the modulation pattern (xmod, ymod given in mas) to the a fits etension that will be added automatically
        to all saved fits files from now-on
        """
        imod = np.array(range(len(xmod)))
        col_ind = fits.Column(name='index', format='I', array=imod)
        col_x = fits.Column(name='ymod', format='E', unit="mas", array=xmod)
        col_y = fits.Column(name='xmod', format='E', unit="mas", array=ymod)
        hdu = fits.TableHDU.from_columns([col_ind, col_x, col_y], name = "Modulation")
        hdu.writeto(self.config["modulation_fits_path"], overwrite = True)
        return None

    def wait_for_fits(self):
        time.sleep(10)
        return None
    
    def merge_modulation(self, fits_filename):
        """
        Merge the modulation.fits table in the given fits file, as a new extension
        """
        hdu = fits.open(fits_filename)
        hdu_mod = fits.open(self.config["modulation_fits_path"])
        hdu.append(hdu_mod[1])
        hdu.writeto(fits_filename, overwrite = True)
        return None

    def get_images(self, nimages = None, ncubes = 0, tint = 0.1, mod_sequence = 1, delay = 10):
        """
        starts the acquisition of a series of cubes, with given dit time and following a given modulation pattern
        param nimages: number of images to take in each cube. If None, this will be set to equal 1 modulation cycle
        param ncubes: number of cubes to acquire 
        param tint: integration time
        param mod_sequence: the modulation sequence to use (1 to 5).
        param delay: the delay between a modulation shift and the start of exposure (in ms)
        """
        # stop the electronics trigger
        print("Stop tip/tilt")
        self._ld.stop_output_trigger()
        self._db.validate_last_tc()
        # select the proper modulation if different from current modulation
        self._ld.get_modulation_sequence_id() # to be implemented
        self._db.validate_last_tc()
        sequence_id = self._db.tcs[-1].reply[0]["data"]["tc_reply_data"]["sequence"]
        if sequence_id != mod_sequence:
            print("Switching to modulation id={}".format(mod_sequence))
            self._ld.switch_modulation_loop(False)
            self._db.validate_last_tc()
            self._ld.load_sequence_from_flash(mod_sequence)
            self._db.validate_last_tc()
            self._ld.switch_modulation_loop(True)
            self._db.validate_last_tc()
            print("Remaking modulation.fits")
            (xmod, ymod) = self._scripts.retrieve_modulation_sequence(mod_sequence)
            self.save_modulation_extension(xmod, ymod)
        # we need to wait until the ongoing DIT is done
        print("Waiting until DIT is finished")
        time.sleep(self._cam.get_tint())
        # now we can set up the camera 
        print("setting up camera")
        self._cam.set_tint(tint) # intergation time in s
        self._cam.set_output_trigger_options("anyexposure", "low", self.config["cam_to_ld_trigger_port"])
        self._cam.set_external_trigger(1)
        # get ready to save files
        print("Getting ready to save files")
        os.system(SAVE_CUBES_COMMAND.format(nimages = nimages, ncubes = ncubes))
        time.sleep(1)
        # reset the modulation loop and start
        print("gogogo")
        self._ld.reset_modulation_loop()
        self._db.validate_last_tc()        
        self._ld.start_output_trigger()#//(delay = delay) # TODO - need to flash new code
        self._db.validate_last_tc()        
        return None
