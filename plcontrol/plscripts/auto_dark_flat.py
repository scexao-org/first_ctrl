# Original code from Miles Lucas (VAMPIRES instrument), modified for FIRST instrument.

import os
import pprint
import time
from datetime import datetime, timezone
from pathlib import Path

import click
import pandas as pd
import tqdm.auto as tqdm
from astropy.io import fits
from scxconf.pyrokeys import FIRST
from swmain.network.pyroclient import connect
#from pyMilk.interfacing.isio_shmlib import SHM as shm
from pyMilk.interfacing.fps import FPS


IS_READOUT_MODE_IN_YET = False
_DEFAULT_DELAY = 3  # s
_ADDED_DELAY = 20 #s
BASE_COMMAND = ("milk-streamFITSlog", "-cset", "q_asl")
DEBUGGING = False
CUBES_FOR_LOW_INTEGRATION_TIME_ARE_STILL_BROKEN = True


def _default_FIRST_raw_folder():
    """ Explicit """
    base = Path("/mnt/datazpool/PL/")
    today = datetime.now(timezone.utc)
    use = base / f"{today:%Y%m%d}"
    test = base / "20250502"
    if DEBUGGING : use = test
    return use


def _relevant_header_for_darks(filename) -> dict:
    """
    List of the headers we want to set as parameters and their values, extracted from our files
    """
    path = Path(filename)
    hdr = fits.getheader(path)
    dark_keys = (
        "PRD-MIN1", #Crop origin
        "PRD-MIN2",
        "PRD-RNG1", #Crop width
        "PRD-RNG2",
        "EXPTIME",
        #"1_DETMOD",
        "DATA-TYP"
    )
    if IS_READOUT_MODE_IN_YET : 
        dark_keys = (
        "PRD-MIN1", #Crop origin
        "PRD-MIN2",
        "PRD-RNG1", #Crop width
        "PRD-RNG2",
        "EXPTIME",
        "1_DETMOD",
        "DATA-TYP"
    )
    return {k: hdr[k] for k in dark_keys}


def unique_headers_combinations(folder=None):
    """
    Collect all the headers from all the saved files and create unique combinations of parameters sets to reproduce
    """
    if folder is None:
        folder = _default_FIRST_raw_folder()
    # get all files taken by the camera
    filenames = list(folder.rglob("*.fits"))
    n_input = len(filenames)

    #logger.info(f"Found {n_input} input FITS files")
    if n_input == 0:
        msg = f"No FITS files found in {folder}"
        raise ValueError(msg)
    
    # get a table from all filenames
    header_rows = [_relevant_header_for_darks(f) for f in filenames]
    # get unique combinations of non dark fits
    header_table = pd.DataFrame(header_rows)
    header_table = header_table[~header_table["DATA-TYP"].isin(["DARK", "BIAS", "FLAT"])]
    header_table = header_table.drop(columns=['DATA-TYP'])
    
    header_table.drop_duplicates(keep="first", inplace=True)
    if IS_READOUT_MODE_IN_YET :header_table.sort_values("1_DETMOD", inplace=True)

    return header_table

def table_for_flat(df):
    """
    Flats requires a specific list of exposure time and not the ones taken during the night. 
    Here, we add these values to the current set of parameters to create a new unique set.
    """
    # 1. Drop the 'EXP-TIME' column
    df = df.drop(columns=['EXPTIME'])
    # 2. Drop duplicate rows across all remaining columns
    df = df.drop_duplicates()
    # 3. Define the list of new EXP-TIME values you want
    exptimes = [0.05, 0.1, 0.25, 0.375, 0.4, 0.5, 0.75, 0.8, 0.875, 1.0,
            1.25, 1.375, 1.5, 1.625, 1.75, 1.875, 2.0, 2.25, 2.375, 2.5,
            2.625, 2.75, 2.875, 3.0, 3.125, 3.25, 3.375, 3.5, 3.625, 3.75,
            3.875, 4.0, 5.0, 6.0, 6.5, 7.0, 8.0, 9.0, 10.0]

    # 4. Create a new DataFrame with all combinations (cartesian product)
    df_expanded = df.merge(pd.DataFrame({'EXPTIME': exptimes}), how='cross')

    return df_expanded

def verify_files_are_done(folder, contents_before, expected_number_of_files, expected_time_taken):

    contents_after = {f for f in os.listdir(folder) if f.endswith(".fits")}
    new_files = sorted(contents_after - contents_before)
    start_time = time.time()
    end_time=time.time()
    while not len(new_files)==expected_number_of_files and not (end_time-start_time)>expected_time_taken:
        contents_after = {f for f in os.listdir(folder) if f.endswith(".fits")}
        new_files = sorted(contents_after - contents_before)
        end_time=time.time()
        print(f"Waiting... {end_time-start_time:.1f} seconds elapsed", end="\r", flush=True)

        print(f"We have... {len(new_files)} new files so far", end="\r", flush=True)
    
    if len(new_files)==expected_number_of_files:
        return True
    
    elif CUBES_FOR_LOW_INTEGRATION_TIME_ARE_STILL_BROKEN==True: 
        return True

    else : 
        print("\nTimeout :(")
        return False

def process_one_camera(table, folder, outdir, DATATYP, num_frames=250, num_cubes=1, verbose=False):#(cam_num: Literal[1, 2], num_frames=1000, folder=None)
    """
    Transmit the sets of parameters needed to the camera in a list of sets, and launch captures with the fits log for every set.
    
    """

    #Connect the camera and logger
    camera = connect(FIRST)
    #firstcam_shm = shm('firstpl')
    logger = FPS('streamFITSlog-firstpl')
    time.sleep(1)
    
    #To implement once readout mode is in for good
    if IS_READOUT_MODE_IN_YET:
        camera.set_readout_mode(table[0]["1_DETMOD"])

    #Prediction of the time to take
    print(table["EXPTIME"], " exptime")
    all_time_taken  = (table["EXPTIME"] * num_cubes * num_frames +1).sum()
    minutes = int(all_time_taken // 60)
    seconds = int(all_time_taken % 60)
    print(f"Now saving {DATATYP}, it will take: {minutes}m {seconds}s for {len(table)} different set of parameters. {num_cubes} cubes of {num_frames} frames will be saved for each set.")



    iterator = table.iterrows()
    if not verbose: #No verbose displays a single progress bar for the saving of all. verbose will have a progress bar for every single set.
        contents_before = {f for f in os.listdir(os.path.join(outdir, DATATYP)) if f.endswith(".fits")}
        iterator = tqdm.tqdm(iterator, total=len(table), desc="Processing rows")

    for index, row in iterator:
        if IS_READOUT_MODE_IN_YET and row["1_DETMOD"] != table[0]["1_DETMOD"]:
            camera.set_readout_mode(row["1_DETMOD"])
        
        if verbose : print("Now taking for the following parameters : \n",row)
        camera.set_tint(row["EXPTIME"])

        dirname_before = folder #logger.get_param('dirname') # should be the last directory we've been saving in
        dirname_after =  outdir #dirname_before #"/home/first/jsarrazin/test_dark/"

        if row["EXPTIME"]>5 : num_frames =100

        logger.set_param("cubesize", num_frames)
        logger.set_param("maxfilecnt", num_cubes)
        logger.set_param("filecnt", 0)

        time_taken = row["EXPTIME"]*num_cubes*num_frames*_DEFAULT_DELAY +_ADDED_DELAY
        print(row["EXPTIME"], " singular exp")
        print(time_taken," s")

        if DATATYP=="FLAT":
            camera.set_keyword("DATA-TYP", "FLAT")
            save_with_fits_logger(dirname_after, "FLAT", logger, time_taken, num_cubes, verbose=verbose)

        if DATATYP=="DARK":
            #os.system('vis_block in') #to uncomment when actually running
            camera.set_keyword("DATA-TYP", "DARK")
            save_with_fits_logger(dirname_after, "DARK", logger, time_taken, num_cubes, verbose=verbose)
            #os.system('vis_block out')

        logger.set_param('dirname', dirname_before) # set param back
    
    if not verbose: 
        contents_after = {f for f in os.listdir(os.path.join(outdir, DATATYP)) if f.endswith(".fits")}
        new_files = sorted(contents_after - contents_before)
        print(f"{len(new_files)} new files created.")
    return

"""
def sleep_with_progress(seconds):
    for _ in tqdm.tqdm(range(int(seconds)), desc="Taking data", unit="s"):
        time.sleep(1)

def sleep_without_progress(seconds):
    for i in range(int(seconds)):
        time.sleep(1)
"""

def save_with_fits_logger(path, DATATYP, logger, time_taken, num_cubes, verbose=False):
    save_here = os.path.join(path, DATATYP)
    os.makedirs(save_here, exist_ok=True)

    contents_before = {f for f in os.listdir(save_here) if f.endswith(".fits")}

    logger.set_param('dirname', save_here)
    logger.set_param('saveON', True)
    print("Currently ", logger.get_param('filecnt'), " files ")
    
    #if verbose : sleep_with_progress(time_taken)
    #else : sleep_without_progress(time_taken)
    verify_files_are_done(save_here, contents_before, num_cubes, time_taken )
    time.sleep(1)

    contents_after = {f for f in os.listdir(save_here) if f.endswith(".fits")}

    new_files = sorted(contents_after - contents_before)
    if verbose : print(f"{len(new_files)} new files created:", new_files)
    logger.set_param('saveON',False)

    return new_files




@click.command("first_auto_flats_n_darks")
@click.argument("data-typ", type=click.Choice(["DARK", "FLAT"], case_sensitive=False), required=False)
@click.argument("folder", type=Path, required=False)
@click.option("-o", "--outdir", type=Path)
@click.option("-nf", "--num-frames", default=10, type=int, help="Number of frames per dark/flat.") 
@click.option("-nc", "--num-cubes", default=2, type=int, help="Number of cubes per dark/flat.")
@click.option("-v", "--verbose", is_flag=True)

def main(folder: Path, outdir: Path, data_typ:str, num_frames: int, num_cubes: int, verbose:bool):
    if data_typ is None:
        raise ValueError("Missing DATA-TYP argument. Specify DARK or FLAT.")
    if folder is None:
        folder = _default_FIRST_raw_folder()
    if outdir is None:
        outdir = folder
    click.echo(f"Saving data to {outdir.absolute()}")
    
    table = unique_headers_combinations(folder) #Return a panda table of unique combinations of headers to cover all cases
    if data_typ=="FLAT":
        table = table_for_flat(table)
    
    if verbose: print("The following parameters will now be taken : \n", table)
    process_one_camera(table, folder = folder, outdir=outdir, DATATYP=data_typ, num_frames=num_frames, num_cubes=num_cubes, verbose=verbose)

if __name__ == "__main__":
    """
    Code to automatically launch darks and flats at the end of the night. 
    The code will look into today's fits file in the pc first and collect sets of parameters to reproduce in darks and flats. 

    Launch the code with the argument "DARK" or "FLAT". 
    """


    #if nothing says, it could be that the fitslogger instance exist for a longer time than the camera instance. Restart the fitslogger with the command :
    # pls.bon.startup_fitslogger()
    main()