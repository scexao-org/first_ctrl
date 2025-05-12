#coding: utf8
from plscripts.base import Base

import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import tqdm.auto as tqdm
from astropy.io import fits
from scxconf.pyrokeys import FIRST
from swmain.network.pyroclient import connect
from pyMilk.interfacing.fps import FPS

IS_READOUT_MODE_IN_YET = True
_DEFAULT_DELAY = 3  # s 
_ADDED_DELAY = 20 #s
BASE_COMMAND = ("milk-streamFITSlog", "-cset", "q_asl")
DEBUGGING = False
CUBES_FOR_LOW_INTEGRATION_TIME_ARE_STILL_BROKEN = True



class Eon(Base):
    def __init__(self, *args, **kwargs):
        self.source_files_path = None#self._default_FIRST_raw_folder()
        self._filenames = None#self._list_of_files_containing_the_correct_keywords()
        self.parameters_used = None#[self._relevant_headers(f) for f in self._filenames]
        self.status = {}
        self._camera = connect(FIRST)
        self._logger = FPS('streamFITSlog-firstpl')
        super(Eon, self).__init__(*args, **kwargs)

    def _list_of_files_containing_the_correct_keywords(self):
         all_files = list(Path(self.source_files_path).rglob("*.fits"))
         files_that_do_have_them_headers = []
         files_that_dont = []
 
         for file in all_files:
             try:
                 with fits.open(file) as hdul:
                     header = hdul[0].header
                     with fits.open(file) as hdul:
                         if all(key in header for key in ['EXPTIME', 'X_FIRDMD', 'DATA-TYP']):
                             files_that_do_have_them_headers.append(file)
                         else:
 
                             files_that_dont.append(file)
             except Exception as e:
                 files_that_dont.append(file)
 
         print(f"{len(files_that_do_have_them_headers)} files will be taken into account, {len(files_that_dont)} don't match the expected headers and will be ignored.")
         return files_that_do_have_them_headers

    
    def _default_FIRST_raw_folder(self):
        """ Explicit """
        base = "/mnt/datazpool/PL/"
        today = datetime.now(timezone.utc)
        use = base + f"{today:%Y%m%d}"+"/"
        test = base + "20250502"+"/"
        if DEBUGGING : use = test
        return use
    
    def _path_to_save_to(self, DATATYP):
        """ Explicit """
        base = "/mnt/datazpool/PL/"
        today = datetime.now(timezone.utc)
        use = base + f"{today:%Y%m%d}/" + DATATYP +"/"
        os.makedirs(use, exist_ok=True)
        return use
    
    def _relevant_headers(self, filename):
        """
        List of the headers we want to set as parameters and their values, extracted from our files
        """
        hdr = fits.getheader(filename)
        dark_keys = (
            #"PRD-MIN1", #Crop origin
            #"PRD-MIN2",
            #"PRD-RNG1", #Crop width
            #"PRD-RNG2",
            "EXPTIME",
            "X_FIRDMD",
            "DATA-TYP"
        )
        return {k: hdr[k] for k in dark_keys}
    
    def _unique_headers_combinations(self, folder=None):
        """
        Collect all the headers from all the saved files and create unique combinations of parameters sets to reproduce
        """

        

        if folder is None:
            self.source_files_path =self._default_FIRST_raw_folder()
            self._filenames = self._list_of_files_containing_the_correct_keywords()
            self.parameters_used = [self._relevant_headers(f) for f in self._filenames]
            folder = self.source_files_path
        filenames = list(Path(folder).rglob("*.fits"))
        n_input = len(filenames)

        if n_input == 0:
            msg = f"No FITS files found in {folder}"
            raise ValueError(msg)
        
        # get a table from all filenames
        header_rows = self.parameters_used
        # get unique combinations of non dark fits
        header_table = pd.DataFrame(header_rows)
        header_table = header_table[~header_table["DATA-TYP"].isin(["DARK", "BIAS", "FLAT"])]
        header_table = header_table.drop(columns=['DATA-TYP'])

        header_table.drop_duplicates(keep="first", inplace=True)

        if IS_READOUT_MODE_IN_YET :header_table.sort_values("X_FIRDMD", inplace=True)

        self.status["ALL_SETS_TO_SAVE"] = header_table
        return header_table
    

    def _table_for_flat(self, table):
        """
        Flats requires a specific list of exposure time and not the ones taken during the night. 
        Here, we add these values to the current set of parameters to create a new unique set.
        """
        table = table.drop(columns=['EXPTIME'])  #Drop the 'EXP-TIME' column
        table = table.drop_duplicates() #Drop duplicate rows across all remaining columns
        exptimes = [0.05, 0.1, 0.25, 0.375, 0.4, 0.5, 0.75, 0.8, 0.875, 1.0,
                1.25, 1.375, 1.5, 1.625, 1.75, 1.875, 2.0, 2.25, 2.375, 2.5,
                2.625, 2.75, 2.875, 3.0, 3.125, 3.25, 3.375, 3.5, 3.625, 3.75,
                3.875, 4.0, 5.0, 6.0, 6.5, 7.0, 8.0, 9.0, 10.0]

        # new DataFrame with all combinations (cartesian product)
        table_w_new_expt = table.merge(pd.DataFrame({'EXPTIME': exptimes}), how='cross')

        self.status["ALL_SETS_TO_SAVE"] = table_w_new_expt
        return table_w_new_expt
    
    def _estimate_total_time(self, table, num_cubes, num_frames):
        #Preds aiction of the total time to take
        
        if num_frames is None : num_frames

        all_time_taken  = (table["EXPTIME"] * num_cubes * num_frames +1).sum()
        minutes = int(all_time_taken // 60)
        seconds = int(all_time_taken % 60)
        print(f"Now saving, it will take: {minutes}m {seconds}s for {len(table)} different set of parameters. {num_cubes} cubes of {num_frames} frames will be saved for each set.")
        return True
    
    def _verify_files_are_done(self, folder, contents_before, expected_number_of_files, expected_time_taken):
        """ 
        Verify in a folder is all the expected cubes have been created. Timeout after expected_time_taken in seconds.
        """

        contents_after = {f for f in os.listdir(folder) if f.endswith(".fits")} 
        new_files = sorted(contents_after - contents_before)
        start_time = time.time()
        end_time=time.time()

        while not len(new_files)==expected_number_of_files and not (end_time-start_time)>expected_time_taken:
            contents_after = {f for f in os.listdir(folder) if f.endswith(".fits")} #Files present now
            new_files = sorted(contents_after - contents_before) #Difference with the ones we started with
            end_time=time.time() #Updating how much time has passed

            #Use either one to see progress
            #print(f"Waiting... {end_time-start_time:.1f} seconds elapsed", end="\r", flush=True)
            #print(f"We have... {len(new_files)} new files so far", end="\r", flush=True)
        
        if len(new_files)==expected_number_of_files:
            return True
        
        elif CUBES_FOR_LOW_INTEGRATION_TIME_ARE_STILL_BROKEN==True: 
            print(f"Timeout, {len(new_files)} created instead of {expected_number_of_files}")
            return True

        else : 
            print(f"Timeout, {len(new_files)} created instead of {expected_number_of_files}")
            return False
        
    
    def _preping_bench_for_save(self, set:dict, num_cubes, num_frames, verbose = False):
        self.status["NOW_SAVING"] = set

        if verbose : print("Now taking for the following parameters : \n",set)
            
        if num_frames is None :
            if set["EXPTIME"]>0.5 : num_frames =250 #1000 until 0.5s, 250 until 1s, 100 for anything above
            if set["EXPTIME"]>1 : num_frames =100 
            else : num_frames = 1000

        if IS_READOUT_MODE_IN_YET and str(set["X_FIRDMD"]) != str(self._camera.get_readout_mode):
            self._camera.set_readout_mode(set["X_FIRDMD"])

        self._camera.set_tint(set["EXPTIME"])
        self._logger.set_param("cubesize", num_frames)
        self._logger.set_param("maxfilecnt", num_cubes)

        time_to_take = set["EXPTIME"]*num_cubes*num_frames*_DEFAULT_DELAY +_ADDED_DELAY
        return time_to_take
    
    def save_single_flat(self, row, num_frames=None, num_cubes=1, verbose=False):

        time_to_take = self._preping_bench_for_save(row, num_cubes, num_frames, verbose=verbose)
        self._camera.set_keyword("DATA-TYP", "FLAT")
        save_here = Path(self._path_to_save_to("FLAT"))
        self._save_with_fits_logger(save_here, time_to_take, num_cubes, verbose=verbose)
        return

    def save_single_dark(self, row, num_frames=None, num_cubes=1, verbose=False):

        time_to_take = self._preping_bench_for_save(row, num_cubes, num_frames, verbose=verbose)
        self._camera.set_keyword("DATA-TYP", "DARK")
        save_here = Path(self._path_to_save_to("DARK"))
        os.system('vis_block in') #to uncomment when actually running
        self._save_with_fits_logger(save_here, time_to_take, num_cubes, verbose=verbose)
        os.system('vis_block out')
        return
    

    

    def save_flats(self, num_frames=None, num_cubes=1, verbose=False):#(cam_num: Literal[1, 2], num_frames=1000, folder=None)
        """
        Transmit the sets of parameters needed to the camera in a list of sets, and launch captures with the fits log for every set.
        """


        table = self._unique_headers_combinations()
        table = self._table_for_flat(table)

        time.sleep(1)

        dirname_before = self.source_files_path #logger.get_param('dirname') # should be the last directory we've been saving in
        dirname_after =  self._path_to_save_to #dirname_before #"/home/first/jsarrazin/test_dark/"

        # Set up first readout mode
        #print(table)
        if IS_READOUT_MODE_IN_YET:
            self._camera.set_readout_mode(table["X_FIRDMD"][0])

        # Prepping for the loop
        #self._estimate_total_time(self, table, num_cubes, num_frames)
        iterator = table.iterrows()

        if not verbose: #No verbose displays a single progress bar for the saving of all. verbose will have a progress bar for every single set.
            contents_before = {f for f in os.listdir(self._path_to_save_to("FLAT")) if f.endswith(".fits")}
            iterator = tqdm.tqdm(iterator, total=len(table), desc="Processing rows")


        for index, row in iterator:
            self.save_single_flat(row, num_frames=num_frames, num_cubes=num_cubes, verbose=verbose)

        self._logger.set_param('dirname', dirname_before) # set param back
        
        if not verbose: 
            contents_after = {f for f in os.listdir(self._path_to_save_to("FLAT")) if f.endswith(".fits")}
            new_files = sorted(contents_after - contents_before)
            print(f"{len(new_files)} new files created.")
        return
    

    def save_darks(self, num_frames=None, num_cubes=1, verbose=False):#(cam_num: Literal[1, 2], num_frames=1000, folder=None)
        """
        Transmit the sets of parameters needed to the camera in a list of sets, and launch captures with the fits log for every set.
        """

        table = self._unique_headers_combinations()

        time.sleep(1)

        dirname_before = self.source_files_path #logger.get_param('dirname') # should be the last directory we've been saving in
        dirname_after =  self._path_to_save_to #dirname_before #"/home/first/jsarrazin/test_dark/"

        # Set up first readout mode
        if IS_READOUT_MODE_IN_YET:
            self._camera.set_readout_mode(table["X_FIRDMD"][0])

        # Prepping for the loop
        #self._estimate_total_time(self, table, num_cubes, num_frames)
        iterator = table.iterrows()

        if not verbose: #No verbose displays a single progress bar for the saving of all. verbose will have a progress bar for every single set.
            contents_before = {f for f in os.listdir(os.path.join(self._path_to_save_to("DARK"))) if f.endswith(".fits")}
            iterator = tqdm.tqdm(iterator, total=len(table), desc="Processing rows")

        for index, row in iterator:
            self.save_single_dark(row, num_frames=num_frames, num_cubes=num_cubes, verbose=verbose)

        self._logger.set_param('dirname', dirname_before) # set param back
        
        if not verbose: 
            contents_after = {f for f in os.listdir(os.path.join(self._path_to_save_to("DARK"))) if f.endswith(".fits")}
            new_files = sorted(contents_after - contents_before)
            print(f"{len(new_files)} new files created.")
        return



    def _save_with_fits_logger(self, save_here, time_taken, num_cubes, verbose=False):
        
        
        contents_before = {f for f in os.listdir(save_here) if f.endswith(".fits")}

        self._logger.set_param('dirname', save_here)
        self._logger.set_param('saveON', True)
        #print("Currently ", self._logger.get_param('filecnt'), " files ")
        
        self._verify_files_are_done(save_here, contents_before, num_cubes, time_taken)
        time.sleep(1)
        contents_after = {f for f in os.listdir(save_here) if f.endswith(".fits")}
        new_files = sorted(contents_after - contents_before)
        if verbose : print(f"{len(new_files)} new files created:", new_files)
        self._logger.set_param('saveON',False)

        return new_files
    
    def _verify_which_files_have_been_done(self, datatyp):
        sets_to_match = self._unique_headers_combinations()
        if datatyp == "FLAT":
            sets_to_match = self._table_for_flat(sets_to_match)
        
        current_sets = self._unique_headers_combinations(self._path_to_save_to(datatyp))
        print("TODO : ", sets_to_match)
        print("Current : ", current_sets)
        

        diff = {k: v for k, v in sets_to_match.items() if current_sets.get(k) != v}
        diff.update({k: v for k, v in current_sets.items() if sets_to_match.get(k) != v})

        if len(diff)==0: 
            print(f"All {datatyp} match the content of the night's folder")
            return {}
        else :
            print("The following sets are missing :\n", diff)
            return diff

        return 1