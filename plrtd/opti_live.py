
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

class LiveOptiFlux(StoppableThread):
    """
    Real time display of the reconstructed images.
    """
    def __init__(self, vmin = None, vmax = None, *args, **kwargs):
        super(LiveOptiFlux, self).__init__(*args, **kwargs)
        self.vmin = vmin
        self.vmax = vmax 
        self.logger = FPS('streamFITSlog-firstpl')

    def get_fitslogger_logdir(self):
        """
        interacts with the fits logger to get the path where data are currently saved
        """
        dirname = self.logger.get_param("dirname")
        return dirname
    
    def find_most_recent_fits_file(self, directory):
        """
        get the the latest fits file that was writen     
        """   
        most_recent_file = None
        most_recent_mtime = 0
        for root, _, files in os.walk(directory):
            for filename in files:
                if filename.endswith('.fits'):
                    filepath = os.path.join(root, filename)
                    if os.path.isfile(filepath):
                        hd = fits.getheader(filepath)
                        first_type = hd.get('X_FIRTYP', "UNKNOWN")
                        trigger = hd.get('X_FIRTRG', "UNKNOWN")
                        if (first_type == "RAW") and (trigger == "EXT"):
                            mtime = os.path.getmtime(filepath)
                            if mtime > most_recent_mtime:
                                most_recent_mtime = mtime
                                most_recent_file = filepath
        return most_recent_file  
        
    def opti_flux(self, data_path = None, filename = None) :
        """
        After running opti_scan to run a grid scan, display the associated 
        flux map to find the position maximizing the flux        
        * maybe we want the SCAN data to be saved with a specific name (including "scan" in the filename for instance)
        """
        # get the data path from logger if none
        if filename is None:
            if data_path is None:
                data_path = self.get_fitslogger_logdir()
            # finding the most recent dataset:
            most_recent = self.find_most_recent_fits_file(data_path)
            filename = most_recent

        # reading the modulation function
        hdu = fits.open(filename)
        objX, objY = hdu[0].header["X_FIROBX"], hdu[0].header["X_FIROBY"] 
        xmod = hdu[1].data['xmod']
        ymod = hdu[1].data['ymod']

        # reading the flux
        fluxes = np.mean(hdu[0].data, axis=(1,2))
        xmin, xmax   = np.min(xmod), np.max(xmod)
        ymin, ymax   = np.min(ymod), np.max(ymod)

        # Define the grid for interpolation
        grid_x, grid_y = np.mgrid[xmin:xmax:500j, ymin:ymax:500j]  # 500x500 grid

        # check if cube bigger then Nmod.
        # if so, just plot the last cube
        Ndit = len(fluxes)
        Nmod = len(xmod)
        Ncube = Ndit//Nmod

        if (Ncube*Nmod)!=Ndit:
            print("WARNING, CUBE not multiple of modulation pattern")
            print("filling with zeros")
            Ncube += 1

        size_new = (Ncube,Nmod)
        size_old = Ndit

        flux_padded=np.zeros(np.prod(size_new))
        flux_padded[:size_old]=fluxes
        flux_padded=flux_padded.reshape(size_new)
        fluxes = flux_padded[-1]

        # Interpolate the fluxes onto the grid
        flux_map = griddata((xmod, ymod), fluxes, (grid_x, grid_y), method='nearest')

        """
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
        try:
            popt, _ = curve_fit(self.gaussian_2d, (x, y), z, p0=initial_guess)
            x_fit=popt[1]
            y_fit=popt[2]
        except:
            x_fit, y_fit = None, None
            print("Failed to perform fit")

        # Generate the fitted Gaussian for plotting
        if x_fit is None:
            fitted_gaussian = None
        else:  
            fitted_gaussian = self.gaussian_2d((grid_x, grid_y), *popt).reshape(grid_x.shape)

        
        # Plot the contours of the fitted Gaussian on top of the image
        # Plot the interpolated 2D image
        plt.figure("Interpolated Flux",clear=True)
        plt.imshow(flux_map.T, extent=(xmin, xmax, ymin, ymax), origin="lower", aspect='auto')
        plt.colorbar(label="Flux")
        plt.xlabel("X")
        plt.ylabel("Y")
        if not(fitted_gaussian is None):
            plt.title("(Xmod,Ymod) maximum position: (%.3f,%.3f)"%(x_fit,y_fit))
            plt.contour(grid_x, grid_y, fitted_gaussian, levels=10, colors='red', linewidths=0.8)

        """
        return flux_map.T

    
    def setting_milk(self):
        #data = self.plot_detector()

        image = self.opti_flux()
        map_void          = np.zeros((image.shape[0], image.shape[1]), dtype=np.float32)
        shm_var         = shm('first_opti', map_void, location=-1, shared=1)

        if self.vmin is not None:
            image[1,1]=self.vmin
        if self.vmax is not None:
            image[99,99]=self.vmax

        shm_var.set_data(image.astype(np.float32))

        
        return None
    
    def run(self):
        while not(self.stopped()):
            self.setting_milk()
            time.sleep(0.01)  # Adjust the delay as needed #0.1
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
    opti.opti_flux()

    # Continuously plot images as new data comes in
    opti.start()