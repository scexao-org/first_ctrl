import logging
import os
import time
from concurrent import futures
from pathlib import Path

import click
import numpy as np
import pandas as pd
import tqdm.auto as tqdm
from device_control.facility import WPU, ImageRotator
from scxconf.pyrokeys import FIRST
from swmain.network.pyroclient import connect
from swmain.redis import get_values

from cam_manager import FIRSTLogManager


# set up logging
formatter = logging.Formatter("%(asctime)s|%(name)s|%(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


class PolCalManager:
    """
    PolCalManager
    """

    IMR_POSNS = (45, 57.5, 70, 82.5, 95, 107.5, 120, 132.5)
    HWP_POSNS = (0, 11.25, 22.5, 33.75, 45, 56.25, 67.5, 78.75)
    EXT_HWP_POSNS = (90, 101.25, 112.5, 123.75, 135, 146.25, 157.5, 168.75)
    IMR_INDS_HWP_EXT = (2, 5)

    def __init__(
        self,
        extend: bool = True,
        debug: bool = False,
    ):
        self.camera = connect(FIRST)
        self.manager = FIRSTLogManager()
        self.extend = extend
        self.imr = ImageRotator.connect()
        self.wpu = WPU()
        self.debug = debug
        if self.debug:
            # filthy, disgusting
            logger.setLevel(logging.DEBUG)
            logger.handlers[0].setLevel(logging.DEBUG)


    def prepare(self):
        if self.debug:
            logger.debug("PREPARING FIRST")
            logger.debug("PREPARING WPU:POLARIZER")
            logger.debug("PREPARING WPU:HWP")
            return

        # prepare FIRST

        # prepare wpu
        self.wpu.spp.move_in()  # move polarizer in
        self.wpu.shw.move_in()  # move HWP in

    def move_imr(self, angle):
        if self.debug:
            logger.debug(f"MOVING IMR TO {angle}")
            return

        # move image rotator to position
        self.imr.move_absolute(angle)
        while np.abs(self.imr.get_position() - angle) > 0.01:
            time.sleep(0.5)
        # let it settle so FITS keywords are sensible
        time.sleep(0.5)
        self.imr.get_position()

    def move_hwp(self, angle):
        if self.debug:
            logger.debug(f"MOVING HWP TO {angle}")
            return

        # move HWP to position
        self.wpu.hwp.move_absolute(angle)
        while np.abs(self.wpu.hwp.get_position() - angle) > 0.01:
            time.sleep(0.5)
        # let it settle so FITS keywords are sensible
        time.sleep(0.5)
        # update camera SHM keywords
        hwp_status = self.wpu.hwp.get_status()
        self.camera.set_keyword("RET-ANG1", round(hwp_status["pol_angle"], 2))
        self.camera.set_keyword("RET-POS1", round(hwp_status["position"], 2))

    def iterate_one_filter(self, parity=False):
        logger.info("Starting HWP + IMR loop")
        imr_range = self.IMR_POSNS
        if parity:
            imr_range = list(reversed(imr_range))

        pbar = tqdm.tqdm(imr_range, desc="IMR")
        for i, imrang in enumerate(pbar):
            self.move_imr(imrang)

            hwp_range = self.HWP_POSNS
            if self.extend and i in self.IMR_INDS_HWP_EXT:
                hwp_range = self.HWP_POSNS + self.EXT_HWP_POSNS
            # every other sequence flip the HWP order to minimize travel
            if i % 2 == 1:
                hwp_range = list(reversed(hwp_range))

            pbar.write(f"HWP angles: [{', '.join(map(str, hwp_range))}]")
            for hwpang in tqdm.tqdm(hwp_range, total=len(hwp_range), desc="HWP"):
                self.move_hwp(hwpang)
                self.acquire_cube()

    def acquire_cube(self):
        if self.debug:
            logger.debug("PLAY PRETEND MODE: take FIRST cube")
            return

        self.manager.start_acquisition()
        self.manager.pause_acquisition(wait_for_cube=True)
        time.sleep(0.5)

    def run(self, confirm=False, **kwargs):
        logger.info("Beginning HWP calibration")
        self.prepare()

        # prepare cameras
        if confirm and not click.confirm(
            "Adjust camera settings and confirm when ready, no to skip to next filter",
            default=True,
        ):
            ...
        self.iterate_one_filter(parity=False, **kwargs)



@click.command("firstpl_pol_calib")
@click.option("--debug/--no-debug", default=False, help="Dry run and debug information")
@click.option(
    "-e/-ne",
    "--extend/--no-extend",
    default=True,
    help=f"For IMR angles {'°, '.join(str(PolCalManager.IMR_POSNS[idx]) for idx in PolCalManager.IMR_INDS_HWP_EXT)} extend HWP angles to 180°",
)
def main(debug: bool, extend: bool):
    manager = PolCalManager(extend=extend, debug=debug)
    manager.run()


if __name__ == "__main__":
    main()
