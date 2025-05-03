# coding: utf-8
from byt import Byt
import zmq
from lantern.packerUnpacker import PackerUnpacker
import time
from lantern.utils import StoppableThread

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

    def validate_last_tc(self, timeout = 3):
        """
        wait for ack for last tc sent and raise and exception if an error occured
        """
        t0 = time.time()
        while (self.tcs[-1].eack is None):
            time.sleep(0.1)
            if (time.time() - t0) > timeout:
                raise Exception("Timeout!")
        error = self.tcs[-1].eack["data"]["error"]
        if error != "OK":
            raise Exception("Error {} occured".format(error))
        return True        


class BaseDriver(StoppableThread):
    def __init__(self, config = None, verbose_level = 0, **kwargs):
        """ 
        verbose level can be:
        0 for no output
        1 for rack only
        2 to rack, eack, tcreply
        3 for all packets
        """
        super(BaseDriver, self).__init__(**kwargs)
        if config is None:
            raise Exception("please provide a valid configuration dictionnary")
        self.config = config        
        self.verbose_level = verbose_level
        self.connected = False
        self.packetid = 0
        self.sysid = self.config["general"]["system_id"]
        self.punp = PackerUnpacker(config = config)
        self.db = Db()
        return None

    def connect(self):
        if self.connected:
            print("Already connected!")
        # open the port for sending TC
        self.sender = context.socket(zmq.PUB)
        self.sender.bind(self.config["zmq_connection"]["tc_port"])        
        self.receiver = context.socket(zmq.SUB)
        self.receiver.connect(self.config["zmq_connection"]["tm_port"])
        self.receiver.subscribe("")
        self.connected = True  
        return None

    def disconnect(self):
        if not(self.connected):
            print("Not connected")
            return None
        self.sender.unbind(self.config["zmq_connection"]["tc_port"])
        self.receiver.close()
        self.connected = False
        return None

    def generate_tc_from_data(self, cmd_data_dict):
        if not("command_id" in cmd_data_dict):
            raise Exception("field 'command_id' is compulsory in command data dictionnary")
        if not(cmd_data_dict["command_id"] in self.punp.tc_packet_data_desc):
            raise Exception("command_id {} not registered in PackerUnpacker. Check your YML descriptor!".format(cmd_data_dict["command_id"]))
        # generate data to calculate length
        data = self.punp._pack_from_desc(cmd_data_dict, self.punp.tc_packet_data_desc[cmd_data_dict["command_id"]])
        data_length = len(data)
        # construct packet
        header = {"system_id": self.sysid | 0b10000000,
                  "packet_id": self.packetid,
                  "data_length": data_length,
                  "crc": 0
                  }
        tcPacket = {"header": header, "data": cmd_data_dict}
        # we need to generate the packet to calculate CRC
        packet = self.punp.pack(tcPacket)
        crc = self.punp._compute_crc32(packet)
        tcPacket["header"]["crc"] = crc
        # increment packet id for next time
        self.packetid = self.packetid + 1
        return tcPacket

    def simple_send_command(self, command_dict):
        if not(self.connected):
            raise Exception("Driver not connected!")
        tcPacket = self.punp.pack(command_dict)
        self.sender.send(tcPacket, zmq.NOBLOCK)
        if not(self.db is None):
            self.db.push_tc(TC(command_dict))
        return None

    def validate_last_tc(self, timeout = 3):
        return self.db.validate_last_tc(timeout = timeout)

    def run(self):
        while not(self.stopped()):
            time.sleep(0.01) # breathing room
            try:
                byte = self.receiver.recv(zmq.NOBLOCK)
                try:
                    packet = self.punp.unpack(Byt(byte))
                    is_rack, is_eack, is_reply = False, False, False
                    if (packet["header"]["packet_type"] == self.punp.rack_packet_type):
                        is_rack = True
                    if (packet["header"]["packet_type"] == self.punp.eack_packet_type):
                        is_eack = True
                    if (packet["header"]["packet_type"] == self.punp.tc_reply_packet_type):
                        is_reply = True     
                    if not(self.db is None):
                        self.db.push_tm(packet, is_ack=is_eack, is_reply=is_reply)                                     
                    #try:
                    crc_status = self.punp.check_crc(packet)
                    #except:
                    #    crc_status = False
                    #    print("Got TM - failed to calc CRC - {}".format(packet))                          
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
                   print("Got TM but unpack failed: "+Byt(byte).hex())           
            except zmq.ZMQError as e:
                if e.errno == zmq.EAGAIN:
                    pass # no message was ready (yet!)
        print("Electronics driver has stopped")

    def stop_receiver(self):
        super(BaseDriver, self).stop()          
        return None
