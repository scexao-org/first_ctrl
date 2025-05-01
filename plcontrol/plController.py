#coding: utf8
# import standard stuff 
import time
import numpy as np
import ruamel.yaml as yaml
import os
from astropy.io import fits

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

    def get_images(self, nimages = None, ncubes = 0, tint = 0.1, mod_sequence = 1):
        """
        starts the acquisition of a series of cubes, with given dit time and following a given modulation pattern
        param nimages: number of images to take in each cube. If None, this will be set to equal 1 modulation cycle
        param ncubes: number of cubes to acquire 
        param tint: integration time
        param mod_sequence: the modulation sequence to use (1 to 5).
        """
        # stop the electronics trigger
        self._ld.stop_output_trigger()
        self._db.validate_last_tc()
        # select the proper modulation if different from current modulation
        #self._ld.get_modulation_sequence_id() # to be implemented
        # TODO
        self._ld.switch_modulation_loop(False)
        self._db.validate_last_tc()
        self._ld.load_sequence_from_flash(mod_sequence)
        self._db.validate_last_tc()
        self._ld.switch_modulation_loop(True)
        self._db.validate_last_tc()
        (xmod, ymod) = self._scripts.retrieve_modulation_sequence(mod_sequence)
        self.save_modulation_extension(xmod, ymod)
        # if no nimages given, automatically set it to the number of modulation points
        if nimages is None:
            nimages = len(xmod)
        # we need to wait until the ongoing DIT is done
        print("Waiting until DIT is finished")
        time.sleep(self._cam.get_tint())
        # now we can set up the camera 
        self._cam.set_tint(tint) # intergation time in s
        self._cam.set_output_trigger_options("anyexposure", "low", self.config["cam_to_ld_trigger_port"])
        self._cam.set_external_trigger(1)
        # get ready to save files
        os.system(SAVE_CUBES_COMMAND.format(nimages = nimages, ncubes = ncubes))
        # reset the modulation loop and start
        self._ld.reset_modulation_loop()
        self._ld.start_output_trigger()
        return None
