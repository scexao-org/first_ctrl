#coding: utf8
#%%
import numpy as np
# import matplotlib
# matplotlib.use('macosx')
from matplotlib import pyplot as plt
plt.ion()

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


    @staticmethod
    def triangle_modulation(radius=1, small=True , size = 1):

        def add_1_position(position,orientation):
            next_position = np.array((np.cos(orientation*np.pi/180), np.sin(orientation*np.pi/180)))
            next_position += position[-1]
            position= np.append(position,next_position[None],axis=0)
            return position

        def add_n_position(n,position,orientation):
            for n in range(n):
                position = add_1_position(position,orientation)
            return position, orientation

        def add_triangle(position,orientation,rotate=120):

            position, orientation = add_n_position(1,position,orientation)
            orientation += rotate 
            position, orientation = add_n_position(2,position,orientation)
            orientation -= 120 
            position, orientation   = add_n_position(2,position,orientation)
            orientation -= 120 
            position, orientation = add_n_position(1,position,orientation)
            orientation += 60 
            return position,orientation

        def add_triangle_peak(position,orientation, rotate=120):
            position, orientation = add_n_position(1,position,orientation)
            orientation += rotate
            position, orientation = add_n_position(2,position,orientation)
            orientation -= 120 
            position, orientation = add_n_position(1,position,orientation)
            orientation -= 60 
            position, orientation = add_n_position(1,position,orientation)
            orientation += 120
            position, orientation = add_n_position(1,position,orientation)
            return position,orientation

        def add_crenal(position,orientation, rotate = 120, last = False):
            position, orientation = add_n_position(1,position,orientation)
            position, orientation = add_n_position(2,position,orientation+rotate)
            position, orientation = add_n_position(1,position,orientation +120)
            position, orientation = add_n_position(1,position,orientation +60)
            position, orientation = add_n_position(2,position,orientation -120)
            position, orientation = add_n_position(2,position,orientation -120)
            position, orientation = add_n_position(1,position,orientation +120)
            if not last:
                position, orientation = add_n_position(1,position,orientation +60)
                position, orientation = add_n_position(1,position,orientation -120)
                position, orientation = add_n_position(2,position,orientation +120)
                position, orientation = add_n_position(1,position,orientation +120)
                orientation -=60
            else:
                position, orientation = add_n_position(2,position,orientation +60)
                position, orientation = add_n_position(1,position,orientation -60)
                position, orientation = add_n_position(2,position,orientation -120)
                orientation +=120

            return position,orientation

        def add_crenal_long(position,orientation, rotate = 0, last = False):
            position,orientation = add_crenal(position,orientation, rotate=rotate, last=True)
            position, orientation = add_n_position(1,position,orientation +0)
            position, orientation = add_n_position(2,position,orientation +60)
            position, orientation = add_n_position(1,position,orientation -120)
            position, orientation = add_n_position(1,position,orientation -60)
            position, orientation = add_n_position(1,position,orientation +120)
            position, orientation = add_n_position(2,position,orientation +60)
            position, orientation = add_n_position(1,position,orientation +120)
            orientation -=60

            return position,orientation


        position = np.zeros((1,2))
        orientation = 0

        position,orientation = add_triangle(position,orientation,rotate=0)
        for n in range(4):
            position,orientation = add_triangle(position,orientation)
        if size == 1:
            position,orientation = add_triangle(position,orientation)
        else:
            position,orientation = add_triangle_peak(position,orientation)

            position,orientation = add_crenal(position,orientation, rotate=60)
            for n in range(4):
                position,orientation = add_crenal(position,orientation, rotate=-120)

            if size == 2:
                position,orientation = add_crenal(position,orientation, rotate=-120)
            else:
                position,orientation = add_crenal(position,orientation, rotate=-120, last=True)

                position,orientation = add_crenal_long(position,orientation, rotate=0)
                for n in range(4):
                    position,orientation = add_crenal_long(position,orientation, rotate=-120)
                if size == 3:
                    position,orientation = add_crenal_long(position,orientation, rotate=-120)
                else:
                    return None


        max_pos = np.abs(position).max() 
        position/= max_pos * radius

        xmod, ymod = position[:, 0], position[:, 1]
        print("Modulation contains {} points".format(len(xmod)))
        return xmod, ymod

# position = add_1_position(position,orientation)
if __name__ == "__main__":

    mod = Modulation()
    # Hexagonal grid
    def hexagonal_grid(radius=1, spacing=0.2):
        """
        Generate a hexagonal (triangular lattice) grid centered on zero, traced as a
        continuous boustrophedon line (each row scanned in alternating direction).
        """
        row_height = spacing * np.sqrt(3) / 2
        n_rows = int(np.floor(radius / row_height))

        hex_points = []
        for j in range(-n_rows, n_rows + 1):
            y = j * row_height
            # offset every other row by half a spacing for the hexagonal pattern
            x_offset = (spacing / 2) if (j % 2) else 0.0
            n_cols = int(np.floor((radius + spacing) / spacing))
            xs = np.arange(-n_cols, n_cols + 1) * spacing + x_offset
            # keep points within the circular aperture
            xs = xs[xs**2 + y**2 <= radius**2]
            # reverse every other row so the points form a connected snake line
            if j % 2:
                xs = xs[::-1]
            for x in xs:
                hex_points.append([x, y])

        hex_points = np.array(hex_points)
        return hex_points

    hex_grid = hexagonal_grid(radius=10, spacing=1)
    xmod, ymod = mod.triangle_modulation(size=3)
    position = np.column_stack((xmod, ymod))

    plt.figure(4, clear=True)
    # plt.plot(hex_grid[:, 0], hex_grid[:, 1], 'o', label='Hexagonal Grid')

    plt.plot(*position.T,'o-')
    plt.gca().set_aspect('equal')
    plt.legend()
# %%
