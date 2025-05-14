import os
from astropy.io import fits
from scipy.interpolate import griddata
from scipy.optimize import curve_fit
import numpy as np
import csv
import pandas as pd
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
plt.ion()

from datetime import datetime, timezone

TARGET_DIR = "/mnt/datazpool/PL/20250514/firstpl/"

def gaussian_2d(xy, amplitude, xo, yo, sigma, offset):
    """
    Define a 2d gaussian
    """
    x, y = xy
    xo = float(xo)
    yo = float(yo)
    w = 1/(sigma**2)
    g = offset + amplitude * np.exp(-(w*((x-xo)**2) + w*((y-yo)**2)))
    return g.ravel()   




def opti_flux(filename = None) :
    # get the data path from logger if none
    hdu = fits.open(filename)
    xmod = hdu[1].data['xmod']
    ymod = hdu[1].data['ymod']

    # reading the flux
    fluxes = np.mean(hdu[0].data, axis=(1,2))
    xmin, xmax   = np.min(xmod), np.max(xmod)
    ymin, ymax   = np.min(ymod), np.max(ymod)
    # Define the grid for interpolation
    grid_x, grid_y = np.mgrid[xmin:xmax:500j, ymin:ymax:500j]  # 500x500 grid

    # Interpolate the fluxes onto the 
    this_header = fits.getheader(filename, ext=0)
    
    flux_map = griddata((xmod, ymod), fluxes, (grid_x, grid_y), method='cubic')
    # Prepare data for fitting
    z = fluxes
    x = xmod
    y = ymod
    amplitude_0=np.max(fluxes)-np.min(fluxes)
    x_0= x[fluxes.argmax()]
    y_0= y[fluxes.argmax()]
    sigma_0 = (x.max()-x.min())/4
    offset_0=np.min(fluxes)

    # Initial guess for the parameters
    initial_guess = (amplitude_0,x_0,y_0,sigma_0,offset_0)

    # Fit the Gaussian
    try:
        popt, _ = curve_fit(gaussian_2d, (x, y), z, p0=initial_guess)
        x_fit=popt[1]
        y_fit=popt[2]
        amplitude = popt[0]
    except:
        x_fit, y_fit, amplitude = None, None, None
        print("Failed to perform fit")

    return x_fit, y_fit, amplitude


def get_all_modid_four():

    tnow = datetime.now(timezone.utc)
    current_path = format(tnow.strftime("%Y%m%d"))
    #current_path = "20250510"
    source_path = TARGET_DIR

    #Gets all the fits files
    filelist = [source_path + f for f in os.listdir(source_path)
            if os.path.isfile(os.path.join(source_path, f)) and f.lower().endswith('.fits')]
    
    modid_four_files = []
    for file in filelist:
        this_header = fits.getheader(file, ext=0)
        if this_header["X_FIRMID"]==5 and this_header["X_FIRTRG"]=="EXT":
            print(file)
            modid_four_files.append(file)
    
    return modid_four_files

def get_pos_content(files_modid_four):
    xpos_l = []
    ypos_l = []
    xzab_l = []
    yzab_l = []
    amp_l = []
    for file in files_modid_four:
        xpos, ypos, amplitude = opti_flux(file)
        
        this_header = fits.getheader(file, ext=0)

        xzab = this_header["X_FIRZBX"]
        yzab = this_header["X_FIRZBY"]
        xpos_l.append(xpos)
        ypos_l.append(ypos)
        xzab_l.append(xzab)
        yzab_l.append(yzab)
        amp_l.append(amplitude)
    
    return xpos_l, ypos_l, xzab_l, yzab_l, amp_l

def get_pos_in_csv():
    files_modid_four = get_all_modid_four()

    xpos_l, ypos_l, xzab_l, yzab_l, amp_l = get_pos_content(files_modid_four)

    # Combine the lists row-wise using zip
    rows = zip(xpos_l, ypos_l, xzab_l, yzab_l, amp_l)
    headers = ["xpos", "ypos", "xzab", "yzab", "amp"]
    # Write to CSV
    save_here = './output.csv'
    with open(save_here, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(headers)  # write the header
        writer.writerows(rows)    # write the data rows
    print("Done")
    return save_here

#get_pos_in_csv()

data = pd.read_csv("./output.csv")
data = data[data["amp"] > 150]


npoints = len(data)
xpos = np.array(data["xpos"])
ypos = np.array(data["ypos"])
xzab = np.array(data["xzab"])
yzab = np.array(data["yzab"])

fig = plt.figure(figsize=(10, 4))
axpos = fig.add_subplot(121)
axzab = fig.add_subplot(122)

axpos.plot(xpos, ypos, "o--")
axpos.set_xlabel("X position (SG ADU)")
axpos.set_ylabel("Y position (SG ADU)")
axpos.axis("equal")
axpos.set_title("Tip/Tilt")

axzab.plot(xzab, yzab, "o--")
axzab.set_xlabel("X position (steps)")
axzab.set_ylabel("Y position (steps)")
axzab.axis("equal")
axzab.set_title("Zabers")

Y = np.zeros([2*npoints, 1])
Y[0:npoints, 0] = xpos
Y[npoints:, 0] = ypos

A = np.zeros([2*npoints, 6])

A[0:npoints, 0] = xzab
A[0:npoints, 1] = yzab
A[0:npoints, 2] = 1

A[npoints:, 3] = xzab
A[npoints:, 4] = yzab
A[npoints:, 5] = 1

X = np.dot(np.linalg.pinv(A), Y)

Yfit = np.dot(A, X)
axpos.plot(Yfit[:npoints], Yfit[npoints:], "o")

theta_x = np.rad2deg(np.arctan2(X[1], X[0]))[0]
theta_y = np.rad2deg(np.arctan2(X[4], X[3]))[0]

print("Position angle of X: {:.2f}".format(theta_x))
print("Position angle of Y: {:.2f}".format(theta_y))

conversion_name = "sky_to_sg"
suffixes = ["11", "12", "21", "22"]
values = [X[0], X[1], X[3], X[4]]
print(conversion_name+"_origin_x: {}".format(X[2][0]))
print(conversion_name+"_origin_y: {}".format(X[5][0]))
for k in range(len(values)):
    print(conversion_name+"_conversion_matrix_"+suffixes[k]+": {}".format(values[k][0]))


# get origin in zabers
M = np.array([[X[0][0], X[1][0]], [X[3][0], X[4][0]]]) # matrice passage
x0_pos = -X[2][0]
y0_pos = -X[5][0]
z0_zab = np.dot(np.linalg.pinv(M), np.array([[x0_pos], [y0_pos]]))
x0_zab, y0_zab = z0_zab

xax_zab = np.linspace(-1000, 1000, 10) + x0_zab
yax_zab = np.linspace(-1000, 1000, 10) + y0_zab

xax_zab_posx = X[0] * xax_zab + X[1] * y0_zab + X[2]
xax_zab_posy = X[3] * xax_zab + X[4] * y0_zab + X[5]

yax_zab_posx = X[0] * x0_zab + X[1] * yax_zab + X[2]
yax_zab_posy = X[3] * x0_zab + X[4] * yax_zab + X[5]

axpos.plot(xax_zab_posx, xax_zab_posy, "-C3")
axpos.plot(xax_zab_posx[0], xax_zab_posy[0], "oC3")
axpos.plot(yax_zab_posx, yax_zab_posy, "-C2")
axpos.plot(yax_zab_posx[0], yax_zab_posy[0], "oC2")

axzab.plot(xax_zab, yax_zab*0 + y0_zab, "-C3")
axzab.plot(xax_zab[0], y0_zab, "oC3")
axzab.plot(xax_zab*0 + x0_zab, yax_zab, "-C2")
axzab.plot(x0_zab, yax_zab[0], "oC2")



fig.tight_layout()
    

for i in plt.get_fignums():
    fig = plt.figure(i)
    fig.savefig(f"figure_{i}.png")



"""
if __name__ == "__main__":
    print("/(U_U)/")
    
    #path = get_pos_in_csv()
    path = './output.csv'
    fun(path)

    print("\(U_U)/")

"""


    



