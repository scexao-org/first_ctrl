# coding: utf-8
from .baseDriver import BaseDriver

class LanternDriver(object):
    def __init__(self, *args, **kwargs):
        self._driver = BaseDriver(*args, **kwargs)
        return None

    def echo(self, message=None):
        """
        reply with the given message
        @param (array or list of int 0-255) message: message
        """
        params = {}
        params["message"] = message
        cmd_data_dict = {"command_id": 1, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def reset_modulation_loop(self):
        """
        reset the modulation to its initial position
        """
        params = {}
        cmd_data_dict = {"command_id": 4, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def switch_modulation_loop(self, state=None):
        """
        turn on/off the modulation loop
        @param (boolean) state: true/false for on/off
        """
        params = {}
        params["state"] = state
        cmd_data_dict = {"command_id": 3, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def switch_flashing_mode(self, state=None):
        """
        turn on/off the flashing mode for updating modulation sequences
        @param (boolean) state: true/false for on/off
        """
        params = {}
        params["state"] = state
        cmd_data_dict = {"command_id": 2, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def switch_control_loop(self, state=None):
        """
        turn on/off the control loop
        @param (boolean) state: true/false for on/off
        """
        params = {}
        params["state"] = state
        cmd_data_dict = {"command_id": 21, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def switch_closed_loop(self, state=None):
        """
        open or close the loop
        @param (boolean) state: true/false for closed_open
        """
        params = {}
        params["state"] = state
        cmd_data_dict = {"command_id": 26, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def switch_hk_data(self, state=None):
        """
        turn on/off the automatic HK reporting
        @param (boolean) state: true/false for on/off
        """
        params = {}
        params["state"] = state
        cmd_data_dict = {"command_id": 22, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def switch_control_data(self, state=None):
        """
        turn on/off the automatic data reporting
        @param (boolean) state: true/false for on/off
        """
        params = {}
        params["state"] = state
        cmd_data_dict = {"command_id": 28, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def get_temperature(self):
        """
        return the temperature value
        """
        params = {}
        cmd_data_dict = {"command_id": 6, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def get_voltage_hv(self):
        """
        return the value of the piezo HV voltage
        """
        params = {}
        cmd_data_dict = {"command_id": 7, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def get_voltage_5v(self):
        """
        return the value of the 5V line
        """
        params = {}
        cmd_data_dict = {"command_id": 8, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def get_modulation_scale(self):
        """
        return the value of the modulation scale
        """
        params = {}
        cmd_data_dict = {"command_id": 29, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def set_modulation_scale(self, scale=None):
        """
        set the value of the modulation scale
        @param (float) scale: the modulation scale (multiplicative factor applied)
        """
        params = {}
        params["scale"] = scale
        cmd_data_dict = {"command_id": 30, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def get_modulation_prescaler(self):
        """
        return the value of the modulation prescaler
        """
        params = {}
        cmd_data_dict = {"command_id": 31, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def get_tracking(self):
        """
        return true/false depening on whether the electronics is tracking the modulation offset
        """
        params = {}
        cmd_data_dict = {"command_id": 39, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def switch_tracking(self, state=None):
        """
        turn on/off the tracking of the modulation offset
        @param (boolean) state: true/false for on/off
        """
        params = {}
        params["state"] = state
        cmd_data_dict = {"command_id": 40, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def set_modulation_prescaler(self, prescaler=None):
        """
        set the value of the modulation prescaler to get multiple DITs per position
        @param (int 0-65535) prescaler: the modulation prescaler (number of DITs at each position)
        """
        params = {}
        params["prescaler"] = prescaler
        cmd_data_dict = {"command_id": 32, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def get_piezo_command(self):
        """
        return the activate command on the piezo 
        """
        params = {}
        cmd_data_dict = {"command_id": 33, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def get_piezo_position(self):
        """
        return the position of the piezo from SG (x, y)
        """
        params = {}
        cmd_data_dict = {"command_id": 10, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def move_piezo(self, x=None, y=None):
        """
        set the piezo setpoint to given coorinates
        @param (float) x: piezo setpoint on x axis (in mas)
        @param (float) y: piezo setpoint on y axis (in mas)
        """
        params = {}
        params["x"] = x
        params["y"] = y
        cmd_data_dict = {"command_id": 9, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def delta_move_piezo(self, dx=None, dy=None):
        """
        set the piezo setpoint to given coorinates, relative to current setpoint
        @param (float) dx: delta piezo setpoint on x axis (in mas)
        @param (float) dy: delta piezo setpoint on y axis (in mas)
        """
        params = {}
        params["dx"] = dx
        params["dy"] = dy
        cmd_data_dict = {"command_id": 44, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def set_modulation_sequence(self, startpoint=None, npoints=None, xmod=None, ymod=None):
        """
        set the sequence of values to be send to the piezo
        @param (int 0-65535) startpoint: the index of the point where to start writting in RAM
        @param (int 0-65535) npoints: the number of points to write in the sequence
        @param (float,float*) xmod,ymod: the coordinates of the modulation points
        """
        params = {}
        params["startpoint"] = startpoint
        params["npoints"] = npoints
        params["xmod"] = xmod
        params["ymod"] = ymod
        cmd_data_dict = {"command_id": 12, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def flash_sequence(self, sequence=None, npoints=None, xcrc=None, ycrc=None):
        """
        flash the sequence currently loaded in RAM to the given modulation sequence in FLASH
        @param (int 0-255) sequence: the sequence id to overwrite (1 to 5 is FLASH, 0 is RAM)
        @param (int 0-65535) npoints: the number of points in the sequence
        @param (int 0-2**32) xcrc: the CRC calculated on the X sequence
        @param (int 0-2**32) ycrc: the CRC calculated on the Y sequence 
        """
        params = {}
        params["sequence"] = sequence
        params["npoints"] = npoints
        params["xcrc"] = xcrc
        params["ycrc"] = ycrc
        cmd_data_dict = {"command_id": 17, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def get_modulation_sequence(self, sequence=None):
        """
        retrieve the sequence of values for the modulation
        @param (int 0-255) sequence: the sequence id to be read (1 to 5)
        """
        params = {}
        params["sequence"] = sequence
        cmd_data_dict = {"command_id": 11, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def get_modulation_sequence_id(self):
        """
        returns the id number of the modulation sequence currently in use
        """
        params = {}
        cmd_data_dict = {"command_id": 36, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def load_sequence_from_flash(self, sequence=None):
        """
        load a modulation sequence from the FLASH, and start to use it
        @param (int 0-255) sequence: the sequence id to be read (1 to 5)
        """
        params = {}
        params["sequence"] = sequence
        cmd_data_dict = {"command_id": 13, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def download_data(self):
        """
        offload tha control data buffer in a TC reply packet
        """
        params = {}
        cmd_data_dict = {"command_id": 14, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def reset_control_data_counter(self):
        """
        reset the data counter to 0
        """
        params = {}
        cmd_data_dict = {"command_id": 15, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def set_max_counter_to_save(self, counter=None):
        """
        set the value of the counter which indicates last counter to be saved in data buffer
        @param (int 0-2**32) counter: the value to set for the counter (0xFFFFFFFF for saving indefinitely)
        """
        params = {}
        params["counter"] = counter
        cmd_data_dict = {"command_id": 16, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def use_config_on_next_boot(self, config_id=None):
        """
        decide which configuration should be use staring on next boot
        @param (int 0-255) config_id: the value (1 to 3, or 255 for default) of the config to use
        """
        params = {}
        params["config_id"] = config_id
        cmd_data_dict = {"command_id": 19, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def upload_config(self, config_id=None, name=None, system_id=None, control_loop_period=None, modulation_period=None, hk_period=None, data_period=None, sg_adc_period=None, tx_timeout=None, i2c_timeout=None, conversion_factor_hv=None, conversion_factor_5v=None, internal_trigger=None, output_trigger_delay=None, close_loop_on_boot=None, location_lat=None, location_lon=None, sky_in_sg_origin_x=None, sky_in_sg_origin_y=None, sky_to_sg_conversion_matrix_11=None, sky_to_sg_conversion_matrix_12=None, sky_to_sg_conversion_matrix_21=None, sky_to_sg_conversion_matrix_22=None, sg_in_com_origin_x=None, sg_in_com_origin_y=None, sg_to_com_conversion_matrix_11=None, sg_to_com_conversion_matrix_12=None, sg_to_com_conversion_matrix_21=None, sg_to_com_conversion_matrix_22=None, piezo_command_lower_limit=None, piezo_command_upper_limit=None, sg_adc_filter_omega_knot=None, max_piezo_step=None, xdac_address=None, ydac_address=None, xsg_ind=None, ysg_ind=None, max_counter_to_save=None, decimation=None, hk_active_on_boot=None, data_active_on_boot=None, control_active_on_boot=None, modulation_active_on_boot=None, piezo_x_setpoint_on_boot=None, piezo_y_setpoint_on_boot=None, use_shaping=None, shaping_slope=None, pid_coeff_p=None, pid_coeff_i=None, pid_coeff_d=None):
        """
        THIS FUNCTION IS NOT INTENDED FOR THE END USER.
        @param (int 0-255) config_id: the id where to save the config
        @param (string) name: the name of the config file
        @param (int 0-255) system_id: 
        @param (int 0-2**32) control_loop_period: 
        @param (int 0-2**32) modulation_period: 
        @param (int 0-2**32) hk_period: 
        @param (int 0-2**32) data_period: 
        @param (int 0-65535) sg_adc_period: 
        @param (int 0-2**32) tx_timeout: 
        @param (int 0-2**32) i2c_timeout: 
        @param (float) conversion_factor_hv: 
        @param (float) conversion_factor_5v: 
        @param (int 0-255) internal_trigger: 
        @param (int 0-65535) output_trigger_delay: 
        @param (int 0-255) close_loop_on_boot: 
        @param (float) location_lat: 
        @param (float) location_lon: 
        @param (float) sky_in_sg_origin_x: 
        @param (float) sky_in_sg_origin_y: 
        @param (float) sky_to_sg_conversion_matrix_11: 
        @param (float) sky_to_sg_conversion_matrix_12: 
        @param (float) sky_to_sg_conversion_matrix_21: 
        @param (float) sky_to_sg_conversion_matrix_22: 
        @param (float) sg_in_com_origin_x: 
        @param (float) sg_in_com_origin_y: 
        @param (float) sg_to_com_conversion_matrix_11: 
        @param (float) sg_to_com_conversion_matrix_12: 
        @param (float) sg_to_com_conversion_matrix_21: 
        @param (float) sg_to_com_conversion_matrix_22: 
        @param (int 0-65535) piezo_command_lower_limit: 
        @param (int 0-65535) piezo_command_upper_limit: 
        @param (float) sg_adc_filter_omega_knot: 
        @param (float) max_piezo_step: 
        @param (int 0-255) xdac_address: 
        @param (int 0-255) ydac_address: 
        @param (int 0-255) xsg_ind: 
        @param (int 0-255) ysg_ind: 
        @param (int 0-2**32) max_counter_to_save: 
        @param (int 0-65535) decimation: 
        @param (int 0-255) hk_active_on_boot: 
        @param (int 0-255) data_active_on_boot: 
        @param (int 0-255) control_active_on_boot: 
        @param (int 0-255) modulation_active_on_boot: 
        @param (float) piezo_x_setpoint_on_boot: 
        @param (float) piezo_y_setpoint_on_boot: 
        @param (int 0-255) use_shaping: 
        @param (float) shaping_slope: 
        @param (float) pid_coeff_p: 
        @param (float) pid_coeff_i: 
        @param (float) pid_coeff_d: 
        """
        params = {}
        params["config_id"] = config_id
        params["name"] = name
        params["system_id"] = system_id
        params["control_loop_period"] = control_loop_period
        params["modulation_period"] = modulation_period
        params["hk_period"] = hk_period
        params["data_period"] = data_period
        params["sg_adc_period"] = sg_adc_period
        params["tx_timeout"] = tx_timeout
        params["i2c_timeout"] = i2c_timeout
        params["conversion_factor_hv"] = conversion_factor_hv
        params["conversion_factor_5v"] = conversion_factor_5v
        params["internal_trigger"] = internal_trigger
        params["output_trigger_delay"] = output_trigger_delay
        params["close_loop_on_boot"] = close_loop_on_boot
        params["location_lat"] = location_lat
        params["location_lon"] = location_lon
        params["sky_in_sg_origin_x"] = sky_in_sg_origin_x
        params["sky_in_sg_origin_y"] = sky_in_sg_origin_y
        params["sky_to_sg_conversion_matrix_11"] = sky_to_sg_conversion_matrix_11
        params["sky_to_sg_conversion_matrix_12"] = sky_to_sg_conversion_matrix_12
        params["sky_to_sg_conversion_matrix_21"] = sky_to_sg_conversion_matrix_21
        params["sky_to_sg_conversion_matrix_22"] = sky_to_sg_conversion_matrix_22
        params["sg_in_com_origin_x"] = sg_in_com_origin_x
        params["sg_in_com_origin_y"] = sg_in_com_origin_y
        params["sg_to_com_conversion_matrix_11"] = sg_to_com_conversion_matrix_11
        params["sg_to_com_conversion_matrix_12"] = sg_to_com_conversion_matrix_12
        params["sg_to_com_conversion_matrix_21"] = sg_to_com_conversion_matrix_21
        params["sg_to_com_conversion_matrix_22"] = sg_to_com_conversion_matrix_22
        params["piezo_command_lower_limit"] = piezo_command_lower_limit
        params["piezo_command_upper_limit"] = piezo_command_upper_limit
        params["sg_adc_filter_omega_knot"] = sg_adc_filter_omega_knot
        params["max_piezo_step"] = max_piezo_step
        params["xdac_address"] = xdac_address
        params["ydac_address"] = ydac_address
        params["xsg_ind"] = xsg_ind
        params["ysg_ind"] = ysg_ind
        params["max_counter_to_save"] = max_counter_to_save
        params["decimation"] = decimation
        params["hk_active_on_boot"] = hk_active_on_boot
        params["data_active_on_boot"] = data_active_on_boot
        params["control_active_on_boot"] = control_active_on_boot
        params["modulation_active_on_boot"] = modulation_active_on_boot
        params["piezo_x_setpoint_on_boot"] = piezo_x_setpoint_on_boot
        params["piezo_y_setpoint_on_boot"] = piezo_y_setpoint_on_boot
        params["use_shaping"] = use_shaping
        params["shaping_slope"] = shaping_slope
        params["pid_coeff_p"] = pid_coeff_p
        params["pid_coeff_i"] = pid_coeff_i
        params["pid_coeff_d"] = pid_coeff_d
        cmd_data_dict = {"command_id": 18, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def software_reboot(self):
        """
        restart the software (in particular, this will reload the configuration)
        """
        params = {}
        cmd_data_dict = {"command_id": 20, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def set_datetime(self, year=None, month=None, day=None, hour=None, minute=None, second=None):
        """
        set the date and time on the RTC clock
        @param (int 0-65535) year: year number (ex 2025)
        @param (int 0-255) month: month number (ex 8)
        @param (int 0-255) day: day number (ex 11)
        @param (int 0-255) hour: hour number in 24h format (ex 14)
        @param (int 0-255) minute: minute number (ex 55)
        @param (int 0-255) second: second number (ex 47)
        """
        params = {}
        params["year"] = year
        params["month"] = month
        params["day"] = day
        params["hour"] = hour
        params["minute"] = minute
        params["second"] = second
        cmd_data_dict = {"command_id": 23, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def get_datetime(self):
        """
        return the date and time from the RTC clock
        """
        params = {}
        cmd_data_dict = {"command_id": 24, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def get_version(self):
        """
        return the version number of the code and the config name currently in use
        """
        params = {}
        cmd_data_dict = {"command_id": 5, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def set_modulation_offset(self, npoints=None, x_offset=None, y_offset=None):
        """
        set the center point of the modulation pattern
        @param (int 0-255) npoints: number of points
        @param (list of float) x_offset: offset on x axis (in um)
        @param (list of float) y_offset: offset on y axis (in um)
        """
        params = {}
        params["npoints"] = npoints
        params["x_offset"] = x_offset
        params["y_offset"] = y_offset
        cmd_data_dict = {"command_id": 25, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def set_decimation(self, decimation=None):
        """
        set the decimation factor to save one point every n points
        @param (int 0-65535) decimation: decimation factor
        """
        params = {}
        params["decimation"] = decimation
        cmd_data_dict = {"command_id": 27, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def start_output_trigger(self, delay=None):
        """
        activate the output trigger for the camera (will start exposures). 
        @param (int 0-65535) delay: the delay between the modulation move and the trigger (in ms)
        """
        params = {}
        params["delay"] = delay
        cmd_data_dict = {"command_id": 34, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def stop_output_trigger(self):
        """
        deactivate the output trigger for the camera (will stop exposures after the current one). 
        """
        params = {}
        cmd_data_dict = {"command_id": 35, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def get_lst_seconds(self):
        """
        get the number of seconds (0 to 86400) elapsed since the beginning of day
        """
        params = {}
        cmd_data_dict = {"command_id": 37, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def set_lst_seconds(self, seconds=None):
        """
        set the number of seconds (0 to 86400) elapsed since the beginning of day
        @param (float) seconds: number of seconds (0 to 86400)
        """
        params = {}
        params["seconds"] = seconds
        cmd_data_dict = {"command_id": 38, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def set_target_coords(self, ra=None, dec=None):
        """
        set the pointing coordinates (to calculate parallactic angle)
        @param (float) ra: Right Ascension (hourangle)
        @param (float) dec: Declination (degrees)
        """
        params = {}
        params["ra"] = ra
        params["dec"] = dec
        cmd_data_dict = {"command_id": 42, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def get_target_coords(self):
        """
        retrieve the current pointing coordinates used to calculate parallactic angle
        """
        params = {}
        cmd_data_dict = {"command_id": 41, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

    def get_parangle(self):
        """
        retrieve the current parangle as calculated by the electronics
        """
        params = {}
        cmd_data_dict = {"command_id": 43, "params": params}
        command_dict = self._driver.generate_tc_from_data(cmd_data_dict)
        return self._driver.simple_send_command(command_dict)

