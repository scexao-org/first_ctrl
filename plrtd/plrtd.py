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

DEBUGGING = True

class FirstPlRtd(StoppableThread):
    """
    Real time display of the reconstructed images.
    """
    def __init__(self, vmin = None, vmax = None, *args, **kwargs):
        super(FirstPlRtd, self).__init__(*args, **kwargs)
        self.Npixel = 100
        self.vmin = vmin
        self.vmax = vmax 
        self.im_io  = shm('firstpl')
        self.width_im = int(self.im_io.get_keywords()['PRD-RNG2'])
        self.height_im = int(self.im_io.get_keywords()['PRD-RNG1'])

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
            file_pixel_map = max(pixel_map_files, key=os.path.getmtime)
        else:
            raise FileNotFoundError("No pixel map files found matching the pattern.")

        self.couplingMap=basic.CouplingMap(file_coupling_map)
        self.pixelMap=basic.PixelMap(file_pixel_map)
        self.detbias = self.pixelMap.header['DETBIAS']

        self.xpos = self.couplingMap.xpos
        self.ypos = self.couplingMap.ypos

        
        self.grid_x, self.grid_y = basic.make_image_grid(self.couplingMap, self.Npixel)

    def plot_detector(self):
        """
        Plot the detector raw image
        """
        self.im = self.im_io.get_data(False).astype(float)
        plt.figure(1234,clear=True)
        plt.imshow(self.im, origin='lower')
        plt.title("Image")
        plt.colorbar()
        plt.pause(0.001)  # Allow the plot to refresh
        plt.show()
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

        # create the image maps
        flux_maps_sum, fluxes = basic.make_image_maps(data_binned.T, self.couplingMap, self.grid_x, self.grid_y, wavelength=False)
        image=flux_maps_sum[0]
        fluxes = fluxes[0,:,0,0]

        popt = basic.fit_gaussian_on_flux(fluxes, self.xpos, self.ypos)
        x_fit=popt[1]
        y_fit=popt[2]
        result = "Maximum at ---> X =%9.3f Y=%9.3f" % (x_fit, y_fit)

        plt.figure(2345,clear=True)
        plt.imshow(image, origin='lower')
        plt.title(result)
        print(result)
        plt.colorbar()
        plt.pause(0.1)  # Allow the plot to refresh

    def setting_milk(self):
        #data = self.plot_detector()
        data = self.im_io.get_data(False).astype(np.float32)
        de,_=basic.preprocess_cutData(data, self.pixelMap)
        # binning data in wavelength according to the coupling map
        data=(de-self.detbias).mean(axis=2)
        Noutput=data.shape[0]
        Nwave=data.shape[1]
        Nbin=self.couplingMap.wavelength_bin

        data=data[:,:(Nwave//Nbin)*Nbin]

        data_binned=data.reshape((Noutput,Nwave//Nbin,Nbin)).sum(axis=-1)
        Nwave=data_binned.shape[1]

        # create the image maps
        flux_maps_sum, fluxes = basic.make_image_maps(data_binned.T, self.couplingMap, self.grid_x, self.grid_y, wavelength=False)
        image=flux_maps_sum[0]
        fluxes = fluxes[0,:,0,0]

        popt = basic.fit_gaussian_on_flux(fluxes, self.xpos, self.ypos)
        x_fit=popt[1]
        y_fit=popt[2]
        result = "Maximum at ---> X =%9.3f Y=%9.3f" % (x_fit, y_fit)
        print(result)

        map_void          = np.zeros((image.shape[0], image.shape[1]), dtype=np.float32)
        shm_var         = shm('first_rtd', map_void, location=-1, shared=1)

        # pymilk does not support setting min/max for scale, so we do it manually by setting some pixels
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
        

# %%

parser = argparse.ArgumentParser(description="Pick min and max color scale values")
parser.add_argument('--vmin', type=int, required=False, help='Min scale value', default=None)
parser.add_argument('--vmax', type=int, required=False, help='Max scale value', default=None)

if __name__ == "__main__":
    args = parser.parse_args()

    # Create an instance of the class
    rtd = FirstPlRtd(vmin = args.vmin, vmax = args.vmax)

    # Load the calibration files
    rtd.load_calibration()

    # Continuously plot images as new data comes in
    rtd.start()