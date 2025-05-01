#coding: utf8
import time
import numpy as np
from byt import Byt
import struct
from ruamel import yaml
import datetime

PIEZO_RANGE = [32768, 32768]

class LanternScripts(object):
    def __init__(self, ld = None, db = None):
        self._ld = ld
        self._db = db
        return None
    
    def _validate_last_tc(self, timeout = 3):
        """
        wait for ack for last tc sent and raise and exception if an error occured
        """
        t0 = time.time()
        while (self._db.tcs[-1].eack is None):
            time.sleep(0.1)
            if (time.time() - t0) > timeout:
                raise Exception("Timeout!")
        error = self._db.tcs[-1].eack["data"]["error"]
        if error != "OK":
            raise Exception("Error {} occured".format(error))
        return None
        
    def retrieve_modulation_sequence(self, sequence = None, timeout = 10):
        """
        Return the xmod, ymod values of the modulation sequence.
        @param sequence: the id of the sequence to retrive (from 1 to 5)
        """
        if not(sequence in [1, 2, 3, 4, 5]):
            raise Exception("Please provide a sequence id between 1 and 5")
        t0 = time.time()
        self._ld.get_modulation_sequence(sequence = sequence)
        while (self._db.tcs[-1].eack is None):
            time.sleep(0.1)
            if (time.time() - t0) > timeout:
                raise Exception("Timeout!")
        if len(self._db.tcs[-1].reply) == 0:
            raise Exception("Did not get a reply")
        tc = self._db.tcs[-1]
        npoints = tc.reply[0]["data"]["tc_reply_data"]["npoints"]
        npoints_received = 0
        while(npoints_received != npoints):
            if (time.time() - t0) > timeout:
                raise Exception("Timeout!")        
            npoints_received = np.array([len(r["data"]["tc_reply_data"]["xmod"]) for r in tc.reply]).sum()
        # gather data in proper order
        xmod = np.zeros(npoints)
        ymod = np.zeros(npoints)
        for r in tc.reply:
            startpoint = r["data"]["tc_reply_data"]["startpoint"]
            xmod[startpoint:] = r["data"]["tc_reply_data"]["xmod"]
            ymod[startpoint:] = r["data"]["tc_reply_data"]["ymod"]        
        return xmod, ymod
    
    def upload_modulation_sequence(self, sequence = None, xmod = None, ymod = None, timeout = 10):
        """
        Set the modulation sequence "sequence" with the given xmod and ymod
        @param sequence: the id of the modulation sequence to overwrite in FLASH (1 to 5)
        @param xmod, ymod: the values (x and y axes, in um) of the modulation sequences. Should be lists or arrays of same length
        """
        if not(sequence in [1, 2, 3, 4, 5]):
            raise Exception("Please provide a sequence id between 1 and 5")
        if len(xmod) != len(ymod):
            raise Exception("xmod and ymod should be of same length")
        if len(xmod) > 625:
            raise Exception("Modulation sequence is too long! The limit is 625 points")
        # first we need to set the flash mode
        self._ld.switch_modulation_loop(state = False)
        self._db.validate_last_tc()
        self._ld.switch_flashing_mode(state = True)
        self._db.validate_last_tc()
        # now we need to upload the sequence bit by bit as we are limited in packet size
        nmod = len(xmod)
        n_points_per_packet = 200 # will put 200 points per packet
        npackets = 1 + nmod//n_points_per_packet
        for k in range(npackets):
            startpoint = k*n_points_per_packet
            npoints = min(n_points_per_packet, nmod - k*n_points_per_packet)
            x = xmod[k*n_points_per_packet:(k+1)*n_points_per_packet]
            y = ymod[k*n_points_per_packet:(k+1)*n_points_per_packet]
            self._ld.set_modulation_sequence(startpoint = startpoint, npoints = npoints, xmod = x, ymod = y)
            self._db.validate_last_tc()
        # now we can request flashing. For this we need the crs
        xmod_bytes, ymod_bytes = Byt(), Byt()
        for k in range(nmod):
            xmod_bytes+=Byt(struct.pack("f", xmod[k]))
            ymod_bytes+=Byt(struct.pack("f", ymod[k]))
        xcrc = self._ld._driver.punp._compute_crc32(xmod_bytes)
        ycrc = self._ld._driver.punp._compute_crc32(ymod_bytes)
        self._ld.flash_sequence(sequence = sequence, npoints = nmod, xcrc = xcrc, ycrc = ycrc)
        self._db.validate_last_tc()
        self._ld.switch_flashing_mode(state = False)   
        self._db.validate_last_tc()             
        return None
    
    def upload_configuration_file(self, config_id = None, filename = None, reboot = False):
        """
        Load a config dict and upload it to the board, under the config_id number.
        @param config_id: the configuration id number where to save it on the flash memory (1 to 5)
        @param filename: the file containing the yml config dictionnary
        @param reboot: if set to true, set the config to use on boot to the new config_id, and reboot
        """
        if not(config_id in [1, 2, 3]):
            raise Exception("Please provide a valid config_id (1 to 3)")
        loader = yaml.YAML()
        config = loader.load(open(filename).read())
        self._ld.upload_config(config_id=config_id, **config)
        self._db.validate_last_tc()
        if reboot:
            self._ld.use_config_on_next_boot(config_id = config_id)
            self._db.validate_last_tc()
            self._ld.software_reboot()

    def get_dataset(self, npoints = 200, decimation = 1, timeout = 15, wait = 1):
        """
        save a small dataset for studying the control loop
        """
        self._ld.set_max_counter_to_save(npoints*decimation)
        self._db.validate_last_tc()
        self._ld.set_decimation(decimation)
        self._db.validate_last_tc()
        self._ld.reset_control_data_counter()
        self._db.validate_last_tc()
        time.sleep(wait)
        t0 = time.time()
        self._ld.download_data()
        self._db.validate_last_tc()
        if len(self._db.tcs[-1].reply) == 0:
            raise Exception("Did not get a reply")
        tc = self._db.tcs[-1]
        npoints_received = len(tc.reply[0]["data"]["tc_reply_data"]["counter"])
        while(npoints_received < npoints):
            if (time.time() - t0) > timeout:
                raise Exception("Timeout!")        
            npoints_received = np.array([len(r["data"]["tc_reply_data"]["counter"]) for r in tc.reply]).sum()
        # gather data
        counter = np.concatenate([reply["data"]["tc_reply_data"]["counter"] for reply in tc.reply])        
        microseconds = np.concatenate([reply["data"]["tc_reply_data"]["microseconds"] for reply in tc.reply])
        xcom = np.concatenate([reply["data"]["tc_reply_data"]["xcom"] for reply in tc.reply])
        ycom = np.concatenate([reply["data"]["tc_reply_data"]["ycom"] for reply in tc.reply])
        xpos = np.concatenate([reply["data"]["tc_reply_data"]["xpos"] for reply in tc.reply])
        ypos = np.concatenate([reply["data"]["tc_reply_data"]["ypos"] for reply in tc.reply])  
        xset = np.concatenate([reply["data"]["tc_reply_data"]["xset"] for reply in tc.reply])
        yset = np.concatenate([reply["data"]["tc_reply_data"]["yset"] for reply in tc.reply])
        xset_shaped = np.concatenate([reply["data"]["tc_reply_data"]["xset_shaped"] for reply in tc.reply])
        yset_shaped = np.concatenate([reply["data"]["tc_reply_data"]["yset_shaped"] for reply in tc.reply])                                              
        return counter, microseconds, xcom, ycom, xpos, ypos, xset, yset, xset_shaped, yset_shaped
    
    def get_noise_sequence(self, nreadouts = 30, xcom = None, ycom = None):
        """
        set the piezo to the middle of the range, and take a series of SG readout
        @param nreadouts: the number of points to read
        @param xcom, ycom: command to send to the piezo before reading (default to midrange)
        """
        if xcom is None:
            xcom = PIEZO_RANGE[1]/2
        if ycom is None:
            ycom = PIEZO_RANGE[1]/2
        self._ld.move_piezo(xcom, ycom)
        self._db.validate_last_tc()
        time.sleep(3) # wait for stable piezo
        xpos, ypos = np.zeros(nreadouts), np.zeros(nreadouts)
        for k in range(nreadouts):
            time.sleep(0.2)
            self._ld.get_piezo_position()
            self._db.validate_last_tc()
            tc = self._db.tcs[-1]
            x, y = tc.reply[0]["data"]["tc_reply_data"]["x_pos"], tc.reply[0]["data"]["tc_reply_data"]["y_pos"]
            xpos[k], ypos[k] = x, y
        return xpos, ypos

    def get_open_loop_response(self, init_position = None, step = None, npoints = 200, decimation = 1, waittime = 5, timeout = 10):
        """
        return x/y the piezo response function in open loop
        """
        # default init position is center of field
        if init_position is None:
            init_position = [PIEZO_RANGE[0]/2, PIEZO_RANGE[1]/2]
        # default step is 5% of range
        if step is None:
            step = 0.05*(PIEZO_RANGE[1] - PIEZO_RANGE[0])
            step = [step, step]
        # first we need to move the piezo to init position and wait a bit
        self._ld.move_piezo(init_position[0], init_position[1])
        self._db.validate_last_tc()
        time.sleep(3) # wait for piezo to settle
        # now we switch control off
        self._ld.switch_control_loop(False)
        self._db.validate_last_tc()
        # now we need to set number of points to save and reset the counter
        self._ld.set_max_counter_to_save(npoints*decimation)
        self._db.validate_last_tc()
        self._ld.set_decimation(decimation)
        self._db.validate_last_tc()        
        self._ld.reset_control_data_counter()
        self._db.validate_last_tc()
        # now we reactivate the piezo and send a step command
        self._ld.switch_control_loop(True) # do not validate this command as we need to go fast
        self._ld.move_piezo(init_position[0]+step[0], init_position[1]+step[1])
        self._db.validate_last_tc()
        time.sleep(waittime)
        # download and return data
        t0 = time.time()
        self._ld.download_data()
        self._db.validate_last_tc()
        if len(self._db.tcs[-1].reply) == 0:
            raise Exception("Did not get a reply")
        tc = self._db.tcs[-1]
        npoints_received = len(tc.reply[0]["data"]["tc_reply_data"]["counter"])
        while(npoints_received < npoints):
            if (time.time() - t0) > timeout:
                raise Exception("Timeout!")        
            npoints_received = np.array([len(r["data"]["tc_reply_data"]["counter"]) for r in tc.reply]).sum()
        # gather data
        counter = np.concatenate([reply["data"]["tc_reply_data"]["counter"] for reply in tc.reply])        
        microseconds = np.concatenate([reply["data"]["tc_reply_data"]["microseconds"] for reply in tc.reply])
        xcom = np.concatenate([reply["data"]["tc_reply_data"]["xcom"] for reply in tc.reply])
        ycom = np.concatenate([reply["data"]["tc_reply_data"]["ycom"] for reply in tc.reply])
        xpos = np.concatenate([reply["data"]["tc_reply_data"]["xpos"] for reply in tc.reply])
        ypos = np.concatenate([reply["data"]["tc_reply_data"]["ypos"] for reply in tc.reply])  
        xset = np.concatenate([reply["data"]["tc_reply_data"]["xset"] for reply in tc.reply])
        yset = np.concatenate([reply["data"]["tc_reply_data"]["yset"] for reply in tc.reply])
        xset_shaped = np.concatenate([reply["data"]["tc_reply_data"]["xset_shaped"] for reply in tc.reply])
        yset_shaped = np.concatenate([reply["data"]["tc_reply_data"]["yset_shaped"] for reply in tc.reply])                                              
        return counter, microseconds, xcom, ycom, xpos, ypos, xset, yset, xset_shaped, yset_shaped
    
    def get_hysteresis(self, npoints = 100, xrange= None, yrange = None):
        """
        move step by step the piezo on the two axis to measure hysteresis.
        @param npoints: number of points on the one-way sequence (final array has 2*npoints length)
        @param xrange, yrange: (min, max) commands on x and y axis
        @return xcom, ycom, xpos, ypos: x/y commands and positions of the piezo. Plot xcom vs xpos for hysteresis
        """
        if xrange is None:
            xrange = 0.0, 2**15-1
        if yrange is None:
            yrange = 0.0, 2**15-1
        xmin, xmax = xrange
        ymin, ymax = yrange
        xcom, ycom = np.linspace(xmin, xmax, npoints), np.linspace(ymin, ymax, npoints)
        xcom, ycom = np.concatenate([xcom, xcom[::-1]]), np.concatenate([ycom, ycom[::-1]])        
        xpos, ypos = np.zeros(2*npoints), np.zeros(2*npoints)
        for k in range(2*npoints):
            self._ld.move_piezo(xcom[k], ycom[k])
            self._db.validate_last_tc()
            time.sleep(0.2) # for piezo to stabilize
            self._ld.get_piezo_position()
            self._db.validate_last_tc()
            tc = self._db.tcs[-1]
            x, y = tc.reply[0]["data"]["tc_reply_data"]["x_pos"], tc.reply[0]["data"]["tc_reply_data"]["y_pos"]
            xpos[k], ypos[k] = x, y
        return (xcom, ycom, xpos, ypos)

    def set_utcnow(self):
        utcnow = datetime.datetime.utcnow()
        dt = {"year": utcnow.year,
              "month": utcnow.month,
              "day": utcnow.day,
              "hour": utcnow.hour,
              "minute": utcnow.minute,
              "second": utcnow.second}
        self._ld.set_datetime(**dt)
        self._db.validate_last_tc()
        return None

    def construct_mu_table(self, npoints = 5):
        """
        construct the mu table used in the MATLAB hysteresis model of the piezo
        """
        alphas = np.linspace(0, 2**15-1, npoints)
        betas = np.linspace(0, 2**15-1, npoints)
        mu = np.zeros([npoints, npoints])
        self._ld.move_piezo(0, 0)
        time.sleep(1)
        self._ld.get_piezo_position()
        self._db.validate_last_tc()
        tc = self._db.tcs[-1]        
        x, _ = tc.reply[0]["data"]["tc_reply_data"]["x_pos"]                 
        X = np.zeros([npoints+1, npoints+1]) + x
        for k in range(npoints):
            self._ld.move_piezo(alphas[k], 0)
            self._db.validate_last_tc()
            time.sleep(0.1)
            for j in range(k, -1, -1):
                self._ld.move_piezo(betas[j], 0)
                self._db.validate_last_tc()
                time.sleep(0.1)
                self._ld.get_piezo_position()
                self._db.validate_last_tc()
                tc = self._db.tcs[-1]
                x, _ = tc.reply[0]["data"]["tc_reply_data"]["x_pos"]             
                X[k+1, j+1] = x
        X = -(X - X[0, 0])
        mu = np.zeros([npoints, npoints])
        for k in range(0, npoints):
            for j in range(0, k):
                mu[k, j] = (X[k+1, j+1] - X[k, j+1]) - (X[k+1, j] - X[k, j])
        return alphas, betas, mu

