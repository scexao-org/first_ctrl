#coding: utf8
from plscripts.base import Base
import time
import numpy as np
import os
from astropy.io import fits
from scipy.interpolate import griddata
from scipy.optimize import curve_fit

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
        col_x = fits.Column(name='ymod', format='E', unit="mas", array=xmod)
        col_y = fits.Column(name='xmod', format='E', unit="mas", array=ymod)
        hdu = fits.TableHDU.from_columns([col_ind, col_x, col_y], name = "Modulation")
        hdu.header["MODID"] = mod_id
        hdu.writeto(self._config["modulation_fits_path"], overwrite = True)
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

        print("changing DIT to low value (to stop long exposure)")
        self._cam.set_tint(0.1)
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
        # check if we need to remake the modulation file
        print("Remaking modulation.fits")
        (xmod, ymod) = self._scripts.retrieve_modulation_sequence(mod_sequence)
        self._ld.get_modulation_scale()
        self._db.validate_last_tc()
        scale = self._db.tcs[-1].reply[0]["data"]["tc_reply_data"]["scale"]
        self.save_modulation_extension(scale*xmod, scale*ymod, mod_sequence)
        # now we can set up the camera 
        print("setting up camera")
        self._cam.set_tint(tint) # intergation time in s
        self._cam.set_output_trigger_options("anyexposure", "low", self._config["cam_to_ld_trigger_port"])
        self._cam.set_external_trigger(1)
        # we need to wait until the ongoing DIT is done
        print("Waiting until DIT is finished")
        time.sleep(self._cam.get_tint()+0.1)
        # get ready to save files
        print("Getting ready to save files")
        self.prepare_fitslogger(nimages = nimages, ncubes = ncubes)
        time.sleep(0.5)
        # reset the modulation loop and start
        print("Starting integration")
        self._ld.reset_modulation_loop()
        self._db.validate_last_tc()
        self._ld.start_output_trigger()#//(delay = delay) # TODO - need to flash new code
        self._db.validate_last_tc()
        return None
    

    def opti_flux(data_path = "/mnt/datazpool/PL/") :
        """
        After running opti_scan to run a grid scan, display the associated 
        flux map to find the position maximizing the flux
        
        * maybe we want the SCAN data to be saved with a specific name (including "scan" in the filename for instance)
        """

        # Function to find the latest fits file that was writen
        def find_most_recent_fits_file(directory):
            most_recent_file = None
            most_recent_mtime = 0

            for root, _, files in os.walk(directory):
                for filename in files:
                    if filename.endswith('.fits'):
                        filepath = os.path.join(root, filename)
                        if os.path.isfile(filepath):
                            mtime = os.path.getmtime(filepath)
                            if mtime > most_recent_mtime:
                                most_recent_mtime = mtime
                                most_recent_file = filepath

            return most_recent_file

        # Define a 2D Gaussian function
        def gaussian_2d(xy, amplitude, xo, yo, sigma, offset):
            x, y = xy
            xo = float(xo)
            yo = float(yo)
            w = 1/(sigma**2)
            g = offset + amplitude * np.exp(-(w*((x-xo)**2) + w*((y-yo)**2)))
            return g.ravel()
        

        # finding the most recent dataset:
        most_recent = find_most_recent_fits_file(data_path)

        if most_recent:
            print(f"Most recent .fits file: {most_recent}")
        else:
            print("No .fits files found.")

        # reading the modulation function
        hdu = fits.open(most_recent)
        xmod = hdu[1].data['xmod']
        ymod = hdu[1].data['ymod']

        # reading the flux
        fluxes = np.mean(hdu[0].data, axis=(1,2))
        xmin, xmax   = np.min(xmod), np.max(xmod)
        ymin, ymax   = np.min(ymod), np.max(ymod)

        # Define the grid for interpolation
        grid_x, grid_y = np.mgrid[xmin:xmax:500j, ymin:ymax:500j]  # 500x500 grid

        # Interpolate the fluxes onto the grid
        flux_map = griddata((xmod, ymod), fluxes, (grid_x, grid_y), method='cubic')

        # Prepare data for fitting
        z = fluxes
        x = xmod
        y = ymod
        amplitude_0=np.max(fluxes)-np.min(fluxes)
        x_0= x[fluxes.argmax()]
        y_0= y[fluxes.argmax()]
        sigma_0 = (x.max()-x.min())/4
        offset_0=np.min(fluxes)

        # Initial guess for the parameters
        initial_guess = (amplitude_0,x_0,y_0,sigma_0,offset_0)

        # Fit the Gaussian
        popt, _ = curve_fit(gaussian_2d, (x, y), z, p0=initial_guess)
        x_fit=popt[1]
        y_fit=popt[2]

        # Generate the fitted Gaussian for plotting
        fitted_gaussian = gaussian_2d((grid_x, grid_y), *popt).reshape(grid_x.shape)

        # Plot the contours of the fitted Gaussian on top of the image
        # Plot the interpolated 2D image
        import matplotlib.pyplot as plt
        plt.ion()

        plt.figure("Interpolated Flux",clear=True)
        plt.imshow(flux_map.T, extent=(xmin, xmax, ymin, ymax), origin="lower", aspect='auto')
        plt.colorbar(label="Flux")
        plt.xlabel("X")
        plt.ylabel("Y")
        plt.title("(Xmod,Ymod) maximum position: (%.3f,%.3f)"%(x_fit,y_fit))
        plt.contour(grid_x, grid_y, fitted_gaussian, levels=10, colors='red', linewidths=0.8)
