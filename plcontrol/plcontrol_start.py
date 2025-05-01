#coding: utf8

# import standard stuff 
import time
import numpy as np
import ruamel.yaml as yaml
import os

# load configuration file for lantern
lantern_config = "/home/scexao/plcontrol/lantern/config.yml"
loader = yaml.YAML()
config = loader.load(open(lantern_config).read())

# import camera modules and create objects for cam control
from camstack.cams.dcamcam import FIRSTOrcam
from camstack.core.logger import init_camstack_logger
os.makedirs(os.environ['HOME'] + "/logs", exist_ok=True)
init_camstack_logger(os.environ['HOME'] + "/logs/camstack-firstcam.log")
mode = FIRSTOrcam.HRS
cam = FIRSTOrcam('heecam', 'heecam', dcam_number=-1, mode_id=mode, taker_cset_prio=('user', 42))

# create the ZMQ ports for connection to the electronics
import zmq
context = zmq.Context()
ZMQ_TC_ADDRESS = config["zmq_connection"]["tc_port"]
ZMQ_TM_ADDRESS = config["zmq_connection"]["tm_port"]

# import modules for the electronics and create objects
from lantern.packerUnpacker import PackerUnpacker
from lantern import lanternDriver
from lantern import scripts
PUNP = PackerUnpacker(config=config)
ld = lanternDriver.LanternDriver(config = config)
scripts = scripts.LanternScripts(ld = ld, db = ld._driver.db) # add a handle for electronics scripts
ld._driver.verbose_level = 3
ld._driver.connect()
ld._driver.start() # start the receiver part of the driver

# define a function to properly stop electronic driver
def stop():
    ld._driver.stop_receiver()    
    ld._driver.disconnect()

# now we can create the main scripts object and connect it to everything
from plController import PlController
pl_config = "/home/scexao/plcontrol/config_plcontrol.yml"
loader = yaml.YAML()
config = loader.load(open(pl_config).read())
pl = PlController(ld, cam, scripts, ld._driver.db, config = config)
