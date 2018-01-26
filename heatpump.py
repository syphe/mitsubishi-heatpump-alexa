import requests

base_url = 'https://api.melview.net/'
username = ''
password = ''
appversion = '3.2.673'

class HeatpumpStatus:
	power = None
	def __init__(self, json):
		self.power = json['power']
		#"id":
	    #"power": 1,
	    #"standby": 0,
	    #"setmode": 3,
	    #"automode": 0,
	    #"setfan": 1,
	    #"settemp": "19",
	    #"roomtemp": "24",
	    #"airdir": 2,
	    #"airdirh": 3,
	    #"sendcount": 0,
	    #"fault": "",
	    #"error": "ok"

class Heatpump:
	room = None
	unitid = None
	status = None
	def __init__(self, room, unitid, status):
		self.room = room
		self.unitid = unitid
		self.status = status


def get_headers(cookie):
	return { 'Cookie': cookie }

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
	data = {
		'unitid': unitid
	}
	req = requests.post(base_url + 'api/unitcapabilities.aspx', json = data, headers = get_headers(cookie))
	print('get_unit_capabilities result', req.status_code, req.reason)

	if req.status_code != 200:
		return None

	return req.json()

def get_unit_status(cookie, unitid):
	data = {
		'unitid': unitid,
		'v': 2
	}
	req = requests.post(base_url + 'api/unitcommand.aspx', json = data, headers = get_headers(cookie))
	print('get_unit_status result', req.status_code, req.reason)

	if req.status_code != 200:
		return None

	return HeatpumpStatus(req.json())

def send_set_power(cookie, unitid, power):
	data = {
		'unitid': unitid,
		'v': 2,
		'commands': 'PW' + str(power)
	}
	req = requests.post(base_url + 'api/unitcommand.aspx', json = data, headers = get_headers(cookie))
	print('send_set_power result', req.status_code, req.reason)
	return req.status_code == 200

def set_power(name, power):
	cookie = login()

	if cookie == None:
		return 'Login Failed'

	op = 'on' if power == 1 else 'off'

	heatpumps = list_rooms(cookie)

	for heatpump in heatpumps:
		if heatpump.room.lower() == name:
			if heatpump.status.power == power:
				logout()
				return 'Heatpump is already ' + op
			if send_set_power(cookie, heatpump.unitid, power):
				logout()
				return 'Successfully turned ' + op + ' ' + name
			logout()
			return 'Failed to turn ' + op + ' ' + name
	logout()
	return 'Failed to find ' + name

def turn_on(name):
	return set_power(name, 1)

def turn_off(name):
	return set_power(name, 0)