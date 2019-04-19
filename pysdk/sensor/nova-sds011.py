"""

Copyright 2019 Yuktix Technologies Private Limited.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

-----------------------------------------------------------------

python program to interface 
Nova PM Air Quality Sensor SDS011 
This is a sensor that works using laser scattering.


@author RAJEEV JHA (rjha@yuktix.com)

sds011 pm sensor program 
This is developer version.
For usage: see main()

check sum is data1 to data15 bytes 
we use 0xFF for device id bytes
e.g. for check check_firmware command, 
data1 = 7, we have 0xFF + 0xFF + 0x07 = 517 (decimal)
517 = 0b1000000101
low 8 bits = 0x05 

-----------------------------------------------------------------

"""


import time
import struct
import binascii
import logging
import logging.handlers
import serial




sds011_commands = {

    "set_active_mode" : {
        "header" : bytearray([0xAA, 0xB4, 0x02, 0x01, 0x00]),
        "id" : 0xC5,
        "checksum" : 0x01  
    },
    
    "set_query_mode" : {
        "header" : bytearray([0xAA, 0xB4, 0x02, 0x01, 0x01]),
        "id" : 0xC5,
        "checksum" : 0x02
    },
    
    "get_report_mode" : {
        "header" : bytearray([0xAA, 0xB4,0x02, 0x00, 0x00]),
        "id" : 0xC5,
        "checksum" : 0x00
    },
    
    "query_data" : {
        "header" : bytearray([0xAA, 0xB4, 0x04, 0x00, 0x00]),
        "id" : 0xC0,
        "checksum" : 0x02
    },
    "check_firmware" : {
        "header" : bytearray([0xAA, 0xB4, 0x07, 0x00, 0x00]),
        "id" : 0xC5,
        "checksum" : 0x05
    }
}



def millis():
    return int(round(time.time() * 1000))



def open_serial(config):

    connx = serial.Serial()
    connx.port = config["port"]
    connx.baudrate = int(config["speed"])

    """
    read and write timeout in seconds 
    floats are allowed. 
    connx.read() will block till timeout
    or return when read(size) bytes have been received.
    """
    
    connx.timeout = 1
    connx.write_timeout = 1

    if not connx.isOpen():
        print "try opening serial port {0} ...".format(connx.port)
        connx.open()
        time.sleep(1)

    if connx.isOpen():
        print "pyserial version {0} on {1} is open!".format(serial.VERSION, connx.port)
    
    return connx




"""
param connx: serial connection 
packet : sensor response packet 
timeout - in seconds 
size - size of packet to collect 
command_id : command_id in response 

"""

def get_response_packet(connx, packet, timeout, size, command_id):
    
    logger = logging.getLogger("main." + __name__)
    current_ts = millis()
    end_ts = millis() + (timeout * 1000)
    
    while current_ts < end_ts:
        packet.extend(connx.read(1))
        if len(packet) >= 2:
            if(packet[0] != 0xAA or packet[1] != command_id):
                packet[0:] = []
        
            
        if len(packet) >= size:
            break
        
        current_ts = millis()
    # loop 
    
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("serial packet: {0}".format(binascii.hexlify(packet)))
    
    return
        

def send_command(connx, header, checksum):
    
    command = bytearray() 
    command.extend(header)
    
    for i in range(10):
        command.append(0x00)
    
    command.append(0xFF)
    command.append(0xFF)
    command.append(checksum)
    command.append(0xAB)
    
    connx.flushInput()
    connx.write(command)
    
    print "pc->sensor [{0}]".format(binascii.hexlify(command))
    command[0:] = []
    return



def process_command(connx, name, response):
    
    command = sds011_commands.get(name, None)
    if not command:
        raise ValueError("unknown command {0}".format(name))
    
    send_command(connx, command["header"], command["checksum"])
    time.sleep(1)
    get_response_packet(connx, response, 5, 10, command["id"])
    return
    



def parse_firmware_response(response):
    
    if(len(response) != 10):
        print "packet size is {0}, not 10".format(len(response))
        print "packet is {0}".format(binascii.hexlify(response))
        return 
    
    
    print "fimware date:{0}-{1}-{2} (dd-mm-YY)".format(response[5], response[4], response[3])
    return
    
    
def parse_mode_response(response):
    
    if(len(response) != 10):
        print "packet size is {0}, not 10".format(len(response))
        print "packet is {0}".format(binascii.hexlify(response))
        return 
    
    
    mode = response[4]
    if mode == 0:
        print "sensor is set in active mode!"
    elif mode == 1:
        print "sensor is set in query mode!"
    else:
        print "God alone knows your report mode!"
    
    return mode




def parse_data_response(packet):
    
    size = len(packet)

    if size != 10:
        print "error: packet size is not 10"
        return None

    if packet[0] != 0xAA:
        print "error: packet header is not 0xAA"
        return None

    if packet[9] != 0xAB:
        print "error: packet tail is not 0xAB"
        return None

    readings = struct.unpack('<BBhhxxBB', packet)
    if (readings[1] != 0xC0) or (readings[5] != 0xAB):
        print "error: packet is not in format 0xAA|0xC0|....|0xAB"
        return None
    
    pm_25 = readings[2]/10.0
    pm_10 = readings[3]/10.0
    print "sds011 pm25: {0} ug/m^3, pm10: {1} ug/m^3".format(pm_25, pm_10)
    return (pm_25, pm_10)



def check_firmware(connx):
    response = bytearray()
    process_command(connx, "check_firmware", response)
    mode = parse_firmware_response(response) 
    response[0:] = []    
    return mode 



def set_active_mode(connx):
    response = bytearray()
    process_command(connx, "set_active_mode", response)
    mode = parse_mode_response(response) 
    response[0:] = []    
    return mode 


def set_query_mode(connx):
    response = bytearray()
    process_command(connx, "set_query_mode", response)
    mode = parse_mode_response(response) 
    response[0:] = []    
    return mode 


def get_report_mode(connx):
    response = bytearray()
    process_command(connx, "get_report_mode", response)
    mode = parse_mode_response(response)
    response[0:] = []    
    return mode
    


def get_active_data(connx, **kwargs):
    
    wait_time = kwargs.pop("wait", 5)
    command_id = sds011_commands["query_data"]["id"]
    print "command_id is {0}".format(command_id)
    
    while True:
        response = bytearray()
        #response.extend(connx.read(10))
        get_response_packet(connx, response, 2, 10, command_id)
        if response:
            print "sensor ->pc [{0}]" .format(binascii.hexlify(response))
            values = parse_data_response(response)
            print "\r\n\r\n"
            response[0:] = [] 
        else:
            print "sensor->pc no response!"
            
        time.sleep(wait_time)
        connx.flushInput()
        
        # loop 
    return



def get_query_data(connx):
    
    command_id = sds011_commands["query_data"]["id"]
    print "command_id is {0}".format(command_id)
    
    response = bytearray()
    values = None 
    
    process_command(connx, "query_data", response)
    get_response_packet(connx, response, 2, 10, command_id)
    
    if response:
        print "sensor ->pc [{0}]" .format(binascii.hexlify(response))
        values = parse_data_response(response)
        response[0:] = [] 
    else:
        print "sensor->pc no response!"
        
    connx.flushInput() 
    return values 
    

def main():
    
    # set serial port and speed.
    xconfig = {
        "port" : "/dev/tty.usbserial-FT1USWV6",
        "speed" : 9600
    }
    
    connx = open_serial(xconfig)
    print "sensor is initializing ..."
    time.sleep(10)
    check_firmware(connx)
    
    # uncomment below 2 lines for active mode 
    # set_active_mode(connx)
    # get_active_data(connx, wait=10)
    
    # default is query mode 
    set_query_mode(connx)
    
    while True:
        get_query_data(connx)
        print "\r\n\r\n"
        time.sleep(10)
    
    connx.close()
    


if __name__ == '__main__':
    main()
