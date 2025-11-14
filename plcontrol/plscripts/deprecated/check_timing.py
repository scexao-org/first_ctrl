#coding: utf8
import numpy as np
from astropy.io import fits
import glob
import datetime
import matplotlib.pyplot as plt
plt.ion()

datadir = "/mnt/datazpool/PL/20250515/firstpl/"

filenames = glob.glob(datadir+"/*.txt")
filenames.sort()

filtered = []

start = datetime.time(8, 58, 0)
end = datetime.time(9, 3, 0)

for k in range(len(filenames)):
    print("{}/{}".format(k+1, len(filenames)))
    filename = filenames[k]
    hh, mm, ss = filename.split("firstpl_")[1].split(".")[0].split(":")
    t = datetime.time(int(hh), int(mm), int(ss))
    if (t < start) or (t > end) :
        continue
    hdr = fits.open(filename.replace(".txt", ".fits"))[0].header
    if hdr["X_FIRTRG"] == "EXT":
        filtered.append(filename)

tlog = []
tacq = []

for filename in filtered:
    tlog.append(np.loadtxt(filename)[:, 3])
    tacq.append(np.loadtxt(filename)[:, 4])

tlog = np.concatenate(tlog)
tacq = np.concatenate(tacq)

plt.figure()
plt.plot(tlog, ".-")
plt.plot(tacq, ".-")
for k in range(len(filtered)):
    plt.plot([595*k, 595*k], [np.min(tlog), np.max(tlog)], "-k", alpha = 0.4)

