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
Dylos DC1100 Air Quality Sensor
This is a sensor that works using laser scattering.


@author RAJEEV JHA (rjha@yuktix.com)

notes: Dylos is a pretty good sensor. It is a pity they 
do not provide the unit in bare package.

The sensor provides data as delimited string on UART. 
You can save the readings to a program or upload it to 
Yuktix ankidb cloud.

-----------------------------------------------------------------

"""

import time
import sys
import traceback
import logging
import logging.handlers
import serial
from datetime import datetime
import requests


def millis():
    return int(round(time.time() * 1000))


def open_serial(serial_port, **kwargs):

    speed = kwargs.pop("speed", 9600)
    connx = serial.Serial()
    connx.port = serial_port
    connx.baudrate = int(speed)

    connx.timeout = 1
    connx.write_timeout = 1

    while True:
        if not connx.isOpen():
            print "opening serial port {0}... ".format(connx.port)
            connx.open()
            time.sleep(2)

        if connx.isOpen():
            print "pyserial version {0} on {1} is open!".format(serial.VERSION, connx.port)
            return connx

    return None


#  timeout  in milli seconds
def read_serial(connx, ibuffer, timeout):

    logger = logging.getLogger("main." + __name__)
    current_ts = millis()
    end_ts = millis() + timeout

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("read serial: time:{0}, end:{1}".format(current_ts, end_ts))

    while current_ts < end_ts:
        if connx.inWaiting():
            ibuffer.extend(connx.read(32))

        time.sleep(0.01)
        current_ts = millis()

    return


def save_data(response):

    response = str(response)
    response = response.strip()
    tokens = response.split(",")
    epoch = int(time.time())
    d1 = datetime.fromtimestamp(epoch)
    dt_string = d1.strftime("%d %B %Y %H:%M:%S")

    xdata = None
    size = len(tokens)
    if size == 2:
        with open("dylos.csv", "a+") as outfile:
            xmsg = "{0},{1},{2},{3} \r\n".format(epoch, dt_string, tokens[0], tokens[1])
            outfile.write(xmsg)
        xdata = {
            "pm10" : tokens[0],
            "pm25" : tokens[1]
        }


    return xdata



def upload_to_server(xdata):

    pm25 = xdata.get("pm25", None)
    pm10 = xdata.get("pm10", None)
    if pm10 and pm25:
        xbencode = "d5:_sno_7:dylos014:PM25i{0}e4:PM10i{1}ee".format(pm25, pm10)
        print xbencode
    
    endpoint = "http://www.yuktix.com/zzz/xxxxxx"
    post_data = {
      "data" : xbencode
    }

    headers = {
        "Content-type": "application/x-www-form-urlencoded",
        "charset" : "utf-8"
    }

    r1 = requests.post(endpoint, data=post_data, headers=headers)
    print r1.status_code
    print r1.text




def read_sensor(connx, **kwargs):

    print "CTRL+C to quit program..."
    upload_flag = kwargs.pop("upload", False)

    while True:
        connx.flushInput()
        response = bytearray()
        read_serial(connx, response, 1000)

        xdata = None
        if response:
            print response
            xdata = save_data(response)
            response[0:] = []

        if upload_flag and xdata:
            upload_to_server(xdata)

    return



def main():

    serial_port = "/dev/tty.usbserial"
    connx = open_serial(serial_port, speed=9600)
    time.sleep(1)
    connx.flushInput()

    # default behavior is to read sensor
    read_sensor(connx, upload=True)
    connx.close()
    print "sensor reading done..."



if __name__ == '__main__':
    main()
