#coding: utf8
import numpy as np


class Modulation(object):
    """
    A class to contain functions to generate modulation patterns
    """
    def __init__(self, *args, **kwargs):
        return None
    
    @staticmethod
    def _loopit(xmod, ymod):
        """
        double the length of the modulation to go back to beginning
        """
        xmod_loop = np.concatenate([xmod, xmod[::-1]])
        ymod_loop = np.concatenate([ymod, ymod[::-1]])
        return xmod_loop, ymod_loop

    @staticmethod
    def hexagon(radius = None, npoints = None, loopit = False):
        """
        return an hexagon pattern defined by a given number of points along the diameter
        and the given radius length
        """
        if (radius is None) or (npoints is None):
            raise Exception("npoints and radius are required")
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
                    xmod.append(xx[k, l] * radius)
                    ymod.append(yy[k, l] * radius)
        if loopit:
            xmod, ymod = Modulation._loopit(xmod, ymod)
        if len(xmod) > 625:
            print("Warning: this modulation contains {} points which is above the acceptable limit of 625.".format(len(xmod)))
        return xmod, ymod

    @staticmethod
    def raster(radius = None, npoints = None, loopit = False, primaryAxis = "x"):
        """
        A raster scan of given radius (i.e. half-width), with npoints along each dimension
        """
        if (radius is None) or (npoints is None) or not(primaryAxis.lower() in ["x", "y"]):
            raise Exception("radius and npoints are required. primaryAxis should be 'x' or 'y'.")
        x, y = radius * np.linspace(-1, 1, npoints), radius * np.linspace(-1, 1, npoints)
        if primaryAxis.lower() == "x":
            xx, yy = np.meshgrid(x, y)
        else:
            yy, xx = np.meshgrid(x, y)
        xmod, ymod = xx.flatten(), yy.flatten()
        if loopit:
            xmod, ymod = Modulation._loopit(xmod, ymod)
        if len(xmod) > 625:
            print("Warning: this modulation contains {} points which is above the acceptable limit of 625.".format(len(xmod)))
        return xmod, ymod

