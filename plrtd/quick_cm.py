#! /usr/bin/env python3
# -*- coding: iso-8859-15 -*-
#%%
"""
Created on Sun May 24 22:56:25 2015

@author: slacour
"""

import os
from astropy.io import fits
from glob import glob
from optparse import OptionParser
import numpy as np
import peakutils
from datetime import datetime, timezone
import re
import argparse


from datetime import datetime
from tqdm import tqdm
import runPL_library_io as runlib
import runPL_library_imaging as runlib_i
import runPL_library_basic as basic
import shutil
from scipy.interpolate import griddata
from collections import defaultdict
from scipy import linalg
from scipy.linalg import pinv


def PX_loop_lowering_my_treshold( sampling, peaks_number, raw_image, peaks, output_channels, start = 0.01, stop = 0.1, num = 50, instance=0):
    threshold_array = np.linspace(start, stop, num)
    solution_found=[]
    for i in (range(sampling.shape[0])): #from 0 to the number of samples
        #Sum 10 values of x (wavelenght=columns) of the pic
        sum_image = raw_image[:,sampling[i]-5:sampling[i]+5].sum(axis=1)
        detectedWavePeaks=np.zeros(output_channels)
        found = False
        #Search for the 38 modes expected
        for t in threshold_array:
            detectedWavePeaks_tmp = peakutils.peak.indexes(sum_image,thres=t, min_dist=6)
            if len(detectedWavePeaks_tmp) == peaks_number:
                detectedWavePeaks = detectedWavePeaks_tmp
                found = True
                break
        solution_found+=[found]
        #The values will be saved at the index i of the sample
        peaks[:,i]=detectedWavePeaks

    true_count = sum(solution_found)  # because True == 1, False == 0
    percentage = true_count / len(solution_found)
    if percentage>=0.1 : 
        return solution_found, peaks
    elif instance<5:
        solution_found, peaks = PX_loop_lowering_my_treshold(sampling, peaks_number, raw_image, peaks, output_channels, start = start/2, stop = stop*2, num=num+20, instance=instance+1)

    print("Too many runs, no solution found. Verify your pixelmap")
    print(instance)
    return

def PX_generate_pixelmap(raw_image, pixel_min, pixel_max, output_channels):

    pixel_length=raw_image.shape[1]

    #300 values of pixels between pixelmin and pixelmax
    sampling        = np.linspace(pixel_min+5,pixel_max-5,300,dtype=int)
    peaks           = np.zeros([output_channels, sampling.shape[0]])

    threshold_array=np.linspace(0.01,0.1,50) #originally #np.linspace(0.01,0.1,50) 
    peaks_number=output_channels
    
    solution_found, peaks = PX_loop_lowering_my_treshold( sampling, peaks_number, raw_image, peaks, output_channels)
    traces_loc= np.ones([pixel_length,output_channels],dtype=int)

    x_found=[]
    y_found=[]
    x_none = []
    y_none = []

    #Once we've picked each detected peak, we need to verify that they all belong to the same mode,
    #and that there is no outlier

    for i in range(output_channels):
        # x is a list of all the pixels/wavelength at which 38 peaks were detected
        x = sampling[solution_found]
        # y the corresponding positions of each peak/mode
        y = peaks[i][solution_found]


        # To check for outlier, we make a 1D polyfit between x and y
        for b in range(5): # The process is repeated 5 times to refine the polyfit each time
            poly_coeffs = np.polyfit(x, y, 1)

            # Calculate residuals of the function
            y_fit = np.polyval(poly_coeffs, x)
            residuals = y - y_fit

            # Calculate standard deviation of residuals
            std_residuals = np.std(residuals)
            if std_residuals < 1*(10**(-10)):
                x_with_none = x
                y_with_none = y
                continue

            # Identify inliers (points with residuals within the threshold)
            inliers = np.abs(residuals) < 3 * std_residuals
            

            # Remove outliers
            x = x[inliers]
            y = y[inliers]

            # Replace outliers with None
            x_with_none = [xi if inlier else None for xi, inlier in zip(x, inliers)]
            y_with_none = [yi if inlier else None for yi, inlier in zip(y, inliers)]

        # Fit the polynomial to the cleaned data
        poly_coeffs = np.polyfit(x, y, 1)
        # We stop considering solo pixels and consider the 1D polyfit to trace over all of them.
        traces_loc[:,i] = np.polyval(poly_coeffs, np.arange(pixel_length))+0.5
        # x is a list of all the pixels/wavelength at which 38 peaks were detected
        # y the corresponding positions of each peak/mode
        x_found += [x]
        y_found += [y]
        x_none +=[x_with_none]
        y_none +=[y_with_none]

    return traces_loc


def PX_save_fits(traces_loc, header,pixel_min, pixel_max,pixel_wide,output_channels, folder):
    # Save fits file with traces_loc inside
    hdu = fits.PrimaryHDU(traces_loc)
    header['X_FIRTYP'] = 'PIXELMAP'
    # Add date and time to the header
    current_time = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    header['DATE-PRO'] = current_time
    if 'DATE' not in header:
        header['DATE'] = current_time

    # Add input parameters to the header
    header['PIX_MIN'] = pixel_min
    header['PIX_MAX'] = pixel_max
    header['PIX_WIDE'] = pixel_wide
    header['OUT_CHAN'] = output_channels
    header['PM_CHECK'] = np.random.randint(0, 2**32, dtype=np.uint32)

    # Définir le chemin complet du sous-dossier "output/wave"
    if folder.endswith("*fits"):
        folder = folder[:-5]
    output_dir = folder#os.path.join(folder,"pixelmaps")

    if os.path.exists(output_dir) and os.path.isdir(output_dir):
        shutil.rmtree(output_dir)

    # Créer les dossiers "output" et "pixel" s'ils n'existent pas déjà
    os.makedirs(output_dir, exist_ok=True)

    hdu.header.extend(header, strip=True)
    hdul = fits.HDUList([hdu])
    filename_out = os.path.join(output_dir, runlib.create_output_filename(header))

    hdul.writeto(filename_out, overwrite=True)
    return filename_out
  

def run_PR_preprocess(filelist_pixelmap,files_by_dir, save_to):
    """
    Preprocesses the data files using the provided pixel map and organizes them by directory.
    This function handles the preprocessing of raw data files, applying the pixel map to extract
    relevant pixel data, and saves the processed data along with diagnostic figures.
    Args:
        filelist_pixelmap (list): A list containing the pixel map file(s).
        files_by_dir (dict): A dictionary where keys are directory paths and values are lists of
                             raw data files in those directories.
    """

    pixelMap=basic.PixelMap(filelist_pixelmap[-1])
    pixel_min = pixelMap.pixel_min
    pixel_max = pixelMap.pixel_max
    pixel_wide = pixelMap.pixel_wide
    output_channels = pixelMap.output_channels
    traces_loc = pixelMap.traces_loc


    # Process each directory separately 
    for dir_path, files in files_by_dir.items():
        raw_image = None
        center_image = None
        files_out = []
        
        for file in tqdm(files[:], desc=f"Pre-processing of files in {dir_path}"):
            data = fits.getdata(file)
            header = fits.getheader(file)
            object = header.get('OBJECT', "NONAME")
            date = header.get('DATE', 'NODATE')
            type = header.get('DATA-TYP',None)
            date_preproc = datetime.fromtimestamp(os.path.getctime(file)).strftime('%Y-%m-%dT%H:%M:%S')

            header['GAIN'] = 1

            if date == 'NODATE':
                header['DATE'] = date_preproc
                date = date_preproc

            if len(data.shape) == 2:
                data = data[None]

            if raw_image is None:
                raw_image = np.zeros_like(data.sum(axis=0), dtype=np.double)

            raw_image += data.sum(axis=0)
            
            data_cut_pixels, data_dark_pixels = basic.preprocess_cutData(data, pixelMap, True)

            perc_background=np.percentile(data_dark_pixels.ravel(),[50-34.1,50,50+34.1],axis=0)
            data_mean= np.percentile(np.mean(data_cut_pixels,axis=(1,2)),90,axis=0)
            data_cut = np.sum(data_cut_pixels,axis=-1,dtype='uint32')
            flux_mean = np.mean(data_cut,axis=(0,1,2))-perc_background[1]*(pixel_wide*2+1)

            if center_image is None:
                center_image = data_mean[:,None]
            else:
                center_image = np.concatenate((center_image,data_mean[:,None]),axis=1)

            centered=data_mean.argmax()-pixel_wide

            comp_hdu = fits.PrimaryHDU(data_cut, header=header)

            # Update the header with the values read in the headers above
            comp_hdu.header['X_FIRTYP'] = "PREPROC"
            comp_hdu.header['ORG_NAME'] = os.path.basename(file)
            comp_hdu.header['PIX_MIN'] = pixel_min
            comp_hdu.header['PIX_MAX'] = pixel_max
            comp_hdu.header['PIX_WIDE'] = pixel_wide
            comp_hdu.header['OUT_CHAN'] = output_channels
            comp_hdu.header['PIXELS'] = filelist_pixelmap[-1]
            comp_hdu.header['QC_SHIFT'] = centered
            comp_hdu.header['QC_BACK'] = perc_background[1]
            comp_hdu.header['QC_BACKR'] = (perc_background[2]-perc_background[0])/2*np.sqrt(2)
            comp_hdu.header['QC_FLUX'] = flux_mean

            # Add the MODULATION extension from the original file to the new FITS file
            if 'MODULATION' in fits.open(file):
                modulation_hdu = fits.open(file)['MODULATION']
                comp_hdu.header['MOD_LEN'] = modulation_hdu.header['NAXIS2']
                comp_hdu = fits.HDUList([comp_hdu, modulation_hdu])

            # create a directory named preproc if it does not exist
            preproc_dir_path = dir_path#os.path.join(dir_path, "preproc")
            if not os.path.exists(preproc_dir_path):
                os.makedirs(preproc_dir_path)
            
            output_filename = runlib.create_output_filename(header)
            files_out += [output_filename]
            comp_hdu.writeto(os.path.join(save_to, output_filename), overwrite=True, output_verify='fix', checksum=True)
            print("Saved preproc to ", save_to)
            

        # copy filelist_pixelmap[-1] to the preproc directory
        #shutil.copy(filelist_pixelmap[-1], preproc_dir_path)
    return preproc_dir_path

def CM_get_projection_matrice(datacube,flux_goodData,Nsingular):
    """
    Computes the projection matrix and singular values using Singular Value Decomposition (SVD).
    datacube is a flux_2_data matrix
    
        flux_2_data == projdata_2_data @ s @ flux_2_data
        data_2_projdata is the transpose of projdata_2_data

    Returns the projection matrix data_2_projdata and singular values.
    """

    Nwave=datacube.shape[0] #100
    Noutput=datacube.shape[1] #38
    Ncube=datacube.shape[2] #10
    Nmod=datacube.shape[3] #625
    datacube=datacube.reshape((Nwave*Noutput,Ncube,Nmod)) #reshape to (3800, 10, 625)

    pos_2_data = datacube[:,flux_goodData] #(3800, 3017) datacube is (3800, 10, 625), flux_good is (10, 625)

    U,s,Vh=linalg.svd(pos_2_data,full_matrices=False)

    #pos_2_singular = Vh[:Nsingular]*s[:Nsingular,None]
    singular_2_data = U[:,:Nsingular] #(3800, 57)
    pos_2_singular = singular_2_data.T @ datacube.reshape((Nwave*Noutput,Ncube*Nmod)) #(57, 6250)

    singular_values = s #(3017,)
    pos_2_singular = pos_2_singular.reshape((Nsingular,Ncube,Nmod)) #reshape to (57, 10, 625)
    singular_2_data = singular_2_data.reshape((Nwave,Noutput,Nsingular))

    return pos_2_singular,singular_values,singular_2_data

def CM_get_fluxtiptilt_matrices(singular_2_data, pos_2_singular_mean, triangles):
    """
    Computes the flux and tip-tilt matrix from the projected data.

    This function calculates matrices for converting between projected data and flux/tip-tilt values.

    Returns:
        tuple: A tuple containing:
            - flux_2_data (numpy.ndarray): Matrix to convert flux to data.
            - data_2_flux (numpy.ndarray): Matrix to convert data to flux.
            - fluxtiptilt_2_data (numpy.ndarray): Matrix to convert flux and tip-tilt to data.
            - data_2_fluxtiptilt (numpy.ndarray): Matrix to convert data to flux and tip-tilt.
    """

    
    Nsingular=pos_2_singular_mean.shape[0]
    Nmod=pos_2_singular_mean.shape[1]
    Nwave=singular_2_data.shape[0]
    Noutput=singular_2_data.shape[1]
    # Ntriangles=len(triangles)

    masque_positions=~np.isnan(pos_2_singular_mean[0])
    masque_triangles=(masque_positions[triangles].sum(axis=1) ==3)
    Npositions=np.sum(masque_positions)
    Ntriangles=np.sum(masque_triangles)

    flux_2_data_tmp = singular_2_data.reshape((Nwave*Noutput,Nsingular)) @ pos_2_singular_mean
    flux_2_data_tmp = flux_2_data_tmp.reshape((Nwave,Noutput,Nmod))
    flux_2_data = flux_2_data_tmp[:,:,masque_positions]
    flux_norm_wave = flux_2_data.sum(axis=(1,2), keepdims=True)
    flux_2_data /= flux_norm_wave

    data_2_flux = np.zeros((Nwave,Npositions,Noutput))
    print("Inverting flux_2_data to data_2_flux for each wavelength:")
    for w in tqdm(range(Nwave)):
        data_2_flux[w]=pinv(flux_2_data[w])

    fluxtiptilt_2_data = flux_2_data_tmp[:,:,triangles[masque_triangles]].transpose((2,0,1,3)).copy()
    data_2_fluxtiptilt = np.zeros((Ntriangles,Nwave,3,Noutput))
    print("Inverting fluxtiptilt_2_data to data_2_fluxtiptilt:")
    for w in tqdm(range(Nwave)):
        for t in range(Ntriangles):
            data_2_fluxtiptilt[t,w]=pinv(fluxtiptilt_2_data[t,w])


    return flux_2_data,data_2_flux,fluxtiptilt_2_data,data_2_fluxtiptilt,masque_positions,masque_triangles

def filter_filelist(filelist,modID):
    """
    Filters the input file list to separate coupling map files and dark files based on FITS keywords.
    Raises an error if no valid files are found.
    Returns a dictionary mapping coupling map files to their closest dark files.
    """

    # Use the function to clean the filelist
    if modID == 0:
        fits_keywords = {'X_FIRTYP': ['PREPROC'],
                        'DATA-TYP': ['OBJECT','TEST']}
    else:
        fits_keywords = {'X_FIRTYP': ['PREPROC'],
                        'DATA-TYP': ['OBJECT','TEST'],
                        'X_FIRMID': [modID],
                        }
    filelist_cmap = runlib.clean_filelist(fits_keywords, filelist)
    print("runPL cmap filelist : ", filelist_cmap)

    fits_keywords = {'X_FIRTYP': ['PREPROC'],
                    'DATA-TYP': ['DARK']}
    filelist_dark = runlib.clean_filelist(fits_keywords, filelist)
    print("runPL dark filelist : ", filelist_dark)


    # raise an error if filelist_cleaned is empty
    if len(filelist_cmap) == 0:
        raise FileNotFoundError("No good file to run cmap")
    # raise an error if filelist_cleaned is empty
    if len(filelist_dark) == 0:
        print("WARNING: No good dark to substract to cmap files")

    # Check if all files have the same value for header['PM_CHECK']
    pm_check_values = set()
    combined_filelist = []
    combined_filelist.extend(filelist_dark)
    combined_filelist.extend(filelist_cmap)
    for file in combined_filelist:
        header = fits.getheader(file)
        pm_check_values.add(header.get('PM_CHECK', 0))
        
    if len(pm_check_values) > 1:
        print("WARNING: The 'PM_CHECK' values (ie, the pixel map used to preprocess the files) \n are not consistent across all files!")
        print(f"Found values: {pm_check_values}")

    # for each file in filelist_cmap find the closest dark file in filelist_dark with, by priority, first the directory in which the file is, and then by the date in the "DATE" fits keyword, and second, the directory in which the file is

    files_with_dark = {cmap: runlib.find_closest_dark(cmap, filelist_dark) for cmap in filelist_cmap}

    return files_with_dark


def run_PX_create_pixel_map_from_a_list_of_fits_files(filelist, folder):
    
    #TODO : ADD A FUNCTION THAT PICKS UP THE LAST N FILES
    #TODO : ADD A FUNCTION THAT VERIFY ALL FILES ARE COMPATIBLE

    header = fits.getheader(filelist[-1])
    raw_image = np.zeros((header['NAXIS2'], header['NAXIS1']), dtype=np.double)
    header = fits.getheader(filelist[-1])
    for filename in tqdm(filelist, desc="Co-adding files"):
        raw_image += fits.getdata(filename).sum(axis=0)

    pixel_min = 100
    pixel_max = 1600
    pixel_wide = 2
    output_channels = 38

    traces_loc = PX_generate_pixelmap(raw_image, pixel_min, pixel_max, output_channels)
    pixelmap_path = PX_save_fits(traces_loc, header,pixel_min, pixel_max,pixel_wide,output_channels, folder)

    return pixelmap_path


def run_CM_create_coupling_maps(files_with_dark, 
                                wavelength_smooth = 20,
                                wavelength_bin = 15,
                                modID = 0,
                                Nsingular=19*3, 
                                output_dir='.'):


    #Input preproc
    #clean and sum all data
    datalist=runlib_i.extract_datacube(files_with_dark,wavelength_smooth,Nbin=wavelength_bin)
    #datacube (625, 38, 100)
    #select only the data in datalist which has the same modulation pattern
    if modID == 0:
        modID = datalist[0].modID
        datalist = [d for d in datalist if d.modID == modID]

    modScale = datalist[0].modScale
    datalist = [d for d in datalist if d.modScale == modScale and d.modID== modID]

    if len(datalist) == 0:
        print("No data with the selected modulation parameters",modID,modScale)
        return

    datacube=np.concatenate([d.data for d in datalist])
    datacube=datacube.transpose((3,2,0,1))

    xmod=datalist[0].xmod
    ymod=datalist[0].ymod
    triangles = datalist[0].get_triangle()

    # select data only above a threshold based on flux
    flux_threshold=np.percentile(datacube.mean(axis=(0,1)),80)/5
    flux_goodData=datacube.mean(axis=(0,1)) > flux_threshold
    # plt.imshow(flux_goodData)
    if np.sum(flux_goodData)<57:
        #too little good data, we need to lower the bar
        flux_goodData=datacube.mean(axis=(0,1)) > flux_threshold/2
        print("Not enough good data, lowering the threshold to ",flux_threshold/2)

    # get the Nsingulat highest singular values and the projection vectors into that space 
    #VSD
    #datacube : (100, 38, 10, 625)
    #flux_gooddata : (10, 625)
    #Nsingular : 57
    pos_2_singular,singular_values,singular_2_data=CM_get_projection_matrice(datacube,flux_goodData,Nsingular)

    # average all the datacubes, do not includes the bad frames
    pos_2_singular[:,~flux_goodData]=np.nan
    pos_2_singular_mean = np.nanmean(pos_2_singular,axis=1)

    # compute the matrices to go from the projected data to the flux and tip tilt (and inverse)
    flux_2_data,data_2_flux,fluxtiptilt_2_data,data_2_fluxtiptilt,masque_positions,masque_triangles = CM_get_fluxtiptilt_matrices(singular_2_data, pos_2_singular_mean, triangles)

    #use flux tip tilt matrice to check if the observations are point like
    # To do so, fits the vector model and check if the chi2 decrease resonably
    chi2_min,chi2_max,arg_triangle=runlib_i.get_chi2_maps(datacube,fluxtiptilt_2_data,data_2_fluxtiptilt)
    chi2_delta=chi2_min/chi2_max
    percents=np.nanpercentile(chi2_delta[flux_goodData],[16,50,84])
    chi2_threshold=percents[1]+(percents[2]-percents[0])*3/2
    chi2_goodData = (chi2_delta < chi2_threshold)&flux_goodData

    #redo most of the work above but with flagged datasets
    pos_2_singular,singular_values,singular_2_data=CM_get_projection_matrice(datacube,chi2_goodData,Nsingular)
    pos_2_singular[:,~chi2_goodData]=np.nan
    pos_2_singular_mean = np.nanmean(pos_2_singular,axis=1)
    flux_2_data,data_2_flux,fluxtiptilt_2_data,data_2_fluxtiptilt,masque_positions,masque_triangles = CM_get_fluxtiptilt_matrices(singular_2_data, pos_2_singular_mean, triangles)
    
    # Flux maps for inspection
    fluxmaps = np.mean(datacube, axis=(0,1))
    # Define the grid for interpolation
    grid_x, grid_y = np.mgrid[np.min(xmod):np.max(xmod):500j, np.min(ymod):np.max(ymod):500j]  # 500x500 grid
    # Interpolate the fluxes onto the grid
    fluxmap_interp= np.zeros((len(fluxmaps), 500, 500))
    for i,fm in enumerate(fluxmaps):
        fluxmap_interp[i] = griddata((xmod, ymod), fm, (grid_x, grid_y), method='cubic').T
    
    # Save arrays into a FITS file

    # Create a primary HDU with no data, just the header
    hdu_primary = fits.PrimaryHDU()

    # Create HDUs for each array
    hdu_1 = fits.ImageHDU(data=flux_2_data, name='F2DATA')
    hdu_2 = fits.ImageHDU(data=data_2_flux, name='DATA2F')
    hdu_3 = fits.ImageHDU(data=fluxtiptilt_2_data, name='FTT2DATA')
    hdu_4 = fits.ImageHDU(data=data_2_fluxtiptilt, name='DATA2FTT')
    hdu_fluxmap = fits.ImageHDU(data=fluxmap_interp, name='FLUXMAP')

    # Create columns for xmod and ymod using fits.Column
    x_pos = xmod[masque_positions]
    y_pos = ymod[masque_positions]
    x_triangles = xmod[triangles[masque_triangles]]
    y_triangles = ymod[triangles[masque_triangles]]

    # shifting all positions around the maximum of flux found from gaussian fitting
    fluxes = datacube.mean(axis=(0,1,2))
    popt = basic.fit_gaussian_on_flux(fluxes, xmod, ymod)
    x_fit=popt[1]
    y_fit=popt[2]
    x_fit = x_pos[((x_fit-x_pos)**2).argmin()] 
    y_fit = y_pos[((y_fit-y_pos)**2).argmin()] 

    x_triangles -= x_fit
    y_triangles -= y_fit
    x_pos -= x_fit
    y_pos -= y_fit

    col_xmod = fits.Column(name='X_POS', format='E', array=x_pos, unit='mas')
    col_ymod = fits.Column(name='Y_POS', format='E', array=y_pos, unit='mas')

    col_xtriangles = fits.Column(name='X_TRI', format='3E', array=x_triangles, unit='mas')
    col_ytriangles = fits.Column(name='Y_TRI', format='3E', array=y_triangles, unit='mas')

    # Create a table HDU for xmod and ymod
    hdu_table_mod = fits.BinTableHDU.from_columns([col_xmod, col_ymod], name='POSITIONS')
    hdu_table_triangle = fits.BinTableHDU.from_columns([col_xtriangles, col_ytriangles], name='TRIANGLES')

    modulation_hdu = fits.open(datalist[-1].filename)['MODULATION']

    header = datalist[-1].header
    # Définir le chemin complet du sous-dossier "output/couplingmaps"
    folder = datalist[-1].dirname
    #output_dir = folder #os.path.join(folder,"couplingmaps")

    header['X_FIRTYP'] = 'COUPLINGMAP'
    # Add date and time to the header
    current_time = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    header['DATE-PRO'] = current_time
    if 'DATE' not in header:
        header['DATE'] = current_time

    # Add input parameters to the header
    header['WLSMOOTH'] = wavelength_smooth  # Add wavelength smoothing factor
    header['WL_BIN'] = wavelength_bin
    header['NSINGUL'] = Nsingular  # Add number of singular values
    header['FLUXTHR'] = flux_threshold  # Add flux threshold
    header['CHI2THR'] = chi2_threshold  # Add chi2 threshold

    # Créer les dossiers "output" et "pixel" s'ils n'existent pas déjà
    os.makedirs(output_dir, exist_ok=True)

    hdu_primary.header.extend(header, strip=True)

    # Combine all HDUs into an HDUList
    hdul = fits.HDUList([hdu_primary, hdu_1, hdu_2, hdu_3, hdu_4,
                         hdu_table_mod,hdu_table_triangle,modulation_hdu,
                         hdu_fluxmap])

    output_filename = os.path.join(output_dir, runlib.create_output_filename(header))

    # Write to a FITS file
    print(f"Saving data to {output_filename}")
    hdul.writeto(output_filename, overwrite=True)


def get_from_header(file, keyword):
    header = fits.getheader(file, ext=0)
    return header[keyword]

def verify_files_are_compatible(filelist):
    ref_header = fits.getheader(filelist[0], ext=0)
    must_verify = ["NAXIS3", "DATA-TYP", "X_FIRMID", "X_FIRMCS"]
    for file in filelist:
        this_header = fits.getheader(file, ext=0)
        for keyword in must_verify:
            same_header = this_header[keyword]==ref_header[keyword]
            if not same_header:
                raise ValueError("The files in the input have a differnt value of ", keyword)
                return False
    return True

def create_dated_folder(base_path="/mnt/datazpool/PL/all_coupling_maps/"):
    """Creates a folder with the current date and time in YYYY-MM-DD_HH-MM-SS format."""
    now = datetime.now()
    folder_name = now.strftime("%Y-%m-%d_%H-%M-%S")
    folder_path = os.path.join(base_path, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    return folder_path

def get_latest_dated_folder(base_path="/mnt/datazpool/PL/all_coupling_maps"):
    """Returns the most recent folder with a date-time name in the format YYYY-MM-DD_HH-MM-SS."""
    pattern = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$")
    folders = [
        f for f in os.listdir(base_path)
        if os.path.isdir(os.path.join(base_path, f)) and pattern.match(f)
    ]
    if not folders:
        return None
    latest_folder = max(folders, key=lambda f: datetime.strptime(f, "%Y-%m-%d_%H-%M-%S"))
    return os.path.join(base_path, latest_folder)

def replace_directory_contents(target_dir, source_dir):
    # Ensure both paths are valid directories
    if not os.path.isdir(target_dir):
        raise ValueError(f"Target directory '{target_dir}' does not exist or is not a directory.")
    if not os.path.isdir(source_dir):
        raise ValueError(f"Source directory '{source_dir}' does not exist or is not a directory.")
    
    # Remove all contents of the target directory
    for item in os.listdir(target_dir):
        item_path = os.path.join(target_dir, item)
        if os.path.isdir(item_path):
            shutil.rmtree(item_path)
        else:
            os.remove(item_path)

    # Copy contents of source directory into target directory
    for item in os.listdir(source_dir):
        src_path = os.path.join(source_dir, item)
        dst_path = os.path.join(target_dir, item)
        if os.path.isdir(src_path):
            shutil.copytree(src_path, dst_path)
        else:
            shutil.copy2(src_path, dst_path)

def new_coupling_map(filelist2):

    #test = "firstpl_05:31:04.859572198.fits"
    #source_path = "/mnt/datazpool/PL/20250510/firstpl/"



    most_recent_folder = create_dated_folder()

    pixel_map_path = run_PX_create_pixel_map_from_a_list_of_fits_files(filelist2, most_recent_folder)

    files_by_dir = defaultdict(list)
    for file in filelist2:
        dir_path = os.path.dirname(os.path.realpath(file))
        files_by_dir[dir_path].append(file)
    
    preproc_dir_path = run_PR_preprocess([pixel_map_path],files_by_dir, most_recent_folder)

    files_by_dir = defaultdict(list)
    for file in preproc_dir_path:
        dir_path = os.path.dirname(os.path.realpath(file))
        files_by_dir[dir_path].append(os.path.basename(file))


    filelist = runlib.get_filelist(most_recent_folder)
    filelist = runlib.clean_filelist({'X_FIRTYP':"PREPROC"}, filelist)

    modID = get_from_header(filelist[0], "X_FIRMID")
    files_with_dark = filter_filelist(filelist, modID)
    

    run_CM_create_coupling_maps(files_with_dark, 
                                wavelength_smooth = 20,
                                wavelength_bin = 15,
                                modID = 0,
                                Nsingular=19*3,
                                output_dir=most_recent_folder)

    # I replace the final directory every time so as to keep the original coupling map in memory in their own folder
    replace_directory_contents("/mnt/datazpool/PL/calibration_files", get_latest_dated_folder())
    print("Calibrations files updated.")



parser = argparse.ArgumentParser(description="Either go by latest or specify which files to use")
parser.add_argument('--n-latest', type=int, required=False, help='Number of latest saved files to use', default=None)
parser.add_argument('--modid', type=int, required=False, help='ModID to filter on', default=None)
parser.add_argument('--modscale', type=int, required=False, help='ModScale to filter on', default=None)
parser.add_argument('--filelist', '--nargs', action='append', nargs='+', required=False, help='List of all the files to use', default=None)

if __name__ == "__main__":
    args = parser.parse_args()
    n_latest = args.n_latest
    filelist = args.filelist[0]
    modid = args.modid
    modscale = args.modscale

    if n_latest is None and filelist is None:
        raise ValueError("Add either a list of files or the number of recent files to consider")


    tnow = datetime.datetime.now(datetime.timezone.utc)
    current_path = format(today = tnow.strftime("%Y%m%d"))

    source_path = "/mnt/datazpool/PL/" + current_path + "/firstpl/"

    if filelist is None:

        filelist1 = [source_path + f for f in os.listdir(source_path)
                if os.path.isfile(os.path.join(source_path, f)) and f.lower().endswith('.fits')]

        filelist2 = runlib.get_n_latest_date_fits(filelist1, n_latest)
    
    else : 
        filelist2=[source_path + f for f in filelist]

    
    verify_files_are_compatible(filelist2, modid, modscale)

    new_coupling_map(filelist2)

    
