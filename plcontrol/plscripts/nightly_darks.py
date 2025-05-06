# Original code from Miles Lucas (VAMPIRES instrument), modified for FIRST instrument.

import multiprocessing as mp
import os
import pprint
import time
from datetime import datetime, timezone
from logging import getLogger
from pathlib import Path
from typing import Literal

import click
import pandas as pd
import tqdm.auto as tqdm
from astropy.io import fits
from scxconf.pyrokeys import FIRST
from swmain.network.pyroclient import connect


from vampires_control.acquisition.manager import VCAMLogManager


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

"""
class all_darks_considered(object):
    def __init__(self, cam, ld, scripts, db):
        self._cam = cam
        self._ld = ld
        self._scripts = scripts
        self._db = db
"""

def _default_FIRST_raw_folder():
    base = Path("/mnt/datazpool/PL/")
    today = datetime.now(timezone.utc)
    debugging = base / "20250502"
    return debugging#base / f"{today:%Y%m%d}"



def _relevant_header_for_darks(filename) -> dict:
    path = Path(filename)
    hdr = fits.getheader(path)
    dark_keys = (
        "PRD-MIN1",
        "PRD-MIN2",
        "PRD-RNG1",
        "PRD-RNG2",
        "EXPTIME",
        "DATA-TYP",
        "OBS-MOD"
        
    )
    return {k: hdr[k] for k in dark_keys}


def vampires_dark_table(folder=None):
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

    print(header_table.columns)
    header_table = header_table[~header_table["DATA-TYP"].isin(["DARK", "BIAS"])]
    


    dark_keys = ["EXPTIME"]
    header_table.drop_duplicates(dark_keys, keep="first", inplace=True)
    header_table.sort_values(dark_keys, inplace=True)
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


def process_one_camera(table, folder=None):#(cam_num: Literal[1, 2], num_frames=1000, folder=None)
    camera = connect(FIRST)
    manager = VCAMLogManager.create(cam_num, num_frames=num_frames, num_cubes=1, folder=folder) #Voir comment logger pour FIRST
    time.sleep(1)
    table["crop"] = table.apply(
        lambda r: (r["PRD-MIN1"], r["PRD-MIN2"], r["PRD-RNG1"], r["PRD-RNG2"]), axis=1
    )

    #"""
    #replacing
    pbar =  tqdm.tqdm(table.groupby("crop"), desc="Crop")
    for crop_key, crop_group in pbar:
        manager.fps.run_stop()
        manager.fps.conf_stop()
        _set_camera_crop(camera, crop_key, crop_group["OBS-MOD"].iloc[0], pbar=pbar)

        # If OBS-MOD is your new "readout mode"
        for readout_mode, sub_group in tqdm.tqdm(
            crop_group.groupby("OBS-MOD"), desc="Readout mode", leave=False
        ):
            _set_readout_mode("SLOW", pbar=pbar) #readout_mode instead of SLOW

            for _, row in tqdm.tqdm(sub_group.iterrows(), total=len(sub_group), desc="Exp. time", leave=False):
                camera.set_keyword("DATA-TYP", "DARK")
                camera.set_tint(row["EXPTIME"])

                manager.fps.conf_start(5.0)
                manager.fps.set_param("cubesize", row["nframes"])
                manager.fps.run_start(100.0)
                assert manager.fps.run_isrunning()
                manager.acquire_cubes(1)

    """
    pbar = tqdm.tqdm(table.groupby("crop"), desc="Crop")

    for key, group in pbar:
        #manager.fps.run_stop()
        #manager.fps.conf_stop()
        _set_camera_crop(camera, key, group["OBS-MOD"].iloc[0], pbar=pbar)

        pbar2 = tqdm.tqdm(
            group.sort_values("U_DETMOD", ascending=False).groupby("U_DETMOD"),
            desc="Det. mode",
            leave=False,
        )
        for key2, group2 in pbar2: #pbar2
            print("pbar ",pbar)
            print("key2 ", key2) #supposed to be fast/slow i think
            print("group2 ", group2)
            _set_readout_mode(key2, pbar=pbar)
            pbar3 = tqdm.tqdm(group2.iterrows(), total=len(group2), desc="Exp. time", leave=False)
            for _, row in pbar3:
                camera.set_keyword("DATA-TYP", "DARK")
                camera.set_tint(row["EXPTIME"])
                #manager.fps.conf_start(5.0)
                #manager.fps.set_param("cubesize", row["nframes"])
                #manager.fps.run_start(100.0)
                #assert manager.fps.run_isrunning()
                #manager.acquire_cubes(1)
                #"""


def process_dark_frames(table, folder):
    print("Now processing darks")
    kwargs = dict(folder=folder)
    #groups = table.groupby("U_CAMERA")
    groups = table
    with mp.Pool(1) as pool:
        
        job = pool.apply_async(process_one_camera, args=(table, None))
        job.get()

        #job = []
        #for key, group in groups:
        #    job = pool.apply_async(process_one_camera, args=(group, key), kwds=kwargs)
        #    jobs.append(job)
        #for job in jobs:
        #    job.get()

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
    
    print("1")
    table = vampires_dark_table(folder) #Return a panda table of unique combinations of headers to cover all cases
    print("2")

    table["nframes"] = num_frames
    mask_med = (table["EXPTIME"] > 0.5) & (table["EXPTIME"] < 5)
    table[mask_med]["nframes"] = 500 #we're going to take a lot of darks of exp time >0.5 and <5
    mask_long = table["EXPTIME"] >= 5
    table[mask_long]["nframes"] = 100 # a lot less for higher exp time
    pprint.pprint(table)
    est_tint = _estimate_total_time(table) # frame * exp_time + delay
    click.echo(f"Est. time for all darks with {num_frames} frames each is {est_tint/60:.01f} min.")
    
    process_dark_frames(table, outdir)

if __name__ == "__main__":
    main()