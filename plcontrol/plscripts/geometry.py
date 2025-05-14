#coding: utf8
import numpy as np

_zab_to_tt_origin = np.array([-17070.65, -7532.78]) 

_zab_to_tt_mat = np.array([[-0.00693861903826579, 0.1069994196338608],
                           [0.059796088370664094, 0.009944617042710019]])

_vam1_to_tt_mat = np.array([[1, 0.0],
                            [-0.0, 1.0]])

_tt_to_zab_mat = np.linalg.inv(_zab_to_tt_mat)
_tt_to_vam1_mat = np.linalg.inv(_vam2_to_tt_mat)

_zab_to_vam1_mat = np.dot(_tt_to_vam1_mat, _zab_to_tt_mat)
_vam1_to_zab_mat = np.dot(_tt_to_zab_mat, _vam1_to_tt_mat)

class Geometry(object):
    """
    A class with methods convert coordinates from one frame to another
    """
    def __init__(self, *args, **kwargs):
        super(Geometry, self).__init__(*args, **kwargs)

    @staticmethod
    def zab_to_tt(x, y):
        zab = np.array([[x], [y]])
        tt = np.dot(_zab_to_tt_mat, zab)
        x, y = tt[0, 0], tt[1, 0]
        return (x, y)
 
    @staticmethod
    def tt_to_zab(x, y):
        tt = np.array([[x], [y]])
        zab = np.dot(_tt_to_zab_mat, tt)
        x, y = zab[0, 0], zab[1, 0]
        return (x, y)
    
    @staticmethod
    def tt_to_vam1(x, y):
        tt = np.array([[x], [y]])
        vam1 = np.dot(_tt_to_vam1_mat, tt)
        x, y = vam1[0, 0], vam1[1, 0]
        return (x, y)
 
    @staticmethod
    def vam1_to_tt(x, y):
        vam1 = np.array([[x], [y]])
        tt = np.dot(_vam1_to_tt_mat, vam1)
        x, y = tt[0, 0], tt[1, 0]
        return (x, y)    
    
    @staticmethod
    def zab_to_vam1(x, y):
        zab = np.array([[x], [y]])
        vam1 = np.dot(_zab_to_vam1_mat, zab)
        x, y = vam1[0, 0], vam1[1, 0]
        return (x, y)
 
    @staticmethod
    def vam1_to_zab(x, y):
        vam1 = np.array([[x], [y]])
        zab = np.dot(_vam1_to_zab_mat, vam1)
        x, y = zab[0, 0], zab[1, 0]
        return (x, y) 
