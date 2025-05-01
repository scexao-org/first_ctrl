#coding: utf8
from byt import Byt
import struct
import os.path
import copy
import ruamel.yaml as yaml

LOADER = yaml.YAML()

class PackerUnpacker:
    """A class to pack and unpack TM/TC packets following the description given in a YML file"""
    def __init__(self, config = None):
        if config is None:
            raise Exception("please provide a valid configuration dictionnary")
        self.config = config
        # lookup table for cimputing payload crc
        payload_crc_table = {}
        poly = 0x04C11DB7
        for byte in range(256):
            c = byte << 24
            for i in range(8):
                c = (c << 1) ^ poly if (c & 0x80000000) else c << 1
            payload_crc_table[byte] = c & 0xffffffff
        self.payload_crc_table = payload_crc_table
        self.tc_reply_packet_type = None
        self.rack_packet_type = None
        self.eack_packet_type = None        
        self.load_descriptors()        
        return None
    
    def _compute_crc32(self, message):
        crc = 0xffffffff
        for i in Byt(message).iterInts():
            crc = ((crc << 8) & 0xffffffff) ^ self.payload_crc_table[(crc >> 24) ^ i]
        return crc
    
    def check_crc(self, packet):
        packet_copy = copy.deepcopy(packet)
        packet_copy["header"]["crc"] = 0
        crc_calc = self._compute_crc32(self.pack(packet_copy))
        return crc_calc==packet["header"]["crc"]

    def load_descriptors(self):
        """ load packet descriptors from a given directory."""

        # load all the descriptors
        tmtc_filename = "{}/{}".format(self.config["descriptors"]["folder"], self.config["descriptors"]["tmtc"])
        tc_packet_data_filename = "{}/{}".format(self.config["descriptors"]["folder"], self.config["descriptors"]["tc_packet_data"])
        tm_packet_data_filename = "{}/{}".format(self.config["descriptors"]["folder"], self.config["descriptors"]["tm_packet_data"])  
        tc_reply_data_filename = "{}/{}".format(self.config["descriptors"]["folder"], self.config["descriptors"]["tc_reply_data"])
        errors_filename = "{}/{}".format(self.config["descriptors"]["folder"], self.config["descriptors"]["errors"])        
        if not(os.path.isfile(tmtc_filename)):
            raise Exception("TMTC descriptors not found at: {}".format(tmtc_filename))
        if not(os.path.isfile(tc_packet_data_filename)):
            raise Exception("TMTC descriptors not found at: {}".format(tc_packet_data_filename))
        if not(os.path.isfile(tm_packet_data_filename)):
            raise Exception("TMTC descriptors not found at: {}".format(tm_packet_data_filename))
        if not(os.path.isfile(tc_reply_data_filename)):
            raise Exception("TMTC descriptors not found at: {}".format(tc_reply_data_filename))        
        if not(os.path.isfile(errors_filename)):
            raise Exception("TMTC descriptors not found at: {}".format(errors_filename))           
        self.tmtc_desc = LOADER.load(open(tmtc_filename).read())
        self.tc_packet_data_desc = LOADER.load(open(tc_packet_data_filename).read())
        self.tm_packet_data_desc = LOADER.load(open(tm_packet_data_filename).read())
        self.tc_reply_data_desc = LOADER.load(open(tc_reply_data_filename).read())
        error_desc = LOADER.load(open(errors_filename).read())
        self.error_desc = {"msg_to_code": {}, "code_to_msg": {}}
        for key in error_desc:
            self.error_desc["code_to_msg"][key] = error_desc[key]
            self.error_desc["msg_to_code"][error_desc[key]] = key

        # process the list of tm data types
        tm_packet_data_desc = {}
        for type in self.tm_packet_data_desc:
            if type == "tc_reply":
                self.tc_reply_packet_type = self.tm_packet_data_desc[type]["packet_type"]
            if type == "rack":
                self.rack_packet_type = self.tm_packet_data_desc[type]["packet_type"]  
            if type == "eack":
                self.eack_packet_type = self.tm_packet_data_desc[type]["packet_type"]                               
            tm_packet_data_desc[self.tm_packet_data_desc[type]["packet_type"]] = self.tm_packet_data_desc[type]["format"]
        self.tm_packet_data_desc = tm_packet_data_desc
        # process the list of tm data types
        tc_packet_data_desc = {}
        for cmd in self.tc_packet_data_desc:
            tc_packet_data_desc[self.tc_packet_data_desc[cmd]["command_id"]] = self.tc_packet_data_desc[cmd]["format"]
        self.tc_packet_data_desc = tc_packet_data_desc
        # process list of tc_reply data
        tc_reply_data_desc = {}
        for cmd in self.tc_reply_data_desc:
            tc_reply_data_desc[self.tc_reply_data_desc[cmd]["command_id"]] = self.tc_reply_data_desc[cmd]["format"]
        self.tc_reply_data_desc = tc_reply_data_desc
        return None
    
    def _unpack_from_desc(self, packet, desc, fieldname):
        """ Recursively unpack the different fields given in the packet description """
        start = desc["start"]
        length = desc["length"]
        if length in ["none", "null", "None", "Null"]:
            subpacket = packet[start:]
        else:
            subpacket = packet[start:start+length]
        if "format" in desc.keys():
            fields = fieldname.split(",")         
            if desc["format"] in ["none", "null", "None", "Null"]:
                return subpacket
            else:
                unpacked = []
                it = struct.iter_unpack(desc["format"], subpacket)
            if len(fields) == 1:
                if fields[0] == "error":
                    unpacked = [self.error_desc["code_to_msg"][r[0]] for r in it]                   
                else:
                    unpacked = [r[0] for r in it]
                    if desc["format"] == "s":
                        unpacked = b''.join(unpacked)
            else:
                values = [r for r in it]
                unpacked = {fields[k].strip(): [v[k] for v in values] for k in range(len(fields))}
            if len(unpacked) == 1:
                unpacked = unpacked[0]             
            return unpacked
        else:
            unpacked = {}
            for k in desc.keys():
                if k in ["start", "length"]:
                    pass
                else:
                    if len(k.split(",")) > 1:
                        unpacked = {**unpacked, **self._unpack_from_desc(subpacket, desc[k], k)}
                    else:
                        unpacked[k] = self._unpack_from_desc(subpacket, desc[k], k)
            return unpacked 

    def _pack_from_desc(self, packet, packet_desc):
        """ Recursively pack a packet following the different fields in the description """
        start = packet_desc["start"]
        length = packet_desc["length"]
        if "format" in packet_desc.keys():
            if isinstance(packet, list):
                packed = Byt("")
                for b in packet:
                    packed += Byt(struct.pack(packet_desc["format"], b))
            else:
                if packet_desc["format"] in ["none", "null", "None", "Null"]:
                    packed = Byt(packet)
                else:
                    if packet_desc["format"] == "s":     
                        packed = Byt()
                        for b in packet: 
                            packed = packed + Byt(struct.pack(packet_desc["format"], Byt(b)))        
                    else:                                          
                        packed = Byt(struct.pack(packet_desc["format"], packet))
            return packed
        else:
            packed = Byt()
            for key in packet_desc.keys():
                if key in ["start", "length"]:
                    pass
                else:
                    if len(key.split(",")) == 1:
                        if key == "error":
                            packet[key] = self.error_desc["msg_to_code"][packet[key]]                               
                        packed += Byt(self._pack_from_desc(packet[key], packet_desc[key]))
                    else:
                        keys = [k.strip() for k in key.split(",")]
                        for j in range(len(packet[keys[0]])):
                            data = [packet[k][j] for k in keys]
                            packed += Byt(struct.pack(packet_desc[key]["format"], *data))
            return packed 
        
    def unpack(self, packet):
        """ Unpack a TM/TC packet by using the first bit to identify it """
        if ((packet.ints()[0] >> 7) == 0):
            unpacked = self._unpack_from_desc(packet, self.tmtc_desc["telemetry"], "telemetry")
            type = unpacked["header"]["packet_type"]
            unpacked["data"] = self._unpack_from_desc(unpacked["data"], self.tm_packet_data_desc[type], type)
            if not(self.tc_reply_packet_type is None):
                if type == self.tc_reply_packet_type:
                    cmd_id = unpacked["data"]["command_id"]
                    unpacked["data"]["tc_reply_data"] = self._unpack_from_desc(unpacked["data"]["tc_reply_data"], 
                                                                               self.tc_reply_data_desc[cmd_id], cmd_id)
        else:
            unpacked = self._unpack_from_desc(packet, self.tmtc_desc["telecommand"], "telecommand")
            command_id = struct.unpack("B", unpacked["data"][0])[0]
            unpacked["data"] = self._unpack_from_desc(unpacked["data"], self.tc_packet_data_desc[command_id], command_id)
        return unpacked
            
    def pack(self, packet):
        """ pack a TM/TC packet by first looking at which type it is using system_id """
        if ((packet["header"]["system_id"]>>7) == 0):
            header = self._pack_from_desc(packet["header"], self.tmtc_desc["telemetry"]["header"])
            if ( (self.tc_reply_packet_type is None) or (packet["header"]["packet_type"] != self.tc_reply_packet_type) ):
                data = self._pack_from_desc(packet["data"], self.tm_packet_data_desc[packet["header"]["packet_type"]])
            else:
                cmd_id = packet["data"]["command_id"]
                packet["data"]["tc_reply_data"] = self._pack_from_desc(packet["data"]["tc_reply_data"], self.tc_reply_data_desc[cmd_id])
                data = self._pack_from_desc(packet["data"], self.tm_packet_data_desc[packet["header"]["packet_type"]])
        else:
            header = self._pack_from_desc(packet["header"], self.tmtc_desc["telecommand"]["header"])
            data = self._pack_from_desc(packet["data"], self.tc_packet_data_desc[packet["data"]["command_id"]])
        return header+data
    

# debug
if __name__ == "__main__":
    packet = Byt.fromHex("01 4b 00 00 00 fd 6d 01 8c e6 10 97 0b 00 00 00 0e 01 00 00 00 d9 ef fb 4d 60 ec 54 c5 90 47 60 46 d0 07 d0 27 00 00 fa 44 00 40 1f 46 00 00 00 00 00 00 00 00 02 00 00 00 f8 ef fb 4d 70 86 53 c5 94 ec 5f 46 d0 07 d0 27 00 00 fa 44 00 40 1f 46 00 00 00 00 00 00 00 00 03 00 00 00 17 f0 fb 4d 60 3c 54 c5 dc e3 5f 46 d0 07 d0 27 00 00 fa 44 00 40 1f 46 00 00 00 00 00 00 00 00 04 00 00 00 36 f0 fb 4d d0 7d 53 c5 a0 0f 60 46 d0 07 d0 27 00 00 fa 44 00 40 1f 46 00 00 00 00 00 00 00 00 05 00 00 00 55 f0 fb 4d 70 48 55 c5 a0 f6 5f 46 d0 07 d0 27 00 00 fa 44 00 40 1f 46 00 00 00 00 00 00 00 00 06 00 00 00 74 f0 fb 4d 70 29 55 c5 3c 33 60 46 d0 07 d0 27 00 00 fa 44 00 40 1f 46 00 00 00 00 00 00 00 00 07 00 00 00 93 f0 fb 4d 30 be 54 c5 94 ba 5f 46 d0 07 d0 27 00 00 fa 44 00 40 1f 46 00 00 00 00 00 00 00 00 08 00 00 00 b2 f0 fb 4d e0 c5 53 c5 18 f9 5f 46 d0 07 d0 27 00 00 fa 44 00 40 1f 46 00 00 00 00 00 00 00 00 09 00 00 00 d1 f0 fb 4d 00 0e 54 c5 04 dc 5f 46 d0 07 d0 27 00 00 fa 44 00 40 1f 46 00 00 00 00 00 00 00 00 09 00 00 00 d1 f0 fb 4d 00 0e 54 c5 04 dc 5f 46 d0 07 d0 27 00 00 fa 44 00 40 1f 46 00 00 00 00 00 00 00 00")
    #packet = Byt.fromHex("01 00 00 00 00 02 10 00 9a 48 b5 66 48 4b 20 49 4e 49 54 20 45 52 52 4f 52 3a 20 30")
    #print(packet.hex())
    LOADER = yaml.YAML()    
    CONFIG = LOADER.load(open("../config.yml").read())
    punp = PackerUnpacker(config=CONFIG)
    tm = punp.unpack(packet)
    print(tm)
    pkt = punp.pack(tm)
    print(pkt.hex())

