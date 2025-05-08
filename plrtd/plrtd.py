#%%
import numpy as np
import glob
import os
from astropy.io import fits
import runPL_library_basic as basic

from pyMilk.interfacing.isio_shmlib import SHM as shm
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.pyplot import *
ion()
import time

class firstpl_rtd(object):

    def load_calibration(self):
        """
        Load the calibration files for the first light injection
        """
        # Load the coupling map and pixel map

        dir_coupling_map = "/mnt/datazpool/PL/calibration_files/"
        pattern_coupling_map = "firstpl_*_COUPLINGMAP.fits"
        dir_pixel_map = "/mnt/datazpool/PL/calibration_files/"
        pattern_pixel_map = "firstpl_*_PIXELMAP.fits"

        # Find all files matching the pattern
        coupling_map_files = glob.glob(dir_coupling_map + pattern_coupling_map)

        # If there are multiple files, select the most recent one
        if coupling_map_files:
            file_coupling_map = max(coupling_map_files, key=os.path.getmtime)
        else:
            raise FileNotFoundError("No coupling map files found matching the pattern.")

        # Find all files matching the pattern
        pixel_map_files = glob.glob(dir_pixel_map + pattern_pixel_map)

        # If there are multiple files, select the most recent one
        if pixel_map_files:
            file_pixel_map = max(pixel_map_files, key(os.path.getmtime))
        else:
            raise FileNotFoundError("No pixel map files found matching the pattern.")

        self.couplingMap=basic.CouplingMap(file_coupling_map)
        self.pixelMap=basic.PixelMap(file_pixel_map)
        self.detbias = self.pixelMap.header['DETBIAS']

        self.xpos = self.couplingMap.xpos
        self.ypos = self.couplingMap.ypos

        
        self.grid_x, self.grid_y = basic.make_image_grid(self.couplingMap, self.Npixel)


    def __init__(self):###############################################################################################
        

        self.Npixel = 100

        self.im_io  = shm('firstpl')
        self.width_im = int(self.im_io.get_keywords()['PRD-RNG2'])
        self.height_im = int(self.im_io.get_keywords()['PRD-RNG1'])

    def plot_detector(self):
        """
        Plot the detector raw image
        """
        self.im = self.im_io.get_data(False).astype(float)
        figure(1234,clear=True)
        imshow(self.im, origin='lower')
        title("Image")
        colorbar()
        show()
        return self.im

    def plot_image(self):
        """
        Plot the image
        """
        data = self.plot_detector()

        de,_=basic.preprocess_cutData(data, self.pixelMap)
        # binning data in wavelength according to the coupling map
        data=(de-self.detbias).mean(axis=2)
        Noutput=data.shape[0]
        Nwave=data.shape[1]
        Nbin=self.couplingMap.wavelength_bin

        data=data[:,:(Nwave//Nbin)*Nbin]

        data_binned=data.reshape((Noutput,Nwave//Nbin,Nbin)).sum(axis=-1)
        Nwave=data_binned.shape[1]
        print("Nwave=",Nwave)

        # create the image maps
        flux_maps_sum, fluxes = basic.make_image_maps(data_binned.T, self.couplingMap, self.grid_x, self.grid_y, wavelength=False)
        image=flux_maps_sum[0]
        fluxes = fluxes[0,:,0,0]

        popt = basic.fit_gaussian_on_flux(fluxes, self.xpos, self.ypos)
        x_fit=popt[1]
        y_fit=popt[2]
        result = "Maximum at ---> X =%9.3f Y=%9.3f" % (x_fit, y_fit)

        figure(2345,clear=True)
        imshow(image, origin='lower')
        title(result)
        print(result)
        colorbar()


# %%

if __name__ == "__main__":
    # Create an instance of the class
    rtd = firstpl_rtd()

    # Load the calibration files
    rtd.load_calibration()

    # Continuously plot images as new data comes in
    try:
        while True:
            rtd.plot_image()
            time.sleep(0.1)  # Adjust the delay as needed
    except KeyboardInterrupt:
        print("Exiting...")