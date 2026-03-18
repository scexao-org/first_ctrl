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
    
    @staticmethod
    def circle(npoints):
        angles = np.linspace(0, 2*np.pi, npoints, endpoint=False)
        xmod = np.cos(angles)
        ymod = np.sin(angles)
        return xmod, ymod

    @staticmethod
    def crenels(Radius, angle_deg):

        # Radius = 14 # 556
        # Radius = 13 # 500
        # Radius = 12 # 428
        # Radius = 11 # 380
        # Radius = 10 # 316
        # Radius = 9 # 276
        # Radius = 8 # 220
        # Radius = 7 # 188 --< 3.4 mas @ 25 mas radius
        # Radius = 6 # 140
        # Radius = 5 # 116
        # Radius = 4 # 76
        # Radius = 3 # 60 --< 5.4 mas @ 25 mas radius


        def add_N_crenele(positions, N, reverse=False):
            xy = [[0, 1], [1, 1], [1, 0], [2, 0]]
            xy = np.array(xy)
            if reverse:
                xy[:,0] = -xy[:,0]
            for i in range(N):
                # print(positions[-1])
                positions = np.concatenate((positions, xy + positions[-1]), axis=0)
            return positions

        def add_side(positions, reverse=False):
            xy = [[0, 1], [1, 1], [1, 2], [0, 2]]
            xy = np.array(xy)
            if reverse:
                xy[:,0] = -xy[:,0]
            positions = np.concatenate((positions, xy + positions[-1]), axis=0)
            return positions

        positions = np.array([[-Radius-1,0.5],[-Radius,0.5]]) 
        reverse = False
        while positions[-1,1] < Radius:
            print(positions[-1])
            if not reverse:
                while positions[-1,0]+positions[-1,1]  < Radius:
                    positions = add_N_crenele(positions, 1, reverse)
            else:
                while positions[-1,0]-positions[-1,1] > -Radius:
                    positions = add_N_crenele(positions, 1, reverse)
            positions = add_side(positions, reverse)
            reverse=not reverse

        positions[-2,1] -= 2
        positions[-1,1] -= 2

        if reverse:
            positions[-1,0] += 2
        else:
            positions[-1,0] -= 2

        positions_2 = positions.copy()
        positions_2[:,1] = -positions_2[:,1]
        positions = np.concatenate((positions_2[::-1], positions), axis=0)

        # Rotate positions by 45 np.degrees
        angle = np.deg2rad(angle_deg)
        rotation_matrix = np.array([
            [np.cos(angle), -np.sin(angle)],
            [np.sin(angle), np.cos(angle)]
        ])
        positions = positions @ rotation_matrix.T

        max_pos = positions.max()
        positions/= max_pos

        xmod, ymod = positions[:,0], positions[:,1]
        return xmod, ymod
