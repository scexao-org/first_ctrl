#coding: utf8
from plscripts.base import Base
import time
from astropy.io import fits
import numpy as np

AUTHORIZED_DATATYP = ["ACQUISITION", "BIAS", "COMPARISON", "DARK", "DOMEFLAT", "FLAT", "FOCUSING", "OBJECT", "SKYFLAT", "STANDARD", "TEST"]


class Acquisition(Base):
    def __init__(self, *args, **kwargs):
        super(Acquisition, self).__init__(*args, **kwargs)
        self.mode = None
        self._ins = None

    def set_mode_rolling(self, x, y, open_loop = True):
        """
        Switch FIRST-PL to rolling acquisition mode, in which the camera is internally
        triggered and the TT does not modulate
        @param x, y: give the position of the tip/tilt
        @param open_loop: whether to open the contol loop once the piezo is settled or not
        """
        print("changing DIT to low value (to stop long exposure)")
        self._cam.set_tint(0.1)
        # stop the electronics trigger
        print("Stop trigger")
        self._ld.stop_output_trigger()
        self._db.validate_last_tc()
        # switch off modulation and send piezo to position
        print("Switching off modulation")
        self._ld.switch_modulation_loop(False)
        self._db.validate_last_tc()        
        print("Moving piezo to x = {}, y = {}".format(x, y))
        self._ld.move_piezo(x, y)
        self._db.validate_last_tc()             
        time.sleep(1)
        if open_loop:
            print("Opening the control loop")
            self._ld.switch_control_loop(False)
            self._db.validate_last_tc()            
        # camera mode
        print("resetting the camera to internal trigger")
        self._cam.set_external_trigger(0)
        # deal with keywords
        keywords = {"X_FIROBX": x, 
                    "X_FIROBY": y,
                    "X_FIRMID": -1, 
                    "X_FIRMSC": -1}
        self.update_keywords(keywords)
        self.mode = "ROLLING"
        keywords = {"X_FIRTRG": "INT"}
        self.update_keywords(keywords=keywords)
        return None

    def set_mode_triggered(self):
        """
        Switch FIRST-PL to triggered acquisition mode, in which the camera is externally
        triggered and the TT modulates the position
        """
        # stop the electronics trigger
        print("Closing the control loop")
        self._ld.switch_control_loop(True)
        self._db.validate_last_tc()
        self._ld.switch_closed_loop(True)
        self._db.validate_last_tc()
        # camera mode
        print("setting the camera to external trigger")
        self._cam.set_output_trigger_options("anyexposure", "low", self._config["cam_to_ld_trigger_port"])
        self._cam.set_external_trigger(1)        
        self.mode = "TRIGGERED"
        keywords = {"X_FIRTRG": "EXT"}
        self.update_keywords(keywords=keywords)
        return None

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
    
    def get_images(self, nimages = None, ncubes = 0, tint = 0.1, mod_sequence = 1, mod_scale = 1, limit_triggers = False, delay = 10, objX = 0, objY = 0, data_typ = "OBJECT"):
        """
        starts the acquisition of a series of cubes, with given dit time and following a given modulation pattern
        param nimages: number of images to take in each cube. If None, this will be set to equal 1 modulation cycle
        param ncubes: number of cubes to acquire 
        param tint: integration time
        param mod_sequence: the modulation sequence to use (1 to 5).
        param mod_scale: the modulation scale (multiplicative factor)
        param limit_triggers: true or false to limit the number of triggers from the electronics to the number of frames
        param delay: the delay between a modulation shift and the start of exposure (in ms)
        param objX: offset of the modulation pattern along RA axis (in mas)
        param objY:  offset of the modulation pattern along DEC axis (in mas)
        param data_typ: the data type for the fits header
        """
        if self.mode != "TRIGGERED":
            raise Exception("Camera not in 'TRIGGERED' mode. This function is unavailable.")
        data_typ = data_typ.upper()
        if not(data_typ in AUTHORIZED_DATATYP):
            raise Exception("DATA-TYP {} is not authorized.".format(data_typ)) 
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
        # check the modulation length and number of cubes
        if ((ncubes > 1) and ((nimages % len(xmod)) != 0)):
            raise Exception("The number of frames ({}) is not a multiple of the number of modulation positions ({}). This is not allowed with nimages = 1.".format(nimages, len(xmod)))
        # now we can set up the camera 
        print("Setting up camera")
        if (tint < self._config["cammode_threshold"]):
            mode = "FAST"
        else:
            mode = "SLOW"
        if self._cam.get_readout_mode() != mode:
            print("Switching readout mode")
            self.mode = None
            self._cam.set_readout_mode(mode)
            print("Going back to triggered mode")
            self.set_mode_triggered()
        self._cam.set_tint(tint) # intergation time in s
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
        # set header kwargs
        keywords = {"X_FIROBX": objX, 
                    "X_FIROBY": objY,
                    "X_FIRMID": mod_sequence, 
                    "X_FIRDMD": mode, 
                    "X_FIRMSC":mod_scale,
                    "X_FIRTYP": "RAW", 
                    "DATA-TYP": data_typ}
        self.update_keywords(keywords)
        time.sleep(0.1) # just in case
        # get ready to save files
        print("Getting ready to save files")
        self.prepare_fitslogger(nimages = nimages, ncubes = ncubes)  
        time.sleep(2) # just in case      
        # reset the modulation loop and start
        print("Starting integration")
        if limit_triggers:
            ntrigs = ncubes*nimages
        else:  
            ntrigs = 0
        self._ld.start_output_trigger(ntrigs = ntrigs, delay = delay)
        self._db.validate_last_tc()
        return None