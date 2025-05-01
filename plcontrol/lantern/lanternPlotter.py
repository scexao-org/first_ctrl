#coding: utf8
from byt import Byt
import zmq
from lantern.packerUnpacker import PackerUnpacker
import time
from lantern.utils import StoppableThread
import numpy as np
from mpl_toolkits.axes_grid1.inset_locator import zoomed_inset_axes
from mpl_toolkits.axes_grid1.inset_locator import mark_inset
import matplotlib
matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
plt.ion()

context = zmq.Context()

SG_TO_AS = 1
MIDPOINT = [2478, 2575]
RANGE = [500, 500]

class FigureResponse():
    def __init__(self, nmax = 1000):
        self.fig = plt.figure(figsize = (8, 4))
        self.ax1 = self.fig.add_subplot(211)
        self.ax2 = self.fig.add_subplot(212)        
        self.timer = self.fig.canvas.new_timer(interval=500)
        mng = self.fig.canvas.manager        
        mng.window.show()
        self.nmax = nmax
        self.stop=False
        self.init_plot()
        return None

    def init_plot(self):
        self.ax1.plot([], [], "-C0")
        self.ax1.plot([], [], "-C2")
        self.ax1.set_xlabel("Time (s)")
        self.ax1.set_ylabel("X Piezo (as)")
        self.ax1.set_ylim((MIDPOINT[0]-RANGE[0]/2)*SG_TO_AS, (MIDPOINT[0]+RANGE[0]/2)*SG_TO_AS)
        self.ax1.legend(["Position", "Setpoint"])        
        self.ax2.plot([0], [0], "-C1", alpha = 1)
        self.ax2.plot([0], [0], "-C3", alpha = 1)        
        self.ax2.set_xlabel("Time (s)")
        self.ax2.set_ylabel("Y Piezo (as)")
        self.ax2.set_ylim((MIDPOINT[1]-RANGE[1]/2)*SG_TO_AS, (MIDPOINT[1]+RANGE[1]/2)*SG_TO_AS)
        self.ax2.legend(["Position", "Setpoint"])
        self.fig.tight_layout()
        return None

    def run(self, controlData):
        if self.stop==True:
            data.stop=True
            self.timer.stop()
        if len(controlData.counter > self.nmax):
            controlData.counter = controlData.counter[-self.nmax:]
            controlData.microseconds = controlData.microseconds[-self.nmax:]
            controlData.xpos = controlData.xpos[-self.nmax:]
            controlData.ypos = controlData.ypos[-self.nmax:]
            controlData.xcom = controlData.xcom[-self.nmax:]
            controlData.ycom = controlData.ycom[-self.nmax:]
            controlData.xset = controlData.xset[-self.nmax:]
            controlData.yset = controlData.yset[-self.nmax:]
        self.ax1.lines[0].set_data(controlData.microseconds/1e6, controlData.xpos*SG_TO_AS)
        self.ax1.lines[1].set_data(controlData.microseconds/1e6, controlData.xset*SG_TO_AS)        
        self.ax2.lines[0].set_data(controlData.microseconds/1e6, controlData.ypos*SG_TO_AS)
        self.ax2.lines[1].set_data(controlData.microseconds/1e6, controlData.yset*SG_TO_AS)
        if len(controlData.microseconds) > 0:
            self.ax1.set_xlim(np.min(controlData.microseconds)/1e6, np.max(controlData.microseconds)/1e6)
            self.ax2.set_xlim(np.min(controlData.microseconds)/1e6, np.max(controlData.microseconds)/1e6)        
        self.fig.canvas.draw()
        return None

class FigureXY():
    def __init__(self, nmax = 1000):
        self.fig = plt.figure(figsize = (5, 5))
        self.ax = self.fig.add_subplot(111)
        self.timer = self.fig.canvas.new_timer(interval=500)
        mng = self.fig.canvas.manager        
        mng.window.show()
        self.nmax = nmax
        self.stop=False
        self.init_plot()
        self.fig.tight_layout()
        return None

    def init_plot(self):
        self.ax.plot([0], [0], "o-C0", alpha = 0.1)
        self.ax.set_xlabel("X Position (arcsec)")
        self.ax.set_ylabel("Y Position (arcsec)")
        self.ax.set_xlim((MIDPOINT[0]-RANGE[0]/2)*SG_TO_AS, (MIDPOINT[0]+RANGE[0]/2)*SG_TO_AS)
        self.ax.set_ylim((MIDPOINT[1]-RANGE[1]/2)*SG_TO_AS, (MIDPOINT[1]+RANGE[1]/2)*SG_TO_AS)
        self.axins = zoomed_inset_axes(self.ax, 15, loc=1)
        self.axins.plot([0], [0], "o-C0", alpha = 0.1)
        self.axins.set_xlim((MIDPOINT[0]-RANGE[0]/100)*SG_TO_AS, (MIDPOINT[0]+RANGE[0]/100)*SG_TO_AS)
        self.axins.set_ylim((MIDPOINT[1]-RANGE[1]/100)*SG_TO_AS, (MIDPOINT[1]+RANGE[1]/100)*SG_TO_AS)
        mark_inset(self.ax, self.axins, loc1=2, loc2=4, fc="none", ec="0.5")
        return None

    def run(self, controlData):
        if self.stop==True:
            data.stop=True
            self.timer.stop()
        if len(controlData.counter > self.nmax):
            controlData.counter = controlData.counter[-self.nmax:]
            controlData.microseconds = controlData.microseconds[-self.nmax:]
            controlData.xpos = controlData.xpos[-self.nmax:]
            controlData.ypos = controlData.ypos[-self.nmax:]
            controlData.xcom = controlData.xcom[-self.nmax:]
            controlData.ycom = controlData.ycom[-self.nmax:]
            controlData.xset = controlData.xset[-self.nmax:]
            controlData.yset = controlData.yset[-self.nmax:]
        self.ax.lines[0].set_data(controlData.xpos*SG_TO_AS, controlData.ypos*SG_TO_AS)
        self.axins.lines[0].set_data(controlData.xpos*SG_TO_AS, controlData.ypos*SG_TO_AS)        
        self.fig.canvas.draw()
        return None


class ControlData():
    def __init__(self):
        self.counter = np.array([])
        self.microseconds = np.array([])
        self.xpos = np.array([])
        self.ypos = np.array([])
        self.xcom = np.array([])
        self.ycom = np.array([])
        self.xset = np.array([])
        self.yset = np.array([])                
        self.stop=False
        return None
    
    def add_packet(self, packet):
        self.counter = np.concatenate([self.counter, packet["counter"]])
        self.microseconds = np.concatenate([self.microseconds, packet["microseconds"]])
        self.xpos = np.concatenate([self.xpos, packet["xpos"]])
        self.ypos = np.concatenate([self.ypos, packet["ypos"]])
        self.xco = np.concatenate([self.xcom, packet["xcom"]])
        self.ycom = np.concatenate([self.ycom, packet["ycom"]])
        self.xset = np.concatenate([self.xset, packet["xset"]])
        self.yset = np.concatenate([self.yset, packet["yset"]])                        
        return None        

class DataReceiver(StoppableThread):
    def __init__(self, config = None, verbose_level = 0, **kwargs):
        super(DataReceiver, self).__init__(**kwargs)
        if config is None:
            raise Exception("please provide a valid configuration dictionnary")
        self.config = config        
        self.connected = False
        self.controlData = ControlData()
        self.punp = PackerUnpacker(config = config)        
        return None

    def connect(self):
        if self.connected:
            print("Already connected!")
        # open the port for sending TC    
        self.tm_receiver = context.socket(zmq.SUB)
        self.tm_receiver.connect(self.config["zmq_connection"]["tm_port"])
        self.tm_receiver.subscribe("")          
        self.connected = True  
        return None

    def disconnect(self):
        if not(self.connected):
            print("Not connected")
            return None
        self.tm_receiver.close()
        self.connected = False
        return None
    
    def process_tm(self, tm):
        try:
            packet = self.punp.unpack(Byt(tm))
            crc_status = self.punp.check_crc(packet)
            print("Got packet of type {} and CRC {}".format(packet["header"]["packet_type"], crc_status))
            if packet["header"]["packet_type"] == 1:
                self.controlData.add_packet(packet["data"])
            else:
                pass
        except Exception as e:
            print(e)
            print("Got TM but unpack failed or cannot calculate CRC")
        return None        
        
    def run(self):
        while not(self.stopped()):
            time.sleep(0.1) # breathing room
            try:
                tm = self.tm_receiver.recv(zmq.NOBLOCK)
                self.process_tm(tm)                
            except zmq.ZMQError as e:
                if e.errno == zmq.EAGAIN:
                    pass # no message was ready (yet!)
        print("DataReceiver has stopped")
        return None


def stop():
    dataReceiver.stop()
    xyFigure.timer.stop()

if __name__ == "__main__":
    from ruamel import yaml
    import os

    # get path to this file
    this_dir = os.path.dirname(os.path.abspath(__file__))
    
    LOADER = yaml.YAML()
    CONFIG = LOADER.load(open(this_dir+"/config.yml").read())        

    dataReceiver = DataReceiver(config = CONFIG)
    dataReceiver.connect()    
    dataReceiver.start()
   
    xyFigure = FigureXY(nmax = 10000)
    xyFigure.timer.add_callback(xyFigure.run, dataReceiver.controlData)
    xyFigure.timer.start()

    figureResponse = FigureResponse(nmax = 10000)
    figureResponse.timer.add_callback(figureResponse.run, dataReceiver.controlData)
    figureResponse.timer.start()    

    def on_close(event):
        xyFigure.timer.stop()
        figureResponse.timer.stop()        
        plt.close('all')
        stop()        
    
    xyFigure.fig.canvas.mpl_connect('close_event', on_close)
    figureResponse.fig.canvas.mpl_connect('close_event', on_close)    

    plt.show()
    plt.pause(0.01)    
    

        
