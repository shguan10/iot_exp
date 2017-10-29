import re
import sys

import time
import warnings
import cPickle

from datetime import datetime

import collections

sys.path.insert(0,'pywemo')
import pywemo
import bd_connect as bd_c
from threading import Thread
import glob, os

class Driver:
    def __init__(self,bd_url="https://192.168.43.152",uid='FV6U2W0fCFEHz8DlWS3dM1nXxeSrldhzD1eKkbwK',ukey='yk5zKMsn8acF5xFEUyDkM1LGIY1ujy6PnRl7o9a53h0GMkXv39',verify=False,use_cache=True):
        #EVERYTHING WILL WORK IN THIS CODE
        #so long as we are on the same network as the wemo
        #and we know the url of Building Depot

        #Cache system:
        #stores cache of driver in wemo_bd_driver_cache_[ts].pklb
        #where [ts] is utc timestamp of driver creation
        #if the cache is more than 60 seconds old, or if the use_cache flag is False,
        #   this will delete the cache and reinitialize a driver
        #at the end of initializing the driver, this will always write self to cache file,
        #   in the form of a dict, and remove the previous cache
        self.used_cache=False
        ts = int(time.time())

        #look for cache file
        cache_file = None
        for file in glob.glob("wemo_bd_driver_cache_*.pklb"):
            #invariant: there is only one cache file at a time
            cache_file = file

        #decide if we want to use the cache
        if(cache_file is not None):
            cache_ts = int(re.findall(r'\d+',cache_file)[0])
            if (not use_cache or ts-cache_ts>60):
                try:
                    os.remove(cache_file)
                    cache_file = None
                except Exception:
                    print("ERROR: Could not remove cache: "+cache_file)
                    pass

        #actually initialize the driver
        if(cache_file is not None):
            print("trying cached driver")
            self.used_cache=True
            with open(cache_file) as f:
                cache_dict = cPickle.load(f)
                for key in cache_dict:
                    setattr(self,key,cache_dict[key])
            os.remove(cache_file)
        else:
            #cache_file has already been removed
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")

                #connect and initialize the wemo
                self.dev = None
                print "Locating wemo device"
                while (self.dev is None or self.dev.mac is None or self.dev.mac is ""):
                    try:
                        self.dev = pywemo.discover_devices()[0]
                    except IndexError:
                        print "Could not locate device, make sure you are on the same network as it.\n\nTrying again"
                utc_ts=long(time.time())
                self.dev.timesync.TimeSync(UTC=utc_ts,dst=False,DstSupported=False,TimeZone=1)
                print("Synced Time")

                print("device mac id: "+ str(self.dev.mac))

                self.sensors_uuid={}

                #connect with the server, initialize the sensors and actuators
                self.bd_url = bd_url

                self.bdc = bd_c.BD_Connect(url=self.bd_url,uid=uid,ukey=ukey,verify=verify)

                #Initialize the model of wemo
                self.dev.update_insight_params()

                # check if the sensors already contained in the Building Depot
                for k in self.dev.insight_params:
                    #NOTE r['result'] will contain results that OR the search params
                    r=self.bdc.search_sensor(SourceName=[k], Tags =["sensorname:wemo","sensormacid:"+str(self.dev.mac)])
                    #now we need to see if there actually is an element in r that has both of our requirements
                    prev_exist = False

                    index = 0
                    while(index < len(r['result']) and not prev_exist):
                        if (r['result'][index]['source_name'] == k and r['result'][index]['source_identifier'] == self.dev.mac): prev_exist = True
                        index += 1

                    if(prev_exist):
                        uuid=r['result'][index-1]['name']
                    else:
                        # initialize a sensor on BD
                        uuid=self.bdc.post_sensor(name=k,building="wemobuilding",identifier=self.dev.mac)['uuid']
                        self.bdc.post_tag_sensor(names=["sensorname","sensormacid"], values=["wemo",self.dev.mac], sensorid=uuid)
                    self.sensors_uuid[k]=uuid

                    #thread-safe double-ended queue, used as buffer between reading wemo values and posting to BD
                    self.deck = collections.deque(maxlen=999999)
        #store current driver into cache
        ts = int(time.time())
        filename = "wemo_bd_driver_cache_"+str(ts)+".pklb"
        with open(filename,"wb") as f:
            cache_dict = {}
            #for attr in dir(self):
                #cache_dict[attr]=getattr(self, attr)
                #setattr(self, attr, getattr(cache_driver, attr))
            cache_dict["bdc"]=self.bdc
            cache_dict["bd_url"]=self.bd_url
            cache_dict["sensors_uuid"]=self.sensors_uuid
            cache_dict["dev"]=self.dev
            cache_dict["deck"]=self.deck
            cPickle.dump(cache_dict,f)

    def retrieve_data(self,uuid):
        #listen to data from BD
        ts = int(time.time())
        r = self.bdc.retrieve_timeseries(uuid, ts - 6, ts)
        if len(r['data'])>1:
            return r['data']['series'][0]['values'][0][-1]
        return r['data']

    def sense(self,wait_time):
        while True:
            # get data from wemosensor and enqueue onto the deck
            self.dev.update_insight_params()
            samples = {}
            for k in self.dev.insight_params:
                samples[k]=self.dev.insight_params[k]

            samples['lastchange'] = int(totimestamp(samples['lastchange']))

            currtime = int(time.time())
            payload = []
            for k in self.sensors_uuid:
                payload.append(
                    {
                        "sensor_id": self.sensors_uuid[k],
                        "samples": [
                            {
                                "value": samples[k],
                                "time": currtime
                            }
                        ]
                    }
                )
            self.deck.append(payload)
            time.sleep(wait_time)

    def post(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            while True:
                try:
                    payload = self.deck.popleft()
                    r = self.bdc.post_time_series(payload)
                except IndexError:
                    #print("posting to BD faster than retrieving from WeMo")
                    sys.exc_clear()

    def sense_post(self,freq):
        wait = 1./float(freq)
        print("starting sensing thread")
        Thread(target=Driver.sense,args=(self,wait)).start()
        time.sleep(2)
        print("starting posting thread")
        Thread(target=Driver.post,args=(self,)).start()

def totimestamp(dt, epoch=datetime(1970,1,1)):
    td = dt - epoch
    # return td.total_seconds()
    return (td.microseconds + (td.seconds + td.days * 86400) * 10**6) / 10**6

def state_listener(driver,arg):
    #arg could be "on","off", or "listen"
    #if "on", listen for a "1" from bd, and if wemo_state does not match, toggle the wemo
    #if "off", do a similar thing
    #if "listen", or if already toggled wemo from initial command, simply continue listening
    #   on BD for a mismatch between bd_state and wemo_state
    #   and then toggle the wemo whenever there is a mismatch
    #NOTE driver.dev.toggle() automatically updates the internal model of wemo_state
    print("listening...")
    received_initial_cmd = False
    while(True):
        bd_state = driver.retrieve_data(driver.sensors_uuid['state'])
        driver.dev.update_insight_params()
        wemo_state = driver.dev.get_standby_state()
        if(not received_initial_cmd and arg=="on" and bd_state=="1"):
            if (wemo_state == "off"):
                driver.dev.toggle()
                received_initial_cmd = True
                time.sleep(1)
        elif(not received_initial_cmd and arg=="off" and bd_state=="0"):
            if (wemo_state is not "off"):
                driver.dev.toggle()
                received_initial_cmd = True
                time.sleep(1)
        elif(received_initial_cmd or arg=="listen"):
            if (wemo_state is not "off" and bd_state == "0"):
                driver.dev.toggle()
                time.sleep(1)
            elif(wemo_state is "off" and (bd_state == "1" or bd_state == "8")):
                driver.dev.toggle()
                time.sleep(1)

def main(args):
    """
        Accept the command to either read or actuate the Wemo Switch.
        Args as Data:
                        'sense [sample freq]': Read the energy data from the Switch
                            with frequency [sample freq] in Hz and
                            update the metadata on the Building Depot.
                            [sample freq] is optional and defaults to 2 Hz
                        'on': Switch on the Wemo
                        'off': Switch off the Wemo
                        'listen': listen for actuation events from BD, i.e. toggle wemo when current
                            wemo_state mismatches with bd_state
        Returns:
                        If the args is to read energy data from Wemo
                        {
                            "success": "True"
                            "HTTP Error 400": "Bad Request"
                        }
                        If the args is to Actuate the Wemo Switch, then
                        {on/off : success} else
                        {"Device Not Found/Error in fetching data"}
    """

    #initialize driver, try to use cache
    mydriver = Driver()
    if(mydriver.used_cache):
        try:
            #test if the driver is valid
            mydriver.dev.toggle()
            mydriver.dev.toggle()
            mydriver.bdc.get_access_token()
            print("verified driver")
        except Exception:
            mydriver=Driver(use_cache=False)
            print Exception

    #default response
    response = {
        "success": "True"
    }

    if(args[1] == "sense"):
        if(len(args)==2):
            #if there is no freq argument, then default to 2 Hz
            mydriver.sense_post(2)
        else:
            mydriver.sense_post(args[2])
    elif(args[1] == "on" or args[1]=="off"):
        #start listener for events
        lt = Thread(target=state_listener, args=(mydriver, args[1]))
        lt.start()

        #send the signal to BD
        if(args[1]=="on"): num=1
        else: num =0

        payload=[
            {
                "sensor_id": mydriver.sensors_uuid["state"],
                "samples": [
                    {
                        "value": str(num),
                        "time": int(time.time())
                    }
                ]
            }
        ]
        r=mydriver.bdc.post_time_series(payload=payload)
        print r
        if(r['success']=='True'):
            response = {
            }
            if args[1]=="on": response["on success"]="True"
            else: response["off success"]="True"
        else:
            response={
                "Device Not Found/Error in fetching data"
            }
    elif(args[1]=="listen"):
        Thread(target=state_listener, args=(mydriver, args[1])).start()
    else:
        response = {
            "HTTP Error 400": "Bad Request"
        }
    return response

if __name__ == "__main__":
    main(sys.argv)