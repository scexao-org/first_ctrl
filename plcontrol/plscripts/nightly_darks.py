# Original code from Miles Lucas (VAMPIRES instrument), modified for FIRST instrument.

import multiprocessing as mp
import os
import pprint
import time
from datetime import datetime, timezone
from logging import getLogger
from pathlib import Path
from typing import Literal
from astropy.time import Time

import click
import pandas as pd
import tqdm.auto as tqdm
from astropy.io import fits
from scxconf.pyrokeys import FIRST
from swmain.network.pyroclient import connect
from pyMilk.interfacing.isio_shmlib import SHM as shm
from pyMilk.interfacing.fps import FPS


IS_READOUT_MODE_IN_YET = False

#from vampires_control.acquisition.manager import VCAMLogManager


# copied from plcontrol_start.py
# will be removed as cam will be an argument when we make this script to a class
"""
from camstack.cams.dcamcam import FIRSTOrcam
from camstack.core.logger import init_camstack_logger
os.makedirs(os.environ['HOME'] + "/logs", exist_ok=True)
init_camstack_logger(os.environ['HOME'] + "/logs/camstack-firstcam.log")
mode = FIRSTOrcam.HRS
cam = FIRSTOrcam('heecam', 'heecam', dcam_number=-1, mode_id=mode, taker_cset_prio=('user', 42))
"""

#logger = getLogger(__file__)
_DEFAULT_DELAY = 2  # s


def _default_FIRST_raw_folder():
    base = Path("/mnt/datazpool/PL/")
    today = datetime.now(timezone.utc)
    debugging = base / "20250502"
    return debugging#base / f"{today:%Y%m%d}"



def _relevant_header_for_darks(filename) -> dict:
    path = Path(filename)
    hdr = fits.getheader(path)
    dark_keys = (
        "PRD-MIN1", #Crop origin
        "PRD-MIN2",
        "PRD-RNG1", #Crop width
        "PRD-RNG2",
        "EXPTIME",
        #"OBS-MOD",
        "DATA-TYP"
    )
    if IS_READOUT_MODE_IN_YET :
        dark_keys = (
        "PRD-MIN1", #Crop origin
        "PRD-MIN2",
        "PRD-RNG1", #Crop width
        "PRD-RNG2",
        "EXPTIME",
        "OBS-MOD",
        "DATA-TYP"
    )
    return {k: hdr[k] for k in dark_keys}


def unique_headers_combinations(folder=None):
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
    header_table = header_table[~header_table["DATA-TYP"].isin(["DARK", "BIAS"])]
    

    #exp time only
    #dark_keys = ["EXPTIME"]
    #header_table.drop_duplicates(dark_keys, keep="first", inplace=True)
    #header_table.sort_values(dark_keys, inplace=True)
    header_table.drop_duplicates(keep="first", inplace=True)
    header_table.sort_values("OBS-MOD", inplace=True)


    return header_table


def _estimate_total_time(headers):
    headers["TINT"] = headers["EXPTIME"] * headers["nframes"]
    #groups = headers.groupby("U_CAMERA")
    tints = headers["TINT"].sum() + len(headers) * _DEFAULT_DELAY
    return tints.max()


BASE_COMMAND = ("milk-streamFITSlog", "-cset", "q_asl")


def _set_readout_mode(mode: str, pbar):
    camera = connect(FIRST)
    pbar.write(f"Setting readout mode to {mode}")
    # readout mode
    camera.set_readout_mode(mode.strip().upper())


class WrongComputerError(BaseException):
    pass


def _set_camera_crop(camera, crop, obsmode, pbar):
    w_offset, h_offset, width, height = crop
    # gotta do backflips to make sure data is labeled correctly
    if obsmode.endswith("MBI"):
        modename = "MBI"
    elif obsmode.endswith("MBIR"):
        modename = "MBI_REDUCED"
    elif obsmode.endswith("PUP"):
        modename = "PUPIL"
    else:
        modename = "CUSTOM"

    pbar.write(f"Setting camera crop x={w_offset} y={h_offset} w={width} h={height} ({modename})")

    camera.set_camera_size(height, width, h_offset, w_offset, mode_name=modename)

def save_chunk(firstcam, firstcam_shm, nframes, name, data_type = None):
    nframe_cut = 100
    if nframes > nframe_cut:
        nframes = nframe_cut
        nfiles = nframes // nframe_cut
    else:
        nfiles = 1

    for n in range(nfiles):
        cube = firstcam_shm.multi_recv_data(n=nframes, output_as_cube = 1)

        tint = firstcam.get_tint()
        temp = firstcam.get_temperature()
        mod = firstcam.get_readout_mode()

        hdu = fits.PrimaryHDU(cube)
        timestamp = Time.now().isot
        hdu.header['DATE-OBS'] = timestamp
        hdu.header['EXPTIME'] = tint
        hdu.header['TEMP'] = temp
        hdu.header['OBS-ID'] = mod

        if data_type != None:
            hdu.header['DATA-TYP'] = data_type

        hdu.writeto(f'{name}_{n}_{timestamp}.fits', overwrite=True)
        print(f'Saved {name}_{n}_{timestamp}.fits')


def process_one_camera(table, folder=None):#(cam_num: Literal[1, 2], num_frames=1000, folder=None)
    
    camera = connect(FIRST)
    firstcam_shm = shm('firstpl')
    logger = FPS('streamFITSlog-firstpl')

    #manager = VCAMLogManager.create(cam_num, num_frames=num_frames, num_cubes=1, folder=folder) #Vomanagerir comment logger pour FIRST
    time.sleep(1)

    if IS_READOUT_MODE_IN_YET:
        camera.set_readout_mode(table[0]["OBS-ID"])

    for index, row in table.iterrows():
        if IS_READOUT_MODE_IN_YET and row["OBS-ID"] != table[0]["OBS-ID"]:
            camera.set_readout_mode(row["OBS-ID"])
            
        camera.set_tint(row["EXPTIME"])

        path = "/jsarrazin/test_dark/"
        save_chunk(camera, firstcam_shm, 1, path+f'firstpl_flat_{row["EXPTIME"]}s', data_type='FLAT')

        #os.system('vis_block in')
        time.sleep(2)
        save_chunk(camera, firstcam_shm, 1, path+f'firstpl_dark_{row["EXPTIME"]}s', data_type='DARK')
        #os.system('vis_block out')
        time.sleep(2)
        



def process_dark_frames(table, folder):
    print("Now processing darks")
    with mp.Pool(1) as pool:   
        job = pool.apply_async(process_one_camera, args=(table, None))
        job.get()

    print("End of function")


@click.command("first_autodarks")
@click.argument("folder", type=Path, default=_default_FIRST_raw_folder())
@click.option("-o", "--outdir", type=Path)
@click.option("-n", "--num-frames", default=1, type=int, help="Number of frames per dark.") #250
@click.option("-y", "--no-confirm", is_flag=True, help="Skip confirmation prompts.")

def main(folder: Path, outdir: Path, num_frames: int, no_confirm: bool):
    print("Beginning main")
    if outdir is None:
        outdir = folder
    click.echo(f"Saving data to {outdir.absolute()}")
    #if os.getenv("WHICHCOMP", "") != "5":
    #    msg = "This script must be run from sc5 in the `vampires_control` conda env"
    #    raise WrongComputerError(msg)

    
    table = unique_headers_combinations(folder) #Return a panda table of unique combinations of headers to cover all cases

    table["nframes"] = num_frames
    mask_med = (table["EXPTIME"] > 0.5) & (table["EXPTIME"] < 5)
    table[mask_med]["nframes"] = 500 #we're going to take a lot of darks of exp time >0.5 and <5
    mask_long = table["EXPTIME"] >= 5
    table[mask_long]["nframes"] = 100 # a lot less for higher exp time

    table[:]["nframes"] = 1


    pprint.pprint(table)
    est_tint = _estimate_total_time(table) # frame * exp_time + delay
    click.echo(f"Est. time for all darks with {num_frames} frames each is {est_tint/60:.01f} min.")
    click.echo(f"The following settings of darks will be saved : \n {table}")


    process_dark_frames(table, outdir)

if __name__ == "__main__":
    main()