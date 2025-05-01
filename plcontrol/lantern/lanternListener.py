#coding: utf8 
import serial
import zmq
import time
from byt import Byt
from utils import StoppableThread

# Create a ZMQ context
context = zmq.Context()

class Listener(StoppableThread):
    """ 
    Listener object which binds to the serial port and forward packets.
    Listens on serial and transfer incoming packet to ZMQ_TM_ADDRESS (in PUSH)
    Listens to ZMQ_TC_ADDRESS (in PULL) and transfer any packet on the serial line
    """
    def __init__(self, config = None, *args, **kwargs):
        super(Listener, self).__init__(*args, **kwargs)
        if config is None:
            raise Exception("Please provide a valid configuration dictionnary")
        self.config = config
        self.end_sequence = Byt.fromHex(self.config["serial_connection"]["end_sequence"])
        self.esc_character = Byt.fromHex(self.config["serial_connection"]["escape_character"])
        self.serial_port = self.config["serial_connection"]["port"]
        self.serial_baud = self.config["serial_connection"]["baud"]
        self.zmq_tc_address = self.config["zmq_connection"]["tc_port"]
        self.zmq_tm_address = self.config["zmq_connection"]["tm_port"]
        self.rx_buffer = Byt() # put the data coming from serial port
        # open serial port
        self.ser = serial.Serial(self.serial_port, self.serial_baud)        
        # Create a ZMQ socket to send data
        self.sender = None
        # create a ZMQ socket to receive data
        self.receiver = None 
        self.connected = False       
        return None
    
    def connect(self):
        self.sender = context.socket(zmq.PUB)          
        self.sender.bind(self.zmq_tm_address)
        self.receiver = context.socket(zmq.SUB)         
        self.receiver.connect(self.zmq_tc_address)  
        self.receiver.subscribe("")
        self.connected = True
        return None

    def disconnect(self):
        self.sender.unbind(self.zmq_tm_address)
        self.receiver.close()
        self.connected = False    
        return None
    
    # escape and de-escape function
    def _escape(self, packet):
        packet = Byt.fromHex(packet.hex()) # make sure it has the correct Byt type and spacing in hex notation
        return Byt.fromHex(packet.hex().replace(self.end_sequence.hex(), self.end_sequence.hex()+" "+self.esc_character.hex()))

    def _unescape(self, packet):
        return Byt.fromHex(packet.hex().replace(self.end_sequence.hex()+" "+self.esc_character.hex(), self.end_sequence.hex()))

    def _get_packets(self, data_byt):
        """
        look for the end sequence in the data_byt (of Byt.byt type) and
        return a list of packets (escaped and with no end sequence)
        """
        packets = []
        ind = data_byt.find(self.end_sequence+self.end_sequence)
        while (ind > 0):
            packets.append(self._unescape(data_byt[:ind]))
            data_byt= data_byt[ind+2*len(self.end_sequence):]
            ind = data_byt.find(self.end_sequence+self.end_sequence)
        return packets, data_byt
        
    def run(self):
        while not(self.stopped()):
            time.sleep(0.01) # breathing room
            # check outgoing
            try:
                packet = self.receiver.recv(zmq.NOBLOCK)   
                send_bytes = self._escape(packet) + self.end_sequence + self.end_sequence
                print("To TC port: {}".format(send_bytes.hex()))
                self.ser.write(send_bytes)      
            except zmq.ZMQError as e:
                if e.errno == zmq.EAGAIN:
                    pass # no message was ready (yet!)         
            # check incoming
            bytesToRead = self.ser.inWaiting()
            self.rx_buffer += Byt(self.ser.read(bytesToRead))            
            packets, remaining_byt = self._get_packets(self.rx_buffer)
            for p in packets:
                print("To TM port: "+Byt(p).hex())   
                self.sender.send(p, zmq.NOBLOCK)
            self.rx_buffer = remaining_byt
        print("Listener has stopped")
        return None

def stop():
    listener.stop()    
    if listener.connected:
        listener.disconnect()

if __name__ == "__main__":
    from ruamel import yaml
    import os
    # get path to this file
    this_dir = os.path.dirname(os.path.abspath(__file__))
    
    LOADER = yaml.YAML()
    CONFIG = LOADER.load(open(this_dir+"/config.yml").read())
    # Create and start the threads
    listener = Listener(config=CONFIG)
    listener.connect()
    listener.start()
