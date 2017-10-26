import sys

import time

sys.path.insert(0,'pywemo')
import wemosensor as ws
import bd_connect as bd_c
from threading import Thread

#should start from the user turning on the wemo
#all user needs to input is wemo_bd_driver.start()
#and everything will be done
#   all of the sensing capabilities of the wemo will be added to buildingdepot
#   if already there, then simply get the preexisting uid and use it
#then the driver will periodically receive data from BD, to read it
#print to file?
class Driver:
    def __init__(self):
        self.url = "https://192.168.43.152:82/"
        self.token_url = "https://192.168.43.152:81/"

        self.token = bd_c.BD_Connect(url=self.token_url).get_access_token()

        self.bdc = bd_c.BD_Connect(url=self.url)
        self.bdc.headers = {"Authorization": "bearer " + self.token, 'content-type': 'application/json'}
        self.bdc.token = self.token

        state_id = "77856d08-56ef-46d8-b8d1-509b6316cc3d"
        today_kwh_id = "6719632b-9c19-4b35-a2a3-612ebb7d9614"
        on_for_id = "d4c57c54-9cd5-42b9-879f-861b07d6326f"

        self.sensors = {"state_id":state_id,"today_kwh_id":today_kwh_id,"on_for_id":on_for_id}

        self.dev = ws.mDevice()
        utc_ts=long(time.time())
        r=self.dev.device.timesync.TimeSync(UTC=utc_ts,dst=1,DstSupported=False,TimeZone=1)
        print r

    def start(self):
        for k in xrange(9999999):
            self.sense()
            if(k%10==0): self.retrieve_data()

    def retrieve_data(self):
        #retrieve data from BD and decide whether or not to turn the wemo device off

        pass

    def sense(self):
        # retrieve data from wemosensor and post to BD
        raw_samples = self.dev.sample()
        samples = {
            "state_id": int(raw_samples["state"]),
            "today_kwh_id": float(raw_samples['todaymw'] * 1.6666667e-8),
            "on_for_id": int(raw_samples['onfor'])
        }
        currtime = int(time.time())
        payload = []
        for k in self.sensors:
            payload.append(
                {
                    "sensor_id": self.sensors[k],
                    "samples": [
                        {
                            "value": samples[k],
                            "time": currtime
                        }
                    ]
                }
            )
        r = self.bdc.post_time_series(payload)
        print r
        print r.headers
        print r.content
        time.sleep(1)