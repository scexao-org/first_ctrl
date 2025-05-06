#coding: utf8
from plscripts.base import Base
import numpy as np
from astropy.io import fits
from pyMilk.interfacing.isio_shmlib import SHM as shm
from scipy.ndimage import affine_transform
import peakutils

def cent_rot(im, rot, rotation_center):
    '''
    cen_rot - takes a cube of images im, and a set of rotation angles in rot,
    and translates the middle of the frame with a size dim_out to the middle of
    a new output frame with an additional rotation of rot.
    '''
    # converting rotation to radians
    a = np.radians(rot)
    # make a rotation matrix
    transform = np.array([[np.cos(a),-np.sin(a)],[np.sin(a),np.cos(a)]])[:,:]
    # calculate total offset for image output
    c_in = rotation_center#center of rotation
    # c_out has to be pre-rotated to make offset correct
    offset = np.dot(transform, -c_in) + c_in
    offset = (offset[0], offset[1],)
    # perform the transformation
    dst = affine_transform(im, transform, offset=offset)
    return dst


class Tracker(Base):
    def __init__(self, *args, **kwargs):
        super(Tracker, self).__init__(*args, **kwargs)
        # load shared memories
        self.im_io = shm('firstpl')
        self.dark = shm('firstpl_dark')

    def get_shm_flux(self):
        im_data = self.im_io.get_data()
        dark_data = self.dark.get_data()
        img = np.float32(im_data)-np.float32(dark_data)
        img = cent_rot(img,0.3,np.array((int(img.shape[0]/2.),int(img.shape[1]/2.))))
        sum_out = np.sum(img, axis=1)
        # detect the positions of traces
        detectedOutPeaks = peakutils.peak.indexes(sum_out,thres=0.05, min_dist=1)
        # prep and fill trace boxes
        outputs = np.zeros([38,8,img.shape[1]])
        for i in np.arange(38):
            outputs[i] = img[detectedOutPeaks[i]-4:detectedOutPeaks[i]+4,:]
        out_spectra = np.sum(outputs, 1)
        flux = np.sum(out_spectra,axis=0)
        return flux
