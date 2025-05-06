#coding: utf8

def init(lanternDriver_handle = None, camera_handle = None, scripts_handle = None, database_handle = None, config_handle = None):
    global ld
    global cam
    global scripts
    global db            
    global config
    ld = lanternDriver_handle
    cam = camera_handle
    scripts = scripts_handle
    db = database_handle
    config = config_handle
    return None
