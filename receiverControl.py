#!/usr/bin/env python
import os
import sys
import serial
from flask import Flask
from flask import jsonify
from flask import make_response

app = Flask(__name__)

inputa = "echo \"tx 4f:82:21:00\" | cec-client -s"
inputb = "echo \"tx 4f:82:22:00\" | cec-client -s"
inputc = "echo \"tx 4f:82:23:00\" | cec-client -s"
#inputd = "echo \"tx 4f:82:24:00\" | cec-client -s"

inputs = {1:(inputa, "1. Sets the active input on the receiver to the Media PC"),
2:(inputb, "2. Sets the active input on the receiver to Aux HDMI"), 
3:(inputc, "3. Sets the active input on the receiver to the Chromecast")}
#4:(inputd, "4. Sets the active input on the receiver to this machine - debug only")

ser = serial.Serial(
	port='/dev/ttyUSB0',
	baudrate=115200,
	parity=serial.PARITY_NONE,
	stopbits=serial.STOPBITS_ONE,
	bytesize=serial.EIGHTBITS
)

ser.isOpen()

@app.route('/input/<int:id>')
def lounge_input(id):
	if id > 4 or id < 1:
		return make_response("fuckoff", 400)
	
	print(id)
	print(inputs)

	os.system(inputs[id][0])

	return make_response("okay", 200)

@app.route('/')
def lounge_help():
	return make_response(jsonify(inputs), 200)

@app.route('/vol/up')
def lounge_vol_up():
	os.system("echo \"tx 15:44:41 \" | cec-client -s")
	return make_response("okay", 200)
@app.route('/vol/down')
def lounge_vol_down():
	os.system("echo \"tx 15:44:42\" | cec-client -s")
	return make_response("okay", 200)
@app.route('/vol/mute')
def lounge_vol_mute():
	#Doesn't work properly
	#These commands are being sent as button presses
	#I think mute doesn't actually apply until button release
	#And I can't send two commands before closing the client
	os.system("echo \"tx 14:44:43\" | cec-client -s")
	#os.system("echo \"tx 15:45\" | cec-client -s")
	return make_response("okay", 200)

@app.route('/proj/on')
def lounge_proj_on():
	ser.write("\r*pow=on#\r")
	return make_response("okay", 200)

@app.route('/proj/off')
def lounge_proj_off():
	ser.write("\r*pow=off#\r")
	return make_response("okay", 200)

@app.route('/proj/status')
def lounge_proj_status():
	ser.write("\r*pow=?#\r")
	return make_response("okay", 200)


if __name__ == '__main__':
	app.run(host='0.0.0.0', debug=True)
