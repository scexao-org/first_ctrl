#coding: utf8
import threading

class StoppableThread(threading.Thread):
    """ Just an extension of Thread which can be stopped """
    def __init__(self,  *args, **kwargs):
        super(StoppableThread, self).__init__(*args, **kwargs)
        self._stop_event = threading.Event()
    def stop(self):
        self._stop_event.set()
    def stopped(self):
        return self._stop_event.is_set()

