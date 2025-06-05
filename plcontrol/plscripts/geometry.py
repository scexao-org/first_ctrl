#coding: utf8
import numpy as np

_zab_to_tt_origin = np.array([-23397.642555913924, -15442.522318264728]) 

_zab_to_tt_mat = np.array([[-0.005972608379818009, 0.14357585101031123],
                           [0.14734139219990922, 0.004982134168408588]])

_vam1_to_tt_mat = np.array([[5.95, 0.0],
                            [-0.0, 5.95]])

_tt_to_zab_mat = np.linalg.inv(_zab_to_tt_mat)
_tt_to_vam1_mat = np.linalg.inv(_vam1_to_tt_mat)

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
