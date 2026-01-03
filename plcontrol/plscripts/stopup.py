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

_DEFAULT_DELAY = 3  # s 
_ADDED_DELAY = 20 #s
BASE_COMMAND = ("milk-streamFITSlog", "-cset", "q_asl")
DEBUGGING = False
CUBES_FOR_LOW_INTEGRATION_TIME_ARE_STILL_BROKEN = True
#BLOCK

EXPTIMES_FOR_FLATS = [0.05, 0.1, 0.25, 0.375, 0.4, 0.5, 0.75, 0.8, 0.875, 1.0,
                1.25, 1.375, 1.5, 1.625, 1.75, 1.875, 2.0, 2.25, 2.375, 2.5,
                2.625, 2.75, 2.875, 3.0, 3.125, 3.25, 3.375, 3.5, 3.625, 3.75,
                3.875, 4.0, 5.0, 6.0, 6.5, 7.0, 8.0, 9.0, 10.0]

class Eon(Base):
    def __init__(self, *args, **kwargs):
        self.source_files_path = None#self._default_FIRST_raw_folder()
        self._filenames = None#self._list_of_files_containing_the_correct_keywords()
        self.parameters_used = None#[self._relevant_headers(f) for f in self._filenames]
        self.status = {}
        self._acq = None 
        super(Eon, self).__init__(*args, **kwargs)

    def _list_of_files_containing_the_correct_keywords(self, filenames):
        files_that_do_have_them_headers = []
        files_that_dont = []
        for file in filenames:
            try:
                with fits.open(file) as hdul:
                    header = hdul[0].header
                    with fits.open(file) as hdul:
                        if all(key in header for key in ['EXPTIME', 'X_FIRDMD', 'DATA-TYP']) and header['X_FIRDMD'] in ['SLOW', 'FAST']:
                            files_that_do_have_them_headers.append(file)
                        else:
                            files_that_dont.append(file)
            except Exception as e:
                files_that_dont.append(file)
        return files_that_do_have_them_headers
    
    def _path_to_save_to(self, DATATYP):
        """ Explicit """
        tnow = datetime.now(timezone.utc)
        if DATATYP == "DARK":
            dirname = self._config["darkdir"].format(today = tnow.strftime("%Y%m%d"))
        else:
            dirname = self._config["flatdir"].format(today = tnow.strftime("%Y%m%d"))
        os.makedirs(dirname, exist_ok=True)
        return dirname
    
    def _relevant_headers(self, filename):
        """
        List of the headers we want to set as parameters and their values, extracted from our files
        """
        hdr = fits.getheader(filename)
        dark_keys = (
            "EXPTIME",
            "X_FIRDMD",
            "DATA-TYP"
        )
        return {k: hdr[k] for k in dark_keys}
    
    def _unique_headers_combinations(self, folder = None):
        """
        Collect all the headers from all the saved files and create unique combinations of parameters sets to reproduce
        """
        if folder is None:
            folder = self.get_fitslogger_logdir()
        filenames = list(Path(folder).rglob("*.fits"))
        print("{} files found in {}".format(len(filenames), folder))
        filenames = self._list_of_files_containing_the_correct_keywords(filenames)
        print("{} have the correct keywords".format(len(filenames)))
        # get unique combinations of non dark fits        
        header_rows = [self._relevant_headers(f) for f in filenames]
        header_table = pd.DataFrame(header_rows)
        header_table = header_table[~header_table["DATA-TYP"].isin(["DARK", "BIAS"])]
        header_table = header_table.drop(columns=['DATA-TYP'])
        header_table.drop_duplicates(keep="first", inplace=True)
        header_table.sort_values("X_FIRDMD", inplace=True)
        self.status["ALL_SETS_TO_SAVE"] = header_table
        return header_table
    
    def _table_for_flat(self, table):
        """
        Flats requires a specific list of exposure time and not the ones taken during the night. 
        Here, we add these values to the current set of parameters to create a new unique set.
        """
        table = table.drop(columns=['EXPTIME'])  #Drop the 'EXP-TIME' column
        table = table.drop_duplicates() #Drop duplicate rows across all remaining columns
        # new DataFrame with all combinations (cartesian product)
        table_w_new_expt = table.merge(pd.DataFrame({'EXPTIME': EXPTIMES_FOR_FLATS}), how='cross')
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
    
    def _preping_bench_for_save(self, set:dict, num_cubes, num_frames, verbose = False):
        self.status["NOW_SAVING"] = set
        if verbose : print("Now taking for the following parameters : \n",set)         
        if num_frames is None :
            if set["EXPTIME"]>0.5 : num_frames =250 #1000 until 0.5s, 250 until 1s, 100 for anything above
            if set["EXPTIME"]>1 : num_frames =100 
            else : num_frames = 1000      
        if str(set["X_FIRDMD"]) != str(self._cam.get_readout_mode()):
            self._acq.set_readout_mode(set["X_FIRDMD"])
        self._cam.set_tint(set["EXPTIME"])
        self.logger.set_param("cubesize", num_frames)
        self.logger.set_param("maxfilecnt", num_cubes)

        time_to_take = set["EXPTIME"]*num_cubes*num_frames*_DEFAULT_DELAY +_ADDED_DELAY
        return time_to_take

    def _verify_which_files_have_been_done(self, datatyp, folder=None): #TO FINISH
        sets_to_match = self._unique_headers_combinations(folder=folder)
        datatyp=datatyp.upper()
        if datatyp == "FLAT":
            sets_to_match = self._table_for_flat(sets_to_match)
        
        current_sets = self._unique_headers_combinations(folder=folder)#self._path_to_save_to(datatyp))
        print("TODO : ", sets_to_match)
        print("Current : ", current_sets)
        
        diff = {k: v for k, v in sets_to_match.items() if current_sets.get(k) != v}
        diff.update({k: v for k, v in current_sets.items() if sets_to_match.get(k) != v})

        if len(diff)==0: 
            print(f"All {datatyp} match the content of the night's folder")
            return True
        else :
            print("The following sets are missing :\n", diff)
            a = input(f"Launch the missing {datatyp}s ? y/n\n")
            if a.lower()=="y":
                if datatyp=="FLAT":
                    self.save_flats(sets=diff)
                else:
                    b = input("Block light using vis block in ? y/n")
                    self.save_darks(sets=diff, block_light_on_the_bench=(b.lower()=="y"))
            return diff
    
    def _save_single_sequence(self, data_typ, detmod, exptime, num_frames=None, num_cubes=1, verbose=False, reset_system = True):
        self._acq.set_mode_rolling(0, 0)
        if num_frames is None :
            if exptime>0.5 : num_frames =250 #1000 until 0.5s, 250 until 1s, 100 until 150s, 50 for anything above.
            if exptime>1 : num_frames =100
            if exptime>150 : num_frames = 50 
            else : num_frames = 500
        dirname_before = self.get_fitslogger_logdir()      
        time_to_take = self._preping_bench_for_save({"EXPTIME": exptime, "X_FIRDMD": detmod}, num_cubes, num_frames, verbose=verbose)  
        save_here = Path(self._path_to_save_to(data_typ))
        contents_before = {f for f in os.listdir(save_here) if f.endswith(".fits")}
        # start acquisition
        self._acq.save_with_fitslogger(dirname = save_here, tint = exptime, readout_mode = detmod, ncubes = num_cubes, nimages = num_frames, data_typ = data_typ)
        # wait for files to be done
        self._verify_files_are_done(save_here, num_cubes, time_to_take)
        time.sleep(1)
        contents_after = {f for f in os.listdir(save_here) if f.endswith(".fits")}
        new_files = sorted(contents_after - contents_before)
        if verbose : print(f"{len(new_files)} new files created:", new_files)        
        # just make sure the fitslogger is off
        self.logger.set_param('saveON', False)
        if reset_system:
            self._reset_camera(dirname_before)
        return None        

    def save_single_flat(self, detmod, exptime, num_frames=None, num_cubes=1, verbose=False, reset_system = True):
        """
        Take the flats for a single set of parameters
        @param detmod: detector readout mode (SLOW or FAST)
        @param exptime: exposure time (in s)
        """
        self._save_single_sequence("FLAT", detmod, exptime, num_frames=num_frames, num_cubes=num_cubes, verbose=verbose, reset_system=reset_system)
        return None

    def save_single_dark(self, detmod, exptime, num_frames=None, num_cubes=1, verbose=False, reset_system= True, block_light_on_the_bench=False):
        """
        Take the darks for a single set of parameters
        @param detmod: detector readout mode (SLOW or FAST)
        @param exptime: exposure time (in s)
        """   
        if block_light_on_the_bench:
            os.system('vis_block in') #to uncomment when actually running
        self._save_single_sequence("DARK", detmod, exptime, num_frames=num_frames, num_cubes=num_cubes, verbose=verbose, reset_system=reset_system)
        if block_light_on_the_bench:
            os.system('vis_block out')
        return

    def save_flats(self, num_frames=None, num_cubes=1, verbose=False, sets=None, folder=None):
        """
        Transmit the sets of parameters needed to the camera in a list of sets, and launch captures with the fits log for every set.
        """
        if sets is None:
            table = self._unique_headers_combinations(folder=folder)
            table = self._table_for_flat(table)
            time.sleep(1)
            dirname_before = self.get_fitslogger_logdir()
            # Set up first readout mode
            self._cam.set_readout_mode(table["X_FIRDMD"][0])
        else : 
            table = sets
        # Prepping for the loop
        #self._estimate_total_time(self, table, num_cubes, num_frames)
        iterator = table.iterrows()

        if not verbose: #No verbose displays a single progress bar for the saving of all. verbose will have a progress bar for every single set.
            contents_before = {f for f in os.listdir(self._path_to_save_to("FLAT")) if f.endswith(".fits")}
            iterator = tqdm.tqdm(iterator, total=len(table), desc="Processing rows")

        for index, row in iterator:
            self.save_single_flat(row["X_FIRDMD"], row["EXPTIME"], num_frames=num_frames, num_cubes=num_cubes, verbose=verbose, reset_dirname=False)

        self._reset_camera(dirname_before) # set param back
        
        if not verbose: 
            contents_after = {f for f in os.listdir(self._path_to_save_to("FLAT")) if f.endswith(".fits")}
            new_files = sorted(contents_after - contents_before)
            print(f"{len(new_files)} new files created.")
        return
    

    def save_darks(self, num_frames=None, num_cubes=3, verbose=False, block_light_on_the_bench=False, sets=None, folder=None):#(cam_num: Literal[1, 2], num_frames=1000, folder=None)
        """
        Transmit the sets of parameters needed to the camera in a list of sets, and launch captures with the fits log for every set.
        """
        if sets is None:
            table = self._unique_headers_combinations(folder = folder)
            time.sleep(1)
            dirname_before = self.get_fitslogger_logdir()
            self._acq.set_readout_mode(table["X_FIRDMD"][0])
            # Prepping for the loop
            #self._estimate_total_time(self, table, num_cubes, num_frames)
        else : 
            table=sets
        iterator = table.iterrows()
        if not verbose: #No verbose displays a single progress bar for the saving of all. verbose will have a progress bar for every single set.
            contents_before = {f for f in os.listdir(os.path.join(self._path_to_save_to("DARK"))) if f.endswith(".fits")}
            iterator = tqdm.tqdm(iterator, total=len(table), desc="Processing rows")

        if block_light_on_the_bench:
            os.system('vis_block in') #to uncomment when actually running            

        for index, row in iterator:
            self.save_single_dark(row["X_FIRDMD"], row["EXPTIME"], num_frames=num_frames, num_cubes=num_cubes, verbose=verbose, reset_system=False, block_light_on_the_bench=False)

        if block_light_on_the_bench:
            os.system('vis_block out') #to uncomment when actually running

        self._reset_camera(dirname_before)
        
        if not verbose: 
            contents_after = {f for f in os.listdir(os.path.join(self._path_to_save_to("DARK"))) if f.endswith(".fits")}
            new_files = sorted(contents_after - contents_before)
            print(f"{len(new_files)} new files created.")
        return None

    def _reset_camera(self,dirname_before):
        #Return to FAST, exptime of 0.0001s, restore previous directory for fitslogger.
        self._cam.set_tint(0.001)
        self._acq.set_readout_mode("FAST")
        self.logger.set_param('dirname', dirname_before)
