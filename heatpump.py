import requests
from config import config

base_url = 'https://api.melview.net/'
username = config["account"]["username"]
password = config["account"]["password"]
appversion = '3.2.673'

class HeatpumpStatus:
	def __init__(self, json):
		self.id = json['id']
		self.power = json['power']
		self.standby = json["standby"]
		self.setmode = json["setmode"]
		self.automode = json["automode"]
		self.setfan = json['setfan']
		self.settemp = json["settemp"]
		self.roomtemp = json['roomtemp']
		self.airdir = json["airdir"]
		self.airdirh = json["airdirh"]
		self.sendcount = json["sendcount"]
		self.fault = json["fault"]
		self.error = json["error"]

def get_headers(cookie):
	return { 'Cookie': cookie }

def post(cookie, api, data):
	req = requests.post(base_url + api, json=data, headers = get_headers(cookie))
	print(f"{api} result", req.status_code, req.reason)
	if req.status_code == 200:
		return req.json()
	return None


def login():
	data = {
		"user": username,
		"pass": password,
		"appversion": appversion
	}
	req = requests.post(base_url + 'api/login.aspx', json=data)
	print('login result', req.status_code, req.reason)
	if req.status_code == 200:
		return req.headers['Set-Cookie']
	return None

def logout():
	req = requests.post(base_url + 'api/logout.aspx')
	print('logout result', req.status_code, req.reason)

def list_rooms(cookie):
	req = requests.get(base_url + 'api/rooms.aspx', headers = get_headers(cookie))
	print('list_rooms result', req.status_code, req.reason)

	if req.status_code != 200:
		return []

	# don't care about buildings, just get the list of units.
	units = req.json()[0]['units']

	heatpumps = []
	
	for unit in units:
		room = unit['room']
		unitid = unit['unitid']

		print('found room', room, unitid)

		status = get_unit_status(cookie, unitid)

		get_unit_capabilities(cookie, unitid)

		if status != None:
			heatpump = Heatpump(room, unitid, status)
			heatpumps.append(heatpump)

	return heatpumps

def get_unit_capabilities(cookie, unitid):
	return post(cookie, "api/unitcapabilities.aspx", { 'unitid': unitid })

def get_unit_status(cookie, unitid):
	data = {
		'unitid': unitid,
		'v': 2
	}
	res = post(cookie, "api/unitcommand.aspx", data)

	if res != None:
		return HeatpumpStatus(res)
	return None

def send_cmd(cookie, unitid, cmd):
	data = {
		'unitid': unitid,
		'v': 2,
		'commands': cmd
	}
	return post(cookie, "api/unitcommand.aspx", data)

def send_set_power(cookie, unitid, power):
	return send_cmd(cookie, unitid, f"PW{power}")

def send_set_temp(cookie, unitid, temp):
	return send_cmd(cookie, unitid, f"TS{temp}")

def send_set_fan(cookie, unitid, fan):
	return send_cmd(cookie, unitid, f"FS{fan}")

def send_set_mode(cookie, unitid, mode):
	return send_cmd(cookie, unitid, f"MD{mode}")

def get_room(name):
	for room in config["rooms"]:
		if room["name"].lower() == name.lower():
			return room
	return None

def set_power(unitid, power):
	cookie = login()

	if cookie == None:
		return False
		
	if send_set_power(cookie, unitid, power):
		logout()
		return True

	logout()
	return False

def turn_on(unitid):
	return set_power(unitid, 1)

def turn_off(unitid):
	return set_power(unitid, 0)

def get_temp(name):
	cookie = login()

	if cookie == None:
		return "Failed to Login"

	room = get_room(name)

	if room == None:
		logout()
		return f"Failed to find {name}"

	unitid = room["unitid"]

	status = get_unit_status(cookie, unitid)

	if status == None:
		logout()
		return "Failed to get the current heatpump temperature"

	logout()
	return f"The current heatpump temperature is {status.settemp}"

def get_room_temp(name):
	cookie = login()

	if cookie == None:
		return "Failed to Login"

	room = get_room(name)

	if room == None:
		logout()
		return f"Failed to find {name}"

	unitid = room["unitid"]

	status = get_unit_status(cookie, unitid)

	if status == None:
		logout()
		return "Failed to get the current room temperature"

	logout()
	return f"The current room temperature is {status.roomtemp}"

def get_status(unitid):
	cookie = login()

	if cookie == None:
		return "Failed to Login"

	status = get_unit_status(cookie, unitid)

	if status == None:
		logout()
		return "Failed to get the current status"

	logout()
	return status

def set_temp(name, temp):
	cookie = login()

	if cookie == None:
		return "Failed to Login"

	room = get_room(name)

	if room == None:
		logout()
		return f"Failed to find {name}"

	unitid = room["unitid"]

	if send_set_temp(cookie, unitid, temp):
		logout()
		return f'Set temperature on the {name} heatpump to {temp} degrees'
	logout()
	return f'Failed to set temperature on the {name} heatpump'


def set_fan(unitid, fan):
	cookie = login()

	if cookie == None:
		return "Failed to Login"

	if send_set_fan(cookie, unitid, fan):
		logout()
		return True
	logout()
	return False

def set_mode(name, mode):
	mode_num = None
	if mode == "heat" or mode == "heating":
		mode = "heat"
		mode_num = 1
	elif mode == "dry":
		mode_num = 2
	elif mode == "cool" or mode == "cooling":
		mode = "cool"
		mode_num = 3
	elif mode == "fan":
		mode_num = 7
	elif mode == "auto":
		mode_num = 8
	else:
		return "I don't know what mode {mode} is"

	cookie = login()

	if cookie == None:
		return "Failed to Login"

	room = get_room(name)

	if room == None:
		logout()
		return f"Failed to find {name}"
		
	unitid = room["unitid"]

	if send_set_mode(cookie, unitid, mode_num):
		logout()
		return f'Set mode on the {name} heatpump to {mode}'
	logout()
	return f'Failed to set mode on the {name} heatpump'