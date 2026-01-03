#coding: utf8
import subprocess
import ruamel.yaml as yaml
import os

print('STARTING PHOTONIC LANTERN CONTROL SYSTEM...')

# load configuration file for lantern
lantern_config = os.environ['HOME']+"/src/firstctrl/first_ctrl/plcontrol/lantern/config.yml"
loader = yaml.YAML()
config = loader.load(open(lantern_config).read())

# Prepare dependent processes for the upd stream for other apps using the images (e.g. PL-wavefront sensor?)
from camstack.core import tmux, utilities as util
import scxconf
print("Starting UPD streams")
STREAM_NAME = 'firstpl'
STREAM_NAME_BIN = 'firstpl_bin'
udp_recv = util.RemoteDependentProcess(
            tmux_name=f'streamUDPreceive_{scxconf.TCPPORT_FIRST_ORCA}',
            # Urrrrrh this is getting messy
            cli_cmd=f'milk-nettransmit {scxconf.TCPPORT_FIRST_ORCA} -c tcprecv1 -p 80 -U',
            cli_args=(),
            remote_host='scexao@' + scxconf.IPLAN_SC6,
            kill_upon_create=False,
        )
udp_send = util.DependentProcess(
            tmux_name='first_tcp',
            cli_cmd='milk-nettransmit %d -T %s -s %s -U',
            cli_args=(scxconf.TCPPORT_FIRST_ORCA, scxconf.IPLAN_SC6, STREAM_NAME_BIN),
            # Sender is kill_upon_create - rather than when starting. that ensures it dies well before the receiver
            # Which is better for flushing TCP sockets
            kill_upon_create=True,
            cset='f_tcp', # Root cause there's no predefined RT conf with cpusets on kamua
            rtprio=45,
        )
util.process_ordering_start([udp_recv, udp_send])
util.process_ordering_stop([udp_recv, udp_send])

# import camera modules and create objects for cam control
from camstack.cams.dcamcam import FIRSTOrcam
from camstack.core.logger import init_camstack_logger
os.makedirs(os.environ['HOME'] + "/logs", exist_ok=True)
init_camstack_logger(os.environ['HOME'] + "/logs/camstack-firstcam.log")
mode = FIRSTOrcam.FIRSTPL
print("Starting camera")
cam = FIRSTOrcam(STREAM_NAME, STREAM_NAME, dcam_number=0, mode_id=mode,
                     taker_cset_prio=('f_asl', 42),
                     dependent_processes=[udp_recv, udp_send])
os.system("milk-streamFITSlog -d \"/mnt/datazpool/PL/\" -z 250 firstpl pstart") # Start the FITS logging process

# FITSMERGER
# Update the fitsmerger
# Send the command to the tmux session
print("Updating the fitsmerger...")
subprocess.run(["tmux", "send-keys", "-t", "firstpl_fitsmerger", " merger.change_target_dir()", "Enter"])


# PYROSERVER
from scxconf import PYRONS3_HOST, PYRONS3_PORT
from camstack import pyro_keys as pk
from swmain.network.pyroserver_registerable import PyroServer
print("Starting Pyroserver")
server = PyroServer(nsAddress=(PYRONS3_HOST, PYRONS3_PORT))
server.add_device(cam, pk.FIRST, add_oneway_callables=True)
server.start()

# create the zaber objects
from zaber.zaber_chain3 import Zaber
print("Connecting to zabers")
zab = Zaber()
zab._open("vis")
zab.start()

# create the ZMQ ports for connection to the electronics
import zmq
context = zmq.Context()
ZMQ_TC_ADDRESS = config["zmq_connection"]["tc_port"]
ZMQ_TM_ADDRESS = config["zmq_connection"]["tm_port"]

# import modules for the electronics and create objects
from lantern.packerUnpacker import PackerUnpacker
from lantern import lanternDriver
from lantern import scripts
print("Starting Tip/Tilt")
PUNP = PackerUnpacker(config=config)
ld = lanternDriver.LanternDriver(config = config)
scripts = scripts.LanternScripts(ld = ld, db = ld._driver.db) # add a handle for electronics scripts
ld._driver.verbose_level = 3
ld._driver.connect()
ld._driver.start() # start the receiver part of the driver

# define a function to properly stop electronic driver
def stop():
    zab.stop()
    zab.close()
    print("Zabers closed")
    ld._driver.stop_receiver()    
    ld._driver.disconnect()

# now we can create the main scripts object and connect it to everything
pl_config = os.environ['HOME']+"/src/firstctrl/first_ctrl/plcontrol/config_plcontrol.yml"
loader = yaml.YAML()
config = loader.load(open(pl_config).read())
import plscripts as pls
pls._linkit(lanternDriver_handle = ld, camera_handle = cam, database_handle = ld._driver.db, scripts_handle = scripts, config_handle = config, zabers_handle = zab)


# update some keywords at startup
from swmain import redis
from scxconf.pyrokeys import FIRST as _FIRST
from swmain.network.pyroclient import connect as _connect
_CAM = _connect(_FIRST)
x, y = zab.get_position()
ld.get_version()
ld._driver.db.validate_last_tc()
version_reply = ld._driver.db.tcs[-1].reply[0]["data"]["tc_reply_data"]
keywords = {"X_FIRZBX": x,
            "X_FIRZBY": y,
            "X_FIROBX": 0,
            "X_FIROBY": 0,
            "X_FIRVER": "{};{}".format(version_reply["version"], version_reply["config"].decode())}
redis.update_keys(**keywords)
for key in keywords.keys():
    _CAM.set_keyword(key, keywords[key])   

print("Tip/Tilt firmware verion {version} with config {config}".format(version = version_reply["version"], config = version_reply["config"].decode()))
print("Zabers at x = {} steps, y = {} steps".format(x, y))
print("Ready to go!")