#coding: utf8
from plscripts.base import Base
import time
from astropy.io import fits
import numpy as np
from plscripts.geometry import Geometry
from astropy.coordinates import SkyCoord
from astropy import units

AUTHORIZED_DATATYP = ["ACQUISITION", "BIAS", "COMPARISON", "DARK", "DOMEFLAT", "FLAT", "FOCUSING", "OBJECT", "SKYFLAT", "STANDARD", "TEST"]

TRIGGERED = "TRIGGERED"
ROLLING = "ROLLING"

class Acquisition(Base):
    def __init__(self, *args, **kwargs):
        super(Acquisition, self).__init__(*args, **kwargs)
        self.mode = None
        self._ins = None

    def update_target_coordinates(self):
        """
        Update the coordinates of the target on the tip/tilt electronics based on the one reported by telescope in redis
        """
        ra, dec = self.get_keyword("RA"), self.get_keyword("DEC")
        print("Updating coordinates to RA={}, DEC={}".format(ra, dec))
        tgt = SkyCoord(ra, dec, unit=(units.hourangle, units.deg))
        ra = tgt.ra.hourangle
        dec = tgt.dec.degree
        self._ld.set_target_coords(ra = ra, dec = dec)
        self._db.validate_last_tc()
        return None

    def set_readout_mode(self, readout_mode = None):
        """
        Helper to change the readout mode of the camera.
        param: readout_mode = "SLOW" or "FAST"
        """
        if not(readout_mode.upper() in ["SLOW", "FAST"]):
            raise Exception("Readout mode should be 'SLOW' or 'FAST'.")
        # first we check if we are not already in this mode
        if self._cam.get_readout_mode() == readout_mode:
            return readout_mode
        current_mode = self.mode
        if current_mode is None :
            raise Exception("Trigger mode undefined") 
        # For unclear reasons, camstack waits for a frame when changing the readout mode of the camera,
        # and gets stuck of the fits logger is running
        self.switch_fitslogger(False)      
        # changing the readout mode reset the trigger configuration so we need to be careful with the acq mode    
        self.mode = None
        print("Switching to readout mode {}".format(readout_mode))
        self._cam.set_readout_mode(readout_mode)
        if current_mode == TRIGGERED:
            # go back to proper trigger configuration
            self._cam.set_output_trigger_options("anyexposure", "low", self._config["cam_to_ld_trigger_port"])
            self._cam.set_external_trigger(1)  
            self.mode = TRIGGERED      
        else:
            self._cam.set_external_trigger(0)    
            self.mode = ROLLING                                
        # restart the logger
        self.switch_fitslogger(True)
        return readout_mode
    
    def set_mode_rolling(self, x, y, open_loop = True):
        """
        Switch FIRST-PL to rolling acquisition mode, in which the camera is internally
        triggered and the TT does not modulate
        @param x, y: give the position of the tip/tilt
        @param open_loop: whether to open the contol loop once the piezo is settled or not
        """
        if self.mode == ROLLING:
            print("Already in ROLLING mode")
            return None
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
        self.mode = ROLLING
        keywords = {"X_FIRTRG": "INT"}
        self.update_keywords(keywords=keywords)
        return None    

    def set_mode_triggered(self):
        """
        Switch FIRST-PL to triggered acquisition mode, in which the camera is externally
        triggered and the TT modulates the position
        """
        if self.mode == TRIGGERED:
            print("Already in TRIGGERED mode")
            return None        
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
        self.mode = TRIGGERED
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

    def save_with_fitslogger(self, nimages = 100, ncubes = 1, tint = 0.1, readout_mode = None, dirname = None, data_typ = "OBJECT"): 
        """
        take a cube using the logger in rolling mode
        param nimages: number of images to take in each cube
        param ncubes: number of cubes to acquire 
        param tint: integration time
        param dirname: a directory name where to save the files if not using the default
        param readout_mode: the readout mode of the camera. None for not changing it
        param data_typ: the data type for the fits header        
        """
        if self.mode != ROLLING:
            raise Exception("Camera not in 'ROLLING' mode. This function is unavailable.")
        data_typ = data_typ.upper()
        if not(data_typ in AUTHORIZED_DATATYP):
            raise Exception("DATA-TYP {} is not authorized.".format(data_typ))         
        print("Setting up camera")
        if not(readout_mode is None): 
            if self._cam.get_readout_mode() != readout_mode:
                print("Switching readout mode")
                self.set_readout_mode(readout_mode)
        self._cam.set_tint(tint) # intergation time in s        
        if not(dirname is None):
            print("Saving to {}".format(dirname))
            self.logger.set_param('dirname', dirname)
        # set header kwargs
        keywords = {"X_FIROBX": 0, 
                    "X_FIROBY": 0,
                    "X_FIRMID": 0, 
                    "X_FIRDMD": self._cam.get_readout_mode(), 
                    "X_FIRMSC": 0,
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
        self.logger.set_param('saveON', True)
        return None
    
    def get_images(self, nimages = None, ncubes = 0, tint = 0.1, mod_sequence = 1, mod_scale = 1, limit_triggers = True, delay = 10, objX = 0, objY = 0, data_typ = "OBJECT"):
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
        if self.mode != TRIGGERED:
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
            self.set_readout_mode(mode)
        self._cam.set_tint(tint) # intergation time in s
        # we need to wait until the ongoing DIT is done
        print("Waiting until DIT is finished")
        time.sleep(self._cam.get_tint()+0.1)
        # update target coordinates and change offset
        self.update_target_coordinates()
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
    
    def get_acquisition_scan(self, wait_until_done = False, tint = 0.05, mod_scale = 200, **kwargs):
        """
        Perform an acquisition scan to try to locate the maximum injection
        @param wait_until_done: if True, will only returns when the fits file is available
        check get_images method for potential keywords to add
        """
        nimages = 144
        ncubes = 1
        timeout = (tint + 0.01) * nimages + 15 
        self.get_images(nimages = nimages, ncubes = ncubes, tint = tint, mod_sequence = 4, mod_scale = mod_scale, data_typ = "ACQUISITION", **kwargs)
        if wait_until_done:
            self.wait_for_file_ready(timeout = timeout)
        return None

    def center_PL(self, tint = 0.05, init_scale = 200, n_iterations = 2):
        """
        perform a series of scans to find the maximum injection and recenter the zabers
        """
        scales = [init_scale] + [75]*(n_iterations - 1)
        for k in range(n_iterations):
            print("Iteration number {}/{}".format(k+1, n_iterations))
            self.get_acquisition_scan(wait_until_done = True, tint = tint, mod_scale = scales[k])
            x, y = self._ins.opti_flux(plot_it = False)
            print("Found maximum at x={:.2f} mas, y={:.2f} mas".format(x, y))
            xzab, yzab = Geometry.tt_to_zab(x, y)
            self._zab.delta_move(-xzab, -yzab)
        # last scan for checking
        self.get_acquisition_scan(wait_until_done = True, tint = tint, mod_scale = 75)            
        return None
