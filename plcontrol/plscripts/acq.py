#coding: utf8
from plscripts.base import Base
import time
import numpy as np
from astropy.io import fits
from swmain import redis

class Acquisition(Base):
    def __init__(self, *args, **kwargs):
        super(Acquisition, self).__init__(*args, **kwargs)

    def save_modulation_extension(self, xmod, ymod, mod_id):
        """
        saves the modulation pattern (xmod, ymod given in mas, and mod_id is the id number) to the a fits etension that will be added automatically
        to all saved fits files from now-on
        """
        imod = np.array(range(len(xmod)))
        col_ind = fits.Column(name='index', format='I', array=imod)
        col_x = fits.Column(name='xmod', format='E', unit="mas", array=xmod)
        col_y = fits.Column(name='ymod', format='E', unit="mas", array=ymod)
        hdu = fits.TableHDU.from_columns([col_ind, col_x, col_y], name = "Modulation")
        hdu.writeto(self._config["modulation_fits_path"], overwrite = True)
        return None

    def get_images(self, nimages = None, ncubes = 0, tint = 0.1, mod_sequence = 1, mod_scale = 1, delay = 10, objX = 0, objY = 0):
        """
        starts the acquisition of a series of cubes, with given dit time and following a given modulation pattern
        param nimages: number of images to take in each cube. If None, this will be set to equal 1 modulation cycle
        param ncubes: number of cubes to acquire 
        param tint: integration time
        param mod_sequence: the modulation sequence to use (1 to 5).
        param mod_scale: the modulation scale (multiplicative factor)
        param delay: the delay between a modulation shift and the start of exposure (in ms)
        param objX: <TODO>
        param objY: <TODO>
        """
        print("changing DIT to low value (to stop long exposure)")
        self._cam.set_tint(0.1)
        # stop the electronics trigger
        print("Stop tip/tilt")
        self._ld.stop_output_trigger()
        self._db.validate_last_tc()
        # select the proper modulation if different from current modulation
        self._ld.get_modulation_sequence_id()
        self._db.validate_last_tc()
        sequence_id = self._db.tcs[-1].reply[0]["data"]["tc_reply_data"]["sequence"]
        if sequence_id != mod_sequence:
            print("Switching to modulation id={}".format(mod_sequence))
            self._ld.switch_modulation_loop(False)
            self._db.validate_last_tc()
            self._ld.load_sequence_from_flash(mod_sequence)
            self._db.validate_last_tc()
        self._ld.set_modulation_scale(mod_scale)
        self._db.validate_last_tc()
        # check if we need to remake the modulation file
        print("Remaking modulation.fits")
        (xmod, ymod) = self._scripts.retrieve_modulation_sequence(mod_sequence)
        self.save_modulation_extension(mod_scale*xmod, mod_scale*ymod, mod_sequence)
        # now we can set up the camera 
        print("Setting up camera")
        if (tint < self._config["cammode_threshold"]):
            mode = "FAST"
        else:
            mode = "SLOW"
        if self._cam.get_readout_mode() != mode:
            print("Switching readout mode")
            self._cam.set_readout_mode(mode)
        self._cam.set_tint(tint) # intergation time in s
        self._cam.set_output_trigger_options("anyexposure", "low", self._config["cam_to_ld_trigger_port"])
        self._cam.set_external_trigger(1)
        # we need to wait until the ongoing DIT is done
        print("Waiting until DIT is finished")
        time.sleep(self._cam.get_tint()+0.1)
        # change offset
        print("Offsetting modulation to X={}, Y={}".format(objX, objY))
        self._ld.set_modulation_offset([1], [objX], [objY])
        self._db.validate_last_tc()
        # make sure modulation is active and reset
        print("Activate modulation")
        self._ld.switch_modulation_loop(True)
        self._db.validate_last_tc()        
        self._ld.reset_modulation_loop()
        self._db.validate_last_tc()        
        # get ready to save files
        print("Getting ready to save files")
        self.prepare_fitslogger(nimages = nimages, ncubes = ncubes)
        # set header kwargs
        redis.update_keys(**{"X_FIROBX": objX, "X_FIROBY": objY, "X_FIRMID": mod_sequence, "X_FIRDMD": mode, "X_FIRTYP":"RAW", "X_FIRMSC":mod_scale})        
        self._cam.set_keyword("X_FIRMID", mod_sequence)
        self._cam.set_keyword("X_FIROBX", objX)
        self._cam.set_keyword("X_FIROBY", objY)
        self._cam.set_keyword("X_FIRDMD", mode)    
        self._cam.set_keyword("X_FIRMSC", mod_scale)   
        self._cam.set_keyword("X_FIRTYP", "RAW")                                             
        time.sleep(0.5)
        # reset the modulation loop and start
        print("Starting integration")
        self._ld.start_output_trigger(delay = delay)
        self._db.validate_last_tc()
        return None
    
    def verify_fits_is_as_expected(file, nimages = None, ncubes = 0, tint = 0.1, mod_sequence = 1, mod_scale = 1, delay = 10, objX = 0, objY = 0):
        error_mess = "Uh oh ! The code ran but the file was saved with the WRONG parameters, you should restart the fitslogger !"
        with fits.open(file) as hdul:
            if nimages != hdul.shape[0]:
                raise ValueError(error_mess)
        return True
    
