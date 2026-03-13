#coding: utf8
from plscripts.base import Base
import os
from astropy.io import fits
from scipy.interpolate import griddata
from scipy.optimize import curve_fit
import numpy as np
import matplotlib.pyplot as plt
import time
import glob
plt.ion()

class Inspect(Base):
    """
    A class with methods to inspect the data, make plots, etc.
    """
    def __init__(self, *args, **kwargs):
        super(Inspect, self).__init__(*args, **kwargs)
        self.flux_map = None
        self.flux_keywords = None

    @staticmethod
    def gaussian_2d(xy, amplitude, xo, yo, sigma, offset):
        """
        Define a 2d gaussian
        """
        x, y = xy
        xo = float(xo)
        yo = float(yo)
        w = 1/(sigma**2)
        g = offset + amplitude * np.exp(-(w*((x-xo)**2) + w*((y-yo)**2)))
        return g.ravel()
    
    @staticmethod
    def find_most_recent_fits_file(directory):
        """
        get the the latest fits file that was writen     
        """
        # glob files and order them by date 
        filenames = glob.glob(directory + "/*.fits")
        filenames.sort()    
        for filename in filenames[::-1]:
            hd = fits.getheader(filename)
            first_type = hd.get('X_FIRTYP', "UNKNOWN")
            trigger = hd.get('X_FIRTRG', "UNKNOWN")
            if (first_type == "RAW") and (trigger == "EXT"):
                return filename
        return None      

    def opti_flux(self, data_path = None, filename = None, perform_fit = True, plot_it = True) :
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
            if most_recent:
                print(f"Most recent .fits file: {most_recent}")
            else:
                print("No fits files found.")
            filename = most_recent


        # reading the modulation function
        hdu = fits.open(filename)
        self.flux_keywords = hdu[0].header
        objX, objY = hdu[0].header["X_FIROBX"], hdu[0].header["X_FIROBY"] 
        xmod = hdu[1].data['xmod']
        ymod = hdu[1].data['ymod']

        gain = 0.11
        # reading the fluxes
        data = hdu[0].data
        datamean = data.mean(axis=0)
        background = np.median(datamean)
        datamean -= background
        datamean =  gain * datamean

        #extracting relevant pixels
        Ny=data.shape[1]
        threshold_high = np.percentile(datamean.ravel(), (1-19/Ny)*100)
        masque = datamean > threshold_high
        fluxes = (np.mean(data[:, masque], axis=1)-background)*gain

        #extraacting spectra
        threshold_lambda = np.percentile(datamean, (1-2*19/Ny)*100, axis=0)
        flux_lambda = []
        for w,i in enumerate(threshold_lambda):
            masque = datamean[:,w] > i
            flux_lambda+=[datamean[:,w][masque].mean()]
        flux_lambda = np.array(flux_lambda)
        
        # Define the grid for interpolation
        xmin, xmax   = np.min(xmod), np.max(xmod)
        ymin, ymax   = np.min(ymod), np.max(ymod)
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

        flux_padded=np.ones(np.prod(size_new))*np.median(fluxes.ravel())
        flux_padded[np.prod(size_new)-size_old+1:]=fluxes[1:]
        # flux_padded[np.prod(size_new)-size_old:]=fluxes[:]
        flux_padded=flux_padded.reshape(size_new)
        fluxes = flux_padded[-1]


        # Interpolate the fluxes onto the grid
        self.flux_map = griddata((xmod, ymod), fluxes, (grid_x, grid_y), method='nearest')
        if perform_fit:        
            # Prepasre data for fitting
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
            fitted_gaussian = None
            try:
                popt, _ = curve_fit(self.gaussian_2d, (x, y), z, p0=initial_guess)
                x_fit=popt[1]
                y_fit=popt[2]
                fitted_gaussian = self.gaussian_2d((grid_x, grid_y), *popt).reshape(grid_x.shape)
            except:
                x_fit, y_fit = None, None
                print("Failed to perform fit")

            # Plot the contours of the fitted Gaussian on top of the image
            # Plot the interpolated 2D image
            if plot_it:
                fig,axs = plt.subplots(2,1,num="Coupling map",figsize=(8,10),clear=True)
                axs[0].imshow(self.flux_map.T, extent=(xmin, xmax, ymin, ymax), origin="lower", aspect='equal')
                cbar = axs[0].figure.colorbar(axs[0].images[0], ax=axs[0])
                cbar.set_label("Flux")
                axs[0].set_xlabel("X")
                axs[0].set_ylabel("Y")
                if not(fitted_gaussian is None):
                    axs[0].set_title("(Xmod,Ymod) maximum position: (%.3f,%.3f)"%(x_fit,y_fit))
                    axs[0].contour(grid_x, grid_y, fitted_gaussian, levels=10, colors='red', linewidths=0.8)

                axs[1].plot(flux_lambda)
                axs[1].set_title("Saturation at 1000 e-")
                axs[1].set_xlabel("Wavelength channels (pixels)")
                axs[1].set_ylabel("Mean flux (e-/exposure/pixel)")
                fig.tight_layout()

            return x_fit, y_fit
        else:
            return None

