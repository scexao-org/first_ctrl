import logging
import subprocess
import time
from pathlib import Path
from typing import Literal

from paramiko import AutoAddPolicy, SSHClient
from pyMilk.interfacing.fps import FPS
from swmain.redis import RDB

logger = logging.getLogger(__name__)


class CamLogManager:
    DATA_DIR_BASE = Path("/mnt/fuuu/")
    ARCHIVE_DATA_DIR_BASE = Path("/mnt/fuuu/ARCHIVED_DATA")
    USER = "scexao"
    COMPUTER = "scexao5"
    BASE_COMMAND = ("milk-streamFITSlog",) 

    def __init__(self, shm_name: str):
        self.shm_name = shm_name
        fps_name = f"streamFITSlog-{self.shm_name}"
        self.fps = FPS(fps_name)

    @classmethod
    def create(cls, shm_name, num_frames: int, num_cubes=-1, folder=None):
        # if archive:
        #     save_dir = cls.ARCHIVE_DATA_DIR_BASE
        # else:
        #     save_dir = cls.DATA_DIR_BASE
        path = Path(folder) / shm_name
        # print(f"Saving data to directory {folder.absolute()}")
        cmd = [
            "ssh",
            f"{cls.USER}@{cls.COMPUTER}",
            *cls.BASE_COMMAND,
            "-z",
            str(num_frames),
            "-D",
            str(path.absolute()),
        ]
        if num_cubes > 0:
            cmd.extend(("-c", f"{num_cubes}"))
        cmd.extend((shm_name, "pstart"))
        subprocess.run(cmd, check=True, capture_output=True)
        time.sleep(0.5)
        return cls(shm_name)

    def start_acquisition(self):
        # start logging
        self.fps.set_param("saveON", True)
        self.update_keys(logging=True)

    def pause_acquisition(self, wait_for_cube=False):
        # pause logging
        if wait_for_cube:
            # allow cube to fill up
            self.fps.set_param("lastcubeON", True)
            self.wait_for_acquire()
            # sometimes you call lastcube but saveON is false,
            # so let's clean this up to avoid messy situations
            self.fps.set_param("lastcubeON", False)
        else:
            # truncate cube immediately
            self.fps.set_param("saveON", False)
        self.update_keys(logging=False)

    def wait_for_acquire(self):
        _wait_delay = 0.1
        while self.fps.get_param("saveON"):
            time.sleep(_wait_delay)

    def kill_process(self):
        command = ["ssh", f"{self.USER}@{self.COMPUTER}", *self.base_command, self.shm_name, "kill"]
        subprocess.run(command, check=True, capture_output=True)
        self.update_keys(logging=False)

    def acquire_cubes(self, num_cubes: int):
        # assert we start at 0 filecnt
        self.fps.set_param("filecnt", 0)
        self.fps.set_param("maxfilecnt", num_cubes)
        self.start_acquisition()
        self.wait_for_acquire()

    def update_keys(self, logging: bool):
        pass


class FIRSTLogManager(CamLogManager):
    COMPUTER = "kamua"
    USER = "first"
    DATA_DIR_BASE = Path("/mnt/datazpool/PL/")

    def __init__(self, **kwargs):
        super().__init__("firstpl", **kwargs)

    @classmethod
    def create(cls, num_frames: int, num_cubes=-1, folder=None):
        shm_name = "firstpl"
        # if archive:
        #     save_dir = cls.ARCHIVE_DATA_DIR_BASE
        # else:
        #     save_dir = cls.DATA_DIR_BASE
        path = Path(folder) / shm_name
        # print(f"Saving data to directory {folder.absolute()}")
        cmd = [
            "ssh",
            f"{cls.USER}@{cls.COMPUTER}",
            *cls.BASE_COMMAND,
            "-z",
            str(num_frames),
            "-D",
            str(path.absolute()),
        ]
        if num_cubes > 0:
            cmd.extend(("-c", f"{num_cubes}"))
        cmd.extend((shm_name, "pstart"))
        subprocess.run(cmd, check=True, capture_output=True)
        time.sleep(0.5)
        return cls()
