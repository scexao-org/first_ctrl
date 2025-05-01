#coding: utf8
from byt import Byt
import zmq
from packerUnpacker import PackerUnpacker
import time
from listener import StoppableThread

context = zmq.Context()

class TC(object):
    """ a simple object to represent a tc and its acks/replies """
    def __init__(self, tc_dict, *args, **kwargs):
        self.packet = tc_dict
        self.command_id = tc_dict["data"]["command_id"]
        self.packet_id = tc_dict["header"]["packet_id"]
        self.eack = None
        self.reply = []
        return None
    
    def attach_packet(self, packet, is_ack = False, is_reply = False):
        if is_ack:
            self.eack = packet            
        if is_reply:
            self.reply.append(packet)         
        return None


class Db(object):
    """ a simple object to represent a tm/tc database which can associate acks/replies to tcs """
    def __init__(self, *args, **kwargs):
        self.tcs = []
        self.tms = []
        return None
    
    def push_tm(self, packet, is_ack = False, is_reply = False):
        self.tms.append(packet)
        if (is_ack or is_reply):
            try:
                ids = [tc.packet_id for tc in self.tcs]
                packet_id = packet["data"]["packet_id"]
                if packet_id in ids:
                    index = ids.index(packet_id)
                    self.tcs[index].attach_packet(packet, is_ack = is_ack, is_reply = is_reply)
            except:
                print("Failed to attach packet to TC")       
        return None
    
    def push_tc(self, packet):
        self.tcs.append(packet)


class Viewer(StoppableThread):
    def __init__(self, config = None, verbose_level = 0, **kwargs):
        """ 
        verbose level can be:
        0 for no output
        1 for rack only
        2 to rack, eack, tcreply
        3 for all packets
        """
        super(Viewer, self).__init__(**kwargs)
        if config is None:
            raise Exception("please provide a valid configuration dictionnary")
        self.config = config        
        self.verbose_level = verbose_level
        self.connected = False
        self.db = Db()
        self.punp = PackerUnpacker(config = config)
        return None

    def connect(self):
        if self.connected:
            print("Already connected!")
        # open the port for sending TC    
        self.tm_receiver = context.socket(zmq.SUB)
        self.tm_receiver.connect(self.config["zmq_connection"]["tm_port"])
        self.tm_receiver.subscribe("")          
        self.tc_receiver = context.socket(zmq.SUB)
        #self.tc_receiver.connect(self.config["zmq_connection"]["tc_port"])    
        #self.tc_receiver.subscribe("")    
        self.connected = True  
        return None

    def disconnect(self):
        if not(self.connected):
            print("Not connected")
            return None
        self.tm_receiver.close()
        self.tc_receiver.close()        
        self.connected = False
        return None
    
    def process_tm(self, tm):
        try:
            packet = self.punp.unpack(Byt(tm))
            if not(self.db is None):
                self.db.push_tm(packet)
            try:
                crc_status = self.punp.check_crc(packet)
                if self.verbose_level == 3:
                    print("Got TM - CRC status {} - {}".format(crc_status, packet))
                elif self.verbose_level == 2:
                    if packet["header"]["packet_type"] in [self.punp.rack_packet_type,
                                                            self.punp.eack_packet_type,
                                                            self.punp.tc_reply_packet_type]:
                        print("Got TM - CRC status {} - {}".format(crc_status, packet))
                elif self.verbose_level == 1:
                    if packet["header"]["packet_type"] in [self.punp.rack_packet_type]:
                        print("Got RACK - CRC status {} - {}".format(crc_status, packet))
                else:
                    pass
            except:
                print("Got TM - failed to calc CRC - {}".format(packet))                       
        except:
            print("Got TM but unpack failed: "+Byt(tm).hex())      
        return None        
        
    def run(self):
        while not(self.stopped()):
            try:
                tc = self.tc_receiver.recv(zmq.NOBLOCK)
                print(tc)     
            except zmq.ZMQError as e:
                if e.errno == zmq.EAGAIN:
                    pass # no message was ready (yet!)            
            time.sleep(0.2) # breathing room
            try:
                tm = self.tm_receiver.recv(zmq.NOBLOCK)  
                print(tm)   
            except zmq.ZMQError as e:
                if e.errno == zmq.EAGAIN:
                    pass # no message was ready (yet!)
        print("Viwer has stopped")

    def stop_receiver(self):
        super(Viewer, self).stop()          
        return None

def stop():
    viewer.stop()
    viewer.disconnect()

if __name__ == "__main__":
    from ruamel import yaml
    LOADER = yaml.YAML()
    CONFIG = LOADER.load(open("../config.yml").read())        
    viewer = Viewer(config = CONFIG)
    viewer.connect()
    viewer.start()
