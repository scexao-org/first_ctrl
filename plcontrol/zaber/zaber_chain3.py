#!/usr/bin/env python
import serial
import os
import time
import sys
home = os.getenv('HOME')
sys.path.append(home+'/src/lib/python/')
import zaber.logit as logit #Custom logging library

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

class Zaber:
    def __init__(self):
        self._s = None

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
        return None

    def get_position(self):
        """
        Return the x,y position of the zabers in steps
        """
        x = self._status(ZAB_X_IND)
        y = self._status(ZAB_Y_IND)
        return x, y

    def close(self):
        self._s.close()
