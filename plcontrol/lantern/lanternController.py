#coding: utf8
import zmq
from packerUnpacker import PackerUnpacker
import numpy as np
import ruamel.yaml as yaml
import os
import matplotlib as mpl
mpl.use("TkAgg")
import matplotlib.pyplot as plt
import os
plt.ion()

# get path to this file
this_dir = os.path.dirname(os.path.abspath(__file__))

LOADER = yaml.YAML()
CONFIG = LOADER.load(open(this_dir+"/config.yml").read())

# Create a ZMQ context
context = zmq.Context()
ZMQ_TC_ADDRESS = CONFIG["zmq_connection"]["tc_port"]
ZMQ_TM_ADDRESS = CONFIG["zmq_connection"]["tm_port"]

PUNP = PackerUnpacker(config=CONFIG)

def stop():
    ld._driver.stop_receiver()    
    ld._driver.disconnect()

# Create driver object
from lantern import lanternDriver
from lantern import scripts
ld = lanternDriver.LanternDriver(config = CONFIG)
ld._driver.verbose_level = 3
ld._driver.connect()
ld._driver.start() # start the receiver part of the driver

# give a convenient handles to the user
from byt import Byt
db = ld._driver.db

# and script object
scripts = scripts.LanternScripts(ld = ld, db = db)

def panic():
    ld.switch_control_loop(False)
    return None

# define some usefull routines
def plot_open_loop_responses(init_position = None, npoints = 200, decimation = 1, step = [2000, 2000]):
    (counter, microseconds, xcom, ycom, xpos, ypos, xset, yset, xset_shaped, yset_shaped) = scripts.get_open_loop_response(init_position = init_position, step = step, waittime=2, decimation = decimation, npoints = npoints)
    fig = plt.figure(figsize=(12,6))
    ax1 = fig.add_subplot(221)
    ax1.plot((microseconds-microseconds[0])*1e-3, xpos, "C0")
    ax1.plot((microseconds-microseconds[0])*1e-3, xset, "C2", alpha = 0.5)
    ax1.plot((microseconds-microseconds[0])*1e-3, xset_shaped, "C2--", alpha = 0.5)
    ax1.legend(["Position", "Setpoint", "Shaping"])
    ax1.set_xlabel("Time (ms)")
    ax1.set_ylabel("Piezo X-axis position (ADU)")

    ax2 = fig.add_subplot(222)
    ax2.plot((microseconds-microseconds[0])*1e-3, xcom, "C0")
    ax2.legend(["Command"])
    ax2.set_xlabel("Time (ms)")
    ax2.set_ylabel("Piezo X-axis command (ADU)")

    ax3 = fig.add_subplot(223)
    ax3.plot((microseconds-microseconds[0])*1e-3, ypos, "C1")
    ax3.plot((microseconds-microseconds[0])*1e-3, yset, "C3", alpha = 0.5)
    ax3.plot((microseconds-microseconds[0])*1e-3, yset_shaped, "C3--", alpha = 0.5)
    ax3.legend(["Position", "Setpoint", "Shaping"])
    ax3.set_xlabel("Time (ms)")
    ax3.set_ylabel("Piezo Y-axis position (ADU)")

    ax4 = fig.add_subplot(224)
    ax4.plot((microseconds-microseconds[0])*1e-3, ycom, "C1")
    ax4.legend(["Command"])
    ax4.set_xlabel("Time (ms)")
    ax4.set_ylabel("Piezo Y-axis command (ADU)")

    fig.tight_layout()
    return None

def plot_hysteresis(xrange = None, yrange = None, npoints = 50):
    xcom, ycom, xpos, ypos = scripts.get_hysteresis(xrange = xrange, yrange = yrange, npoints = npoints)
    fig = plt.figure(figsize=(6,6))
    ax1 = fig.add_subplot(211)
    line = ax1.plot(xcom, xpos)
    line[0].axes.annotate('',
        xytext=(xcom[npoints//2-1], xpos[npoints//2-1]),
        xy=(xcom[npoints//2+1], xpos[npoints//2+1]),
        arrowprops=dict(arrowstyle="->", color="C0"),
        size=10
    )
    line[0].axes.annotate('',
        xytext=(xcom[npoints+npoints//2-1], xpos[npoints+npoints//2-1]),
        xy=(xcom[npoints+npoints//2+1], xpos[npoints+npoints//2+1]),
        arrowprops=dict(arrowstyle="->", color="C0"),
        size=10
    )    
    ax1.set_xlabel("Piezo X-axis setpoint (ADU)")
    ax1.set_ylabel("Piezo X-axis position (ADU)")

    ax2 = fig.add_subplot(212)
    line = ax2.plot(ycom, ypos, "C1")
    line[0].axes.annotate('',
        xytext=(ycom[npoints//2-1], ypos[npoints//2-1]),
        xy=(ycom[npoints//2+1], ypos[npoints//2+1]),
        arrowprops=dict(arrowstyle="->", color="C1"),
        size=10
    )
    line[0].axes.annotate('',
        xytext=(ycom[npoints+npoints//2-1], ypos[npoints+npoints//2-1]),
        xy=(ycom[npoints+npoints//2+1], ypos[npoints+npoints//2+1]),
        arrowprops=dict(arrowstyle="->", color="C1"),
        size=10
    )
    ax2.set_xlabel("Piezo Y-axis setpoint (ADU)")
    ax2.set_ylabel("Piezo Y-axis position (ADU)")

    fig.tight_layout()
    return None

def plot_noise(iterations = 3):
    xpos, ypos= np.array([]), np.array([])
    for k in range(iterations):
        (_, _, _, _, x, y, _, _, _, _) = scripts.get_open_loop_response(init_position= [0, 0], step = [0, 0], waittime=2)
        xpos = np.concatenate([xpos, x])
        ypos = np.concatenate([ypos, y])
    fig = plt.figure(figsize=(6, 6))
    ax1 = fig.add_subplot(211)
    ax1.hist(xpos, align = "mid", bins=1+int(np.max(xpos)-np.min(xpos)), color="C0", density=True)
    xx = np.linspace(np.min(xpos), np.max(xpos), 100)
    yy = 1.0/np.sqrt(2*np.pi*np.var(xpos))*np.exp(-0.5*(xx-np.mean(xpos))**2/np.std(xpos)**2)
    ax1.plot(xx, yy, "--k", alpha = 0.5)
    ax1.text(np.min(xpos), np.max(yy)/2, "Mean: {:.2f}\nStd: {:.2f}".format(np.mean(xpos), np.std(xpos)))
    ax1.set_xlabel("Piezo position (ADU)")
    ax1.set_ylabel("Occurence rate")

    ax2 = fig.add_subplot(212)
    ax2.hist(ypos, align = "mid", bins=1+int(np.max(ypos)-np.min(ypos)), color="C1", density=True)
    xx = np.linspace(np.min(ypos), np.max(ypos), 100)
    yy = 1.0/np.sqrt(2*np.pi*np.var(ypos))*np.exp(-0.5*(xx-np.mean(ypos))**2/np.std(ypos)**2)
    ax2.plot(xx, yy, "--k", alpha = 0.5)    
    ax2.set_xlabel("Piezo position (ADU)")
    ax2.set_ylabel("Occurence rate")
    ax2.text(np.min(ypos), np.max(yy)/2, "Mean: {:.2f}\nStd: {:.2f}".format(np.mean(ypos), np.std(ypos)))
    ax2.plot()
    fig.tight_layout()
    return None

def get_piezo_com_to_sg_calibration():
    """
    Attempt to calibrate the piezo command ADU to piezo position (um) calibrations factors
    """
    npoints = 20
    (xcom, ycom, xpos, ypos) = scripts.get_hysteresis(npoints = npoints, xrange=(5000, 25000), yrange=(5000, 25000))
    A = np.array([xpos, np.ones(2*npoints)]).T
    X = np.dot(np.linalg.pinv(A), xcom)
    xcom_fit = np.dot(A, X)[0:npoints]
    A = np.array([ypos, np.ones(2*npoints)]).T
    Y = np.dot(np.linalg.pinv(A), ycom)
    ycom_fit = np.dot(A, Y)[0:npoints]
    print("Got calibraton:")
    print("sg_in_com_origin_x: {}".format(X[1]))
    print("sg_in_com_origin_y: {}".format(Y[1]))    
    print("sg_to_com_conversion_matrix_11: {}".format(X[0]))
    print("sg_to_com_conversion_matrix_12: {}".format(0))
    print("sg_to_com_conversion_matrix_21: {}".format(0))
    print("sg_to_com_conversion_matrix_22: {}".format(Y[0]))
    fig = plt.figure(figsize=(6,6))
    ax1 = fig.add_subplot(211)
    ax1.plot(xcom_fit, xpos[0:npoints], "C0--")
    line = ax1.plot(xcom, xpos)
    line[0].axes.annotate('',
        xytext=(xcom[npoints//2-1], xpos[npoints//2-1]),
        xy=(xcom[npoints//2+1], xpos[npoints//2+1]),
        arrowprops=dict(arrowstyle="->", color="C0"),
        size=10
    )
    line[0].axes.annotate('',
        xytext=(xcom[npoints+npoints//2-1], xpos[npoints+npoints//2-1]),
        xy=(xcom[npoints+npoints//2+1], xpos[npoints+npoints//2+1]),
        arrowprops=dict(arrowstyle="->", color="C0"),
        size=10
    )    
    ax1.set_xlabel("Piezo command (ADU)")
    ax1.set_ylabel("Piezo position (ADU)")

    ax2 = fig.add_subplot(212)
    ax2.plot(ycom_fit, ypos[0:npoints], "C1--")
    line = ax2.plot(ycom, ypos, "C1")
    line[0].axes.annotate('',
        xytext=(ycom[npoints//2-1], ypos[npoints//2-1]),
        xy=(ycom[npoints//2+1], ypos[npoints//2+1]),
        arrowprops=dict(arrowstyle="->", color="C1"),
        size=10
    )
    line[0].axes.annotate('',
        xytext=(ycom[npoints+npoints//2-1], ypos[npoints+npoints//2-1]),
        xy=(ycom[npoints+npoints//2+1], ypos[npoints+npoints//2+1]),
        arrowprops=dict(arrowstyle="->", color="C1"),
        size=10
    )
    ax2.set_xlabel("Piezo command (ADU)")
    ax2.set_ylabel("Piezo position (ADU)")

    return None
    

def plot_data(**kwargs):
    (counter, microseconds, xcom, ycom, xpos, ypos, xset, yset, xset_shaped, yset_shaped) = scripts.get_dataset(**kwargs)
    fig = plt.figure(figsize=(12,6))
    ax1 = fig.add_subplot(221)
    ax1.plot((microseconds-microseconds[0])*1e-3, xpos, "C0")
    ax1.plot((microseconds-microseconds[0])*1e-3, xset, "C2", alpha = 0.5)
    ax1.plot((microseconds-microseconds[0])*1e-3, xset_shaped, "C2--", alpha = 0.5)
    ax1.legend(["Position", "Setpoint", "Shaping"])
    ax1.set_xlabel("Time (ms)")
    ax1.set_ylabel("Piezo X-axis position (ADU)")

    ax2 = fig.add_subplot(222)
    ax2.plot((microseconds-microseconds[0])*1e-3, xcom, "C0")
    ax2.legend(["Command"])
    ax2.set_xlabel("Time (ms)")
    ax2.set_ylabel("Piezo X-axis command (ADU)")

    ax3 = fig.add_subplot(223)
    ax3.plot((microseconds-microseconds[0])*1e-3, ypos, "C1")
    ax3.plot((microseconds-microseconds[0])*1e-3, yset, "C3", alpha = 0.5)
    ax3.plot((microseconds-microseconds[0])*1e-3, yset_shaped, "C3--", alpha = 0.5)
    ax3.legend(["Position", "Setpoint", "Shaping"])
    ax3.set_xlabel("Time (ms)")
    ax3.set_ylabel("Piezo Y-axis position (ADU)")

    ax4 = fig.add_subplot(224)
    ax4.plot((microseconds-microseconds[0])*1e-3, ycom, "C1")
    ax4.legend(["Command"])
    ax4.set_xlabel("Time (ms)")
    ax4.set_ylabel("Piezo Y-axis command (ADU)")

    fig.tight_layout()
    return None


def hexagon(npoints = 11):
    xmod = []
    ymod = []
    y = np.linspace(-1, 1, npoints)
    x = np.linspace(-np.sqrt(4/3), np.sqrt(4/3), npoints)
    xx, yy = np.meshgrid(x, y)
    for k in range(0, npoints, 2):
        xx[k, :] = -(xx[k, :]+(x[1]-x[0])/2)
    for k in range(npoints):
        for l in range(npoints):
            if xx[k, l]**2 + yy[k, l]**2 <= 1:
                xmod.append(xx[k, l])
                ymod.append(yy[k, l])
    return xmod, ymod
