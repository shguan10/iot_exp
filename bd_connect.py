import requests
import json

from requests import ConnectionError

class BD_Connect:
	def __init__(self,uid='FV6U2W0fCFEHz8DlWS3dM1nXxeSrldhzD1eKkbwK',ukey='yk5zKMsn8acF5xFEUyDkM1LGIY1ujy6PnRl7o9a53h0GMkXv39',url="https://xinyu-virtualbox.wv.cc.cmu.edu",verify=False):
		self.uid = uid
		self.ukey = ukey
		self.cs_root_url = url+":81/"
		self.ds_root_url = url+":82/"
		self.token = None
		self.verify=verify
		self.get_access_token()

	def get_access_token(self):
		url = self.cs_root_url + "oauth/access_token/client_id=" + self.uid + "/client_secret=" + self.ukey
		try:
			response = requests.get(url,verify=self.verify).json()
		except ConnectionError:
			print "\n\nCould Not Connect to Building Depot, Check URL\n\n"
			raise
		if(response['success']=='True'):
			print("Successful credentials. Your token is: "+ response['access_token'])
			self.token = response['access_token']
			self.headers = {"Authorization": "bearer " + self.token, 'content-type': 'application/json'}
			return self.token
		else:
			print("Incorrect credentials")
			return None

	def post_building(self,name="defaultname",desc="defDesc",template="testbtemplate"):
		data = {
			"data": {
				'name': name,
				"description": desc,
				"template":template
			}
		}
		print json.dumps(data)
		r=requests.post(self.cs_root_url+'api/building',headers=self.headers,data=json.dumps(data),verify=self.verify)
		if (r.content[63:79] == b"401 Unauthorized"):
			self.get_access_token()
			return requests.post(self.cs_root_url+'api/building',headers=self.headers,data=json.dumps(data),verify=self.verify).json()
		return r.json()

	def post_sensor(self, name="defaultsensorname",building="testb",identifier="Sensor Tag"):
		data = {
			"data": {
				'name': name,
				'building': building,
				'identifier': identifier
			}
		}
		print json.dumps(data)
		r=requests.post(self.cs_root_url + 'api/sensor', headers=self.headers, data=json.dumps(data), verify=self.verify)
		if (r.content[63:79] == b"401 Unauthorized"):
			self.get_access_token()
			return requests.post(self.cs_root_url+'api/sensor',headers=self.headers,data=json.dumps(data),verify=self.verify).json()
		return r.json()

	def post_tagtype(self,name="defaulttagtypename",desc="defaultdesc",parents=""):
		data = {
			"data": {
				'name': name,
				'description': desc,
				'Parents': parents
			}
		}
		print json.dumps(data)
		r=requests.post(self.cs_root_url+'api/tagtype',headers=self.headers,data=json.dumps(data),verify=self.verify)
		if (r.content[63:79] == b"401 Unauthorized"):
			self.get_access_token()
			return requests.post(self.cs_root_url+'api/tagtype',headers=self.headers,data=json.dumps(data),verify=self.verify).json()
		return r.json()

	def post_tag_sensor(self, names=["defaulttagtypename"], values=["defaultvalue"], sensorid=["e5fa523e-553c-46d8-bc3f-3458a96da21d"]):
		tags =[]
		for index in xrange(len(names)):
			tags.append(
				{
				"name":names[index],
				"value":values[index]
				}
			)
		data = {
			"data": tags
		}
		print json.dumps(data)
		r=requests.post(self.cs_root_url +'api/sensor/' + sensorid + "/tags", headers=self.headers, data=json.dumps(data), verify=self.verify)
		if (r.content[63:79] == b"401 Unauthorized"):
			self.get_access_token()
			return requests.post(self.cs_root_url +'api/sensor/' + sensorid + "/tags", headers=self.headers, data=json.dumps(data), verify=self.verify).json()
		return r.json()

	def post_time_series(self,payload):
		r = requests.post(self.ds_root_url + 'api/sensor/timeseries', headers=self.headers, data=json.dumps(payload),
							 verify=self.verify)
		#print r
		#print r.content
		if (r.content[63:79] == b"401 Unauthorized"):
			self.get_access_token()
			return requests.post(self.ds_root_url + 'api/sensor/timeseries', headers=self.headers, data=json.dumps(payload),
							 verify=self.verify).json()
		return r.json()

	def search_sensor(self, SourceName=["test"], Source_Identifier=["1234567"], Tags = ["sensorname:wemo"]):
		#TODO build a truly generic implementation of this
		payload = {
			"data": {
				"SourceName":SourceName,
				"SourceIdentifier": Source_Identifier,
				"Tags":Tags
			}
		}
		#TODO the api is extremely abiguous as to the structure of the payload, this cost me an hour to get
		r=requests.post(self.cs_root_url + "api/search", data=json.dumps(payload), headers=self.headers,
					  verify=self.verify)
		if (r.content[63:79] == b"401 Unauthorized"):
			self.get_access_token()
			return requests.post(self.cs_root_url + "api/search", data=json.dumps(payload), headers=self.headers,
					  verify=self.verify).json()
		return r.json()

	def search_sensor_bkup(self, SourceName=["test"], Building=["wemobuilding"], Source_Identifier=["1234567"]):
		#TODO build a truly generic implementation of this
		payload = {
			"data": {
				"Building": Building,
				"Source_Name":SourceName,
				"Source_Identifier": Source_Identifier,
			}
		}
		#TODO the api is extremely abiguous as to the structure of the payload, this cost me an hour to get
		r=requests.post(self.cs_root_url + "api/search", data=json.dumps(payload), headers=self.headers,
					  verify=self.verify)
		if (r.content[63:79] == b"401 Unauthorized"):
			self.get_access_token()
			return requests.post(self.cs_root_url + "api/search", data=json.dumps(payload), headers=self.headers,
					  verify=self.verify).json()
		return r.json()

	def retrieve_timeseries(self,sensoruuid,start_time,end_time,resolution=""):
		url = self.ds_root_url + "api/sensor/"+str(sensoruuid)+"/timeseries?start_time="+str(start_time)+"&end_time="+str(end_time)
		if(resolution is not ""): url+="&resolution="+str(resolution)
		#TODO the url in the api doc is incorrect, this cost me around two hours to fix
		#print url
		r=requests.get(url, headers=self.headers, verify=self.verify)
		if(r.content[63:79]==b"401 Unauthorized"):
			self.get_access_token()
			return requests.get(url, headers=self.headers, verify=self.verify).json()
		return r.json()

#post_sensor(token,name="sudo",building="testb",identifier="sudoidentifier")
#post_tag_sensor(token, sensorid="9abb78c9-8028-42a2-ae52-358faef1eb2b")