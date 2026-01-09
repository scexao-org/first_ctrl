#coding: utf8

def init(lanternDriver_handle = None, camera_handle = None, fcam_handle = None, scripts_handle = None, database_handle = None, config_handle = None, zabers_handle = None):
    global ld
    global cam
    global fcam
    global scripts
    global db            
    global config
    global zab
    ld = lanternDriver_handle
    cam = camera_handle
    fcam = fcam_handle
    scripts = scripts_handle
    db = database_handle
    config = config_handle
    zab = zabers_handle
    return None
