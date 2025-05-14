#coding: utf8
import numpy as np

_zab_to_tt_origin = np.array([-10477.919349999765, -20227.281649999986]) 

_zab_to_tt_mat = np.array([[0.09397099999915978, 0.007182100000496333],
                           [-0.00554900000161867, 0.12482190000095877]])

_vam2_to_tt_mat = np.array([[1, 0.0],
                            [-0.0, 1.0]])

_tt_to_zab_mat = np.linalg.inv(_zab_to_tt_mat)
_tt_to_vam2_mat = np.linalg.inv(_vam2_to_tt_mat)

_zab_to_vam2_mat = np.dot(_tt_to_vam2_mat, _zab_to_tt_mat)
_vam2_to_zab_mat = np.dot(_tt_to_zab_mat, _vam2_to_tt_mat)

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
    def tt_to_vam2(x, y):
        tt = np.array([[x], [y]])
        vam2 = np.dot(_tt_to_vam2_mat, tt)
        x, y = vam2[0, 0], vam2[1, 0]
        return (x, y)
 
    @staticmethod
    def vam2_to_tt(x, y):
        vam2 = np.array([[x], [y]])
        tt = np.dot(_vam2_to_tt_mat, vam2)
        x, y = tt[0, 0], tt[1, 0]
        return (x, y)    
    
    @staticmethod
    def zab_to_vam2(x, y):
        zab = np.array([[x], [y]])
        vam2 = np.dot(_zab_to_vam2_mat, zab)
        x, y = vam2[0, 0], vam2[1, 0]
        return (x, y)
 
    @staticmethod
    def vam2_to_zab(x, y):
        vam2 = np.array([[x], [y]])
        zab = np.dot(_vam2_to_zab_mat, vam2)
        x, y = zab[0, 0], zab[1, 0]
        return (x, y) 