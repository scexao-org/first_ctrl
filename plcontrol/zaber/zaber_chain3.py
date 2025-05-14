#!/usr/bin/env python
import serial
import os
import time
import sys
home = os.getenv('HOME')
sys.path.append(home+'/src/lib/python/')
import zaber.logit as logit #Custom logging library
# we need some stuff for the keywords
from swmain import redis
from swmain.network.pyroclient import connect
from scxconf.pyrokeys import FIRST
CAM = connect(FIRST)

from pyMilk.interfacing.isio_shmlib import SHM as shm

# zabers can track the target so we need threading
from lantern.utils import StoppableThread
from plscripts.geometry import Geometry

ZAB_X_IND = 1
ZAB_Y_IND = 2

ZAB_X_NAME = "first_pl_inj_x"
ZAB_Y_NAME = "first_pl_inj_x"

delay = 0.1 

def step2zaberByte(nstep):
    step = nstep        # local version of the variable
    zbytes = [int(0),int(0),int(0),int(0)]  # series of four bytes for Zaber
    if step < 0: step += 256**4
    for i in range(3,-1,-1):
        zbytes[i] = step // 256**i
        step     -= zbytes[i] * 256**i
    return zbytes
                                                     
def zaberByte2step(zb):
    nstep = 0
    for i in range(len(zb)):
        nstep += zb[i]*256**i
        if i == 3:
            if zb[3] > 127: nstep -= 256**4
        
    return nstep

def zab_cmd(cmd):
    nl = []
    instr = list(map(int, cmd.split(' ')))

    for c in instr:
        if c == 255: nl.extend([c,c])
        else:        nl.append(c)

    buf = ''.join(list(map(chr, nl)))
    return buf.encode('latin-1')


class Zaber(StoppableThread):
    def __init__(self):
        super(Zaber, self).__init__()
        self._s = None
        self.vcam1_xy = shm("vcam1_xy")
        self.xvam1_0 = None
        self.yvam1_0 = None
        self.xzab_0 = None
        self.yzab_0 = None
        self.tracking = False
        self.period = 1
        return None

    def _open(self, zaberchain):
        filename = "/home/first/bin/devices/conf/path_zabchain_"+zaberchain+".txt"
        filep = open(filename, 'r')
        self._dev  = "/dev/serial/"
        self._dev += filep.read().rstrip('\n')
        try:
            self._s = serial.Serial(self._dev, 9600, timeout=0.1)
            dummy = self._s.readlines() # flush the port
        except:
            print("Zaber chain %s not connected" %zaberchain)
            sys.exit()

    def home(self, idn, devname):
        self._command(idn, 1, 0)
        logit.logit(devname,'Homed')

    def _move(self, idn, pos, devname, log=True):
        self._command(idn, 20, pos)
        time.sleep(delay)
        if log:
            logit.logit(devname,'moved_to_'+str(pos))
        
    def _push(self, idn, step, devname, log=True):
        self._command(idn, 21, step)
        time.sleep(delay)
        if log:
            logit.logit(devname,'moved_rel_'+str(step))
      
    def _status(self, idn):
        pos = self._command(idn, 60, 0)
        return pos

    def _command(self, idn, cmd, arg, quiet=True):
        args = ' '.join(map(str, step2zaberByte(int(arg))))
        full_cmd = '%s %d %s' % (idn, cmd, args)
        #if not quiet:
        self._s.write(zab_cmd(full_cmd))
        dummy = ''.encode()
        dummy = self._s.read_until(b'\r\n')
        reply = zaberByte2step(dummy[2:])
        if not quiet:
            print("zaber %d = %d" % (int(idn), reply))
        return(reply)

    def move(self, x = None, y = None, log = True):
        """
        Move zabers to given x, y position. Leave one param to none to not move the axis
        @param x: position along the x axis (in steps)
        @param y: position along the y axis (in steps)
        """
        if not(x is None):
            self._move(ZAB_X_IND, x, ZAB_X_NAME, log = log)
        if not(y is None):
            self._move(ZAB_Y_IND, y, ZAB_Y_NAME, log = log)
        x, y = self.get_position()
        keywords = {"X_FIRZBX": x,
                    "X_FIRZBY": y}
        redis.update_keys(**keywords)
        for key in keywords.keys():
            CAM.set_keyword(key, keywords[key])               
        return None

    def get_position(self):
        """
        Return the x,y position of the zabers in steps
        """
        x = self._status(ZAB_X_IND)
        y = self._status(ZAB_Y_IND)
        return x, y
    
    def delta_move(self, dx = None, dy = None, log = True):
        """
        Move the zabers by some amount dx and dy relative to current position
        @param dx: position along the x axis (in steps)
        @param dy: position along the y axis (in steps)        
        """
        x, y = self.get_position()
        xnew, ynew = None, None
        if not(dx is None):
            xnew = x + dx
        if not(dy is None):
            ynew = y + dy        
        return self.move(x = xnew, y = ynew, log = log)

    def close(self):
        self._s.close()

    def start_tracking(self):
        """
        Register current position and start tracking it using vampires data
        """
        xvam1, yvam1 = self._get_xyvam1_from_shm()
        self.xvam1_0 = xvam1   
        self.yvam1_0 = yvam1
        x, y = self.get_position()   
        self.xzab_0 = x
        self.yzab_0 = y
        self.tracking = True
        return None
    
    def stop_tracking(self):
        self._tracking = False
        return None
    
    def _get_xyvam2_from_shm(self):
        xvam1, yvam1 = self.vcam1_xy.get_data()
        return xvam1, yvam1   
        
    def run(self):
        """
        start tracking the position on vampies camera
        """
        while not(self.stopped()):
            time.sleep(self.period)
            if self.tracking:
                xvam1, yvam1 = self._get_xyvam1_from_shm()
                # get diff from last position
                dxvam2 = xvam1 - self.xvam1_0
                dyvam2 = yvam1 - self.yvam1_0
                # convert to zaber frame
                xzab, yzab = Geometry.vam1_to_zab(dxvam1, dyvam1)
                print(xzab, yzab)
                #self.move(xzab + self.xzab_0, yzab + self.yzab_0)
        return None        

