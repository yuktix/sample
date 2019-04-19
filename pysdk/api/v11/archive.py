
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

test script for ankidb cloud api version 1.1.0 
this script is supposed to be standalone for quick testing 
on machines with minimum library support. Use yuktix python sdk 
for better library support and avoid repeatable chores!


please ensure proper intervals between subsequent API calls 
to avoid blacklisting. 


"""

import hmac
import hashlib
import base64
import string
import random

import sys 
import logging
import logging.handlers

import traceback
import time
import json
import requests




__CHANNEL_MAP__ = {
    "T" : "Temperature",
    "RH" : "Humidity",
    "Rain" : "Rain",
    "SE" : "SENSOR_ERROR",
    "__rssi" : "CELL_SIGNAL"
}


def do_post(api_url, post_data, headers, **kwargs):
    
    logger = logging.getLogger("main." + __name__)
    success_code = kwargs.pop("success_code", 200)
    api_name = kwargs.pop("api_name", "unknown")
    
    try:
        post_request = requests.post(api_url, data=post_data, headers=headers)
        if post_request.status_code != success_code:
            raise Exception(post_request.text.encode("ascii"))

        return post_request.text
        
    except Exception:
        exc_tuple = sys.exc_info()
        logger.error(traceback.format_exc())
        xmsg = "error in api {0}, cause: {1}".format(api_name, str(exc_tuple[1]))
        raise Exception(xmsg)


def format_points(points):
    
    if not points:
        print "error: server returned no points!"
        return 
    
    for point in points:
        ts_unix = int(point["tsUnix"])
        print "timestamp: {0}".format(ts_unix)
        
        for channel in point.keys(): 
            name = __CHANNEL_MAP__.get(channel) 
            if name:
                print "{0}: {1}".format(name, point[channel])
        print "\r\n"

    


def get_device_archive(server, auth_header, serial, num_hours):
    
    api_url = server["endpoint"] + "/device/archive"
    
    # end time is now 
    # @warning: if machine uses NTP - this can go out of sync
    # scale to millis for API 
    end_ts = int(time.time())
    start_ts = end_ts - (num_hours * 3600)
    start_ts = start_ts * 1000 
    end_ts = end_ts * 1000 
    
    params = {
        "map" : {
            "serialNumber" : serial, 
            "start" : start_ts, 
            "end": end_ts
        }
    }

    post_data = json.dumps(params)
    post_data = post_data + "\r\n"
    headers = {
        'Content-type': 'application/json', 
        'Authorization' : auth_header 
    }
    
    response = do_post(api_url, post_data, headers, success_code=200, api_name="/device/archive")
    #print response 
    # parse response 
    response_obj = json.loads(response)
    points = response_obj.get("result")
    return points 
    

def compute_api_digest(key, message):

    digest_maker = hmac.new(key, message, hashlib.sha256)
    output = digest_maker.hexdigest()
    output = output +  'a' + 'b'
    encoded = base64.b64encode(output)
    return encoded

    
def random_word(num_digits):
    return ''.join(random.choice(string.lowercase) for i in range(num_digits))


def get_api_auth_header(config):
    
    client_key = config["client_key"]
    secret_key = config["secret_key"]
    
    nonce = random_word(8)
    message = "{0}:{1}".format(nonce, client_key)
    signature = compute_api_digest(str(secret_key), message)
    header = "api client={0} nonce={1} signature={2} ".format(client_key, nonce, signature)
    return header
    
    


def main():
    
    config = {
        
        "apiv11devm1" : {
            "endpoint" : "http://apiv11devm1.yuktix.com/sensordb/v1",
            "client_key" : "xxxx",
            "secret_key" : "zzzz"
        },
        
        "macbook" : {
            "endpoint" : "http://127.0.0.1:8087/sensordb/v1",
            "client_key" : "xxx",
            "secret_key" : "zzz"
        },
        
        "log_file" : "/tmp/forecast.log",
        "log_level" : 10,
        
    }
    
    # setup logging 
    logger = logging.getLogger("main")
    logger.setLevel(config["log_level"])
    file_handler = logging.handlers.WatchedFileHandler(config["log_file"], delay=True)
    
    # logger file handler
    format_string = '%(asctime)s %(levelname)s [%(pathname)s:%(lineno)d]  %(message)s'
    formatter = logging.Formatter(format_string)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(config["log_level"])
    logger.addHandler(file_handler)
    
    # machines to fetch
    serials = ["rainbow"]
    # latest num_hours data
    num_hours = 1
    
    server = config["apiv11devm1"]
    auth_header = get_api_auth_header(server)
    points = None
    
    for serial in serials:
        points = get_device_archive(server, auth_header, serial, num_hours)
        format_points(points)
    
    
    
    # wait at least 15 seconds before making next API call 
    # to avoid being blacklisted on cloud server 
    print "sleep for a bit now...."
    time.sleep(1)
    print "we are done..."



if __name__ == '__main__':
    main()
