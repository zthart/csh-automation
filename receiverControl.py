#!/usr/bin/env python

import serial
import time
import RPi.GPIO as GPIO
from flask import request
from flask import Flask
from flask import jsonify
from flask import make_response

app = Flask(__name__)

token = "<API KEY>"

sourceChangeCallback = ""
lastKnownSource = "21:00"

import cec
print(cec)

class pyCecClient:
  cecconfig = cec.libcec_configuration()
  lib = {}
  # don't enable debug logging by default
  log_level = cec.CEC_LOG_TRAFFIC

  # create a new libcec_configuration
  def SetConfiguration(self):
    self.cecconfig.strDeviceName   = "pyLibCec"
    self.cecconfig.bActivateSource = 0
    self.cecconfig.deviceTypes.Add(cec.CEC_DEVICE_TYPE_RECORDING_DEVICE)
    self.cecconfig.clientVersion = cec.LIBCEC_VERSION_CURRENT

  def SetLogCallback(self, callback):
    self.cecconfig.SetLogCallback(callback)

  def SetKeyPressCallback(self, callback):
    self.cecconfig.SetKeyPressCallback(callback)

  # detect an adapter and return the com port path
  def DetectAdapter(self):
    retval = None
    adapters = self.lib.DetectAdapters()
    for adapter in adapters:
      print("found a CEC adapter:")
      print("port:     " + adapter.strComName)
      print("vendor:   " + hex(adapter.iVendorId))
      print("product:  " + hex(adapter.iProductId))
      retval = adapter.strComName
    return retval

  # initialise libCEC
  def InitLibCec(self):
    self.lib = cec.ICECAdapter.Create(self.cecconfig)
    # print libCEC version and compilation information
    print("libCEC version " + self.lib.VersionToString(self.cecconfig.serverVersion) + " loaded: " + self.lib.GetLibInfo())

    # search for adapters
    adapter = self.DetectAdapter()
    if adapter == None:
      print("No adapters found")
    else:
      if self.lib.Open(adapter):
        print("connection opened")
      else:
        print("failed to open a connection to the CEC adapter")

  # display the addresses controlled by libCEC
  def ProcessCommandSelf(self):
    addresses = self.lib.GetLogicalAddresses()
    strOut = "Addresses controlled by libCEC: "
    x = 0
    notFirst = False
    while x < 15:
      if addresses.IsSet(x):
        if notFirst:
          strOut += ", "
        strOut += self.lib.LogicalAddressToString(x)
        if self.lib.IsActiveSource(x):
          strOut += " (*)"
        notFirst = True
      x += 1
    print(strOut)

  # send an active source message
  def ProcessCommandActiveSource(self):
    self.lib.SetActiveSource()

  # send a standby command
  def ProcessCommandStandby(self):
    self.lib.StandbyDevices(CECDEVICE_BROADCAST)

  # send a custom command
  def ProcessCommandTx(self, data):
    cmd = self.lib.CommandFromString(data)
    print("transmit " + data)
    if self.lib.Transmit(cmd):
      print("command sent")
    else:
      print("failed to send command")

  # scan the bus and display devices that were found
  def ProcessCommandScan(self):
    print("requesting CEC bus information ...")
    strLog = "CEC bus information\n===================\n"
    addresses = self.lib.GetActiveDevices()
    activeSource = self.lib.GetActiveSource()
    x = 0
    while x < 15:
      if addresses.IsSet(x):
        vendorId        = self.lib.GetDeviceVendorId(x)
        physicalAddress = self.lib.GetDevicePhysicalAddress(x)
        active          = self.lib.IsActiveSource(x)
        cecVersion      = self.lib.GetDeviceCecVersion(x)
        power           = self.lib.GetDevicePowerStatus(x)
        osdName         = self.lib.GetDeviceOSDName(x)
        strLog += "device #" + str(x) +": " + self.lib.LogicalAddressToString(x)  + "\n"
        strLog += "address:       " + str(physicalAddress) + "\n"
        strLog += "active source: " + str(active) + "\n"
        strLog += "vendor:        " + self.lib.VendorIdToString(vendorId) + "\n"
        strLog += "CEC version:   " + self.lib.CecVersionToString(cecVersion) + "\n"
        strLog += "OSD name:      " + osdName + "\n"
        strLog += "power status:  " + self.lib.PowerStatusToString(power) + "\n\n\n"
      x += 1
    print(strLog)

  # logging callback
  def LogCallback(self, level, time, message):
    global sourceChangeCallback 
    if level > self.log_level:
      return 0

    if level == cec.CEC_LOG_ERROR:
      levelstr = "ERROR:   "
    elif level == cec.CEC_LOG_WARNING:
      levelstr = "WARNING: "
    elif level == cec.CEC_LOG_NOTICE:
      levelstr = "NOTICE:  "
    elif level == cec.CEC_LOG_TRAFFIC:
      levelstr = "TRAFFIC: "
      #If the message is a broadcast from the audio system
      #specifying a routing change, store it in sourceChangeCallback
      if message.find("5f:80") > 0:
          sourceChangeCallback = message
          lounge_sourceChanged()
    elif level == cec.CEC_LOG_DEBUG:
      levelstr = "DEBUG:   "

    print(levelstr + "[" + str(time) + "]     " + message)
    return 0

  # key press callback
  def KeyPressCallback(self, key, duration):
    print("[key pressed] " + str(key))
    return 0

  def __init__(self):
    self.SetConfiguration()

# logging callback
def log_callback(level, time, message):
  return lib.LogCallback(level, time, message)

# key press callback
def key_press_callback(key, duration):
  return lib.KeyPressCallback(key, duration)

#Set up serial communications with the projector
ser = serial.Serial(
	port='/dev/ttyUSB0',
	baudrate=115200,
	parity=serial.PARITY_NONE,
	stopbits=serial.STOPBITS_ONE,
	bytesize=serial.EIGHTBITS
)

if not ser.isOpen():
    ser.open()
else:
    ser.close()

#LibCEC stuff, should be eventually culled back to what we actually need
lib = pyCecClient()
lib.SetLogCallback(log_callback)
lib.SetKeyPressCallback(key_press_callback)
lib.InitLibCec()

#Receiver Input Control
#
#A successful request will change the currently selected input on the
#receiver. The currently connected devices are the MediaPC, the 
#AuxHDMI cable for presentations, the Chromecast, and the RPi that this
#service is running on.

@app.route('/lounge/receiver/input', methods=["GET", "PUT"])
def lounge_input():
        global lastKnownSource
	#store request json
	req = request.get_json()
	input = req["input"]["select"]
	if req["token"]["id"] == token:
		if input == "MediaPC":
			#Change to MediaPC (2.1.0.0)
                        lastKnownSource = "21:00"
			lib.ProcessCommandTx("1f:82:21:00")
		elif input == "AuxHDMI":
			#Change to AuxHDMI (2.2.0.0)
                        lastKnownSource = "22:00"
			lib.ProcessCommandTx("1f:82:22:00")
		elif input == "Chromecast":
			#Change to Chromecast (2.3.0.0)
                        lastKnownSource = "23:00"
			lib.ProcessCommandTx("1f:82:23:00")
		elif input == "Admin":
			#Change to Chromecast (2.4.0.0)
                        lastKnownSource = "24:00"
			lib.ProcessCommandTx("1f:82:24:00")
		else:
			#If no proper input was selected
			return make_response(jsonify({"status" : {"success":False}}), 400)
		#If an available input was selected and switched
		return make_response(jsonify({"status" : {"success":True}}), 200)
	else:
		#If the provided token was incorrect
		return make_response(jsonify({"status" : {"success":False}}), 400)

#Mute Control                                                         
#                                                                     
#A successful request will send commands to emulate a user pressing   
#the mute button on the receiver remote, then releasing it.           
#The mute command is the only command that requires we actually      
#release the selected button - as all the others have a desired      
#behavior of sending multiple inputs, whereas the mute button should
#only be pressed once in order to correctly mute the machine.
#
#To compensate for not being able to get a clear status from the
#reciever as to its volume/mute state, the assumed mute state is off when the
#service starts. Since this is the case most often, the downsides
#to this assumption are relatively small. Care should be taken when
#restarting this service that the receiver is in an unmuted state
#in order for the service to keep a correct status for the receiver

@app.route('/lounge/receiver/mute', methods=["GET", "PUT"])
def lounge_mute():
	#store request json	
	req = request.get_json()
	if req["token"]["id"] == token:
		#send user control pressed, then user control released
		lib.ProcessCommandTx("15:44:43")
		lib.ProcessCommandTx("15:45")
		lib.ProcessCommandTx("15:71")
		
		if lounge_audio_status() > 127:
			return make_response(jsonify({"status" : {"success":True,"state":1}}),200)
		else:
			return make_response(jsonify({"status" : {"success":True,"state":0}}),200)
	else:
		#if the request token is invalid
		return make_response(jsonify({"status" : {"success":False,"state":isMuted}}),400) 

#Volume Control
#
#A successful request will send either a volume up (1), or volume down (0)
#command, along with a command to ask the receiver for it's current audio status.
#The service will then return whether or not the volume change was successful,
#and the current audio status. the audio status reports volume from 1-80, mapped
#to 1-127. Any number larger than 127 reported as an audio status means
#the system is presently muted.
#
#Any requests with a control type less than 0 or larger than 1 will return the
#last known audio status, and "success" as 'False'. Requests with an invalid
#API Key receive the same return status.

@app.route('/lounge/receiver/volume', methods=["GET", "PUT"])
def lounge_volume():
	req = request.get_json()
	if req["token"]["id"] == token:
		if req["control"]["type"] == 1:
			lib.ProcessCommandTx("15:44:41")
			lib.ProcessCommandTx("15:71")
			time.sleep(.5)
			return make_response(jsonify({"status" : {"success":True, "level" : lounge_audio_status()}}), 200)
		elif req["control"]["type"] == 0:
			lib.ProcessCommandTx("15:44:42")
			lib.ProcessCommandTx("15:71")
			time.sleep(.5)
			return make_response(jsonify({"status" : {"success":True, "level" : lounge_audio_status()}}), 200)
		else:
			return make_response(jsonify({"status" : {"success":False, "level" : lounge_audio_status()}}), 400)
	else:
		return make_response(jsonify({"status" : {"success":False, "level" : lounge_audio_status()}}), 400)

#Refresh Audio Status
#
#Asks the Receiver for its updated audio status, then waits long enough
#for its response. Returns a value between 1-127 for unmuted volumes,
#returns the previous audio value plus 128 for muted volumes.
def lounge_audio_status():
	lib.ProcessCommandTx("15:71")
	time.sleep(.5)
	audio_status = lib.lib.AudioStatus()
	return audio_status 

#Refresh Input Status
#
#Each time a broadcast from the audio system that signifies a routing 
#change, the assumed source is checked against the reported source, as a
#means to keep track of changes to the receiver's source via the front
#panel on the receiver.
def lounge_sourceChanged():
        global lastKnownSource
        global sourceChangeCallback
        if lastKnownSource != sourceChangeCallback[15:]:
            lastKnownSource = sourceChangeCallback[15:]
            return True
        else:
            return False

#Receiver Status
#
#Reports the current status of the receiver
@app.route('/lounge/receiver', methods=["GET", "PUT"])
def lounge_receiver():
    global lastKnownSource
    sources = {"HDMI 1" : "Media PC",
            "HDMI 2" : "Aux HDMI",
            "HDMI 3" : "Chromecast",
            "HDMI 4" : "Raspberry PI"}
    recInput = ""
    if lastKnownSource == "21:00":
        recInput = "HDMI 1"
    elif lastKnownSource == "22:00":
        recInput = "HDMI 2"
    elif lastKnownSource == "23:00":
        recInput = "HDMI 3"
    elif lastKnwonSource == "24:00":
        recInput = "HDMI 4"

    recMute = False
    if lounge_audio_status() > 127:
        recMute = True
    else:
        revMute = False

    recVolume = 0
    if lounge_audio_status() > 127:
        recVolume = lounge_audio_status() - 128
    else:
        recVolume = lounge_audio_status()

    recStatus = {"input" : recInput,
            "mute" : recMute,
            "sources" : sources,
            "volume" : recVolume}

    response = {"receiver" : recStatus, "status" : {"success" : True}}
    return make_response(jsonify(response), 200) 

###
#Projector Controls
#
#Each time a projector control is called the serial port is opened,
#written to and/or read from, flushed, then closed in order to keep
#instructions from being misread or miswritten.
###

#Projector Power Control
#
#Sends power commands over serial to the projector, takes either a string
#"true" or "false" for "on" and "off" respectively. Response code 412 is 
#used in instances in which the projectors status cannot be acquired.
#It is safe to assume that in these moments the projector is cooling down,
#or is unreachable via serial.
@app.route('/lounge/projector/power', methods=["GET", "PUT"])
def lounge_projpower():
	req = request.get_json()
        ser.open()
	if req["token"]["id"] == token:
		if req["power"]["state"] == "true":
			ser.write("\r*pow=on#\r")
                        ser.flush()
                        ser.readline()
                        if ser.readline().find("ON") > 0:
                            ser.flush()
                            ser.close()
			    return make_response(jsonify({"status" : {"success":True}}), 200)
                        else:
                            ser.flush()
                            ser.close()
                            return make_response(jsonify({"status" : {"success":False}}), 412)
		elif req["power"]["state"] == "false":
			ser.write("\r*pow=off#\r")
                        ser.flush()
                        ser.readline()
                        if ser.readline().find("OFF") > 0:
                            ser.flush()
                            ser.close()
			    return make_response(jsonify({"status" : {"success":True}}), 200)
                        else:
                            ser.flush()
                            ser.close()
                            return make_response(jsonify({"status" : {"success":False}}), 412)
		else:
                        ser.close()
			return make_response(jsonify({"status" : {"success":False}}), 400)
	else:
                ser.close()
		return make_response(jsonify({"status" : {"success":False}}), 400)

#Projector Blank Control
#
#Checks the current blank status of the projector, and toggles it.
@app.route('/lounge/projector/blank', methods=["GET", "PUT"])
def lounge_projblank():
        req = request.get_json()
        ser.open()
        ser.write("\r*blank=?#\r")
        ser.flush()
        ser.readline()
        status = ser.readline()
        if req["token"]["id"] == token:
            if status.find("ON") > 0:
                print(status)
                ser.write("\r*blank=off#\r")
                ser.flush()
                ser.close()
                return make_response(jsonify({"status" : {"success":True}}), 200)
            else:
                print(status)
                ser.write("\r*blank=on#\r")
                ser.flush()
                ser.close()
                return make_response(jsonify({"status" : {"success":True}}), 200)
        else:
            ser.flush()
            ser.close()
            return make_response(jsonify({"status" : {"success":False}}), 400)
#Projector Input Control
#
#Changes the current input on the projector
@app.route('/lounge/projector/input', methods=["GET", "PUT"])
def lounge_projinput():
        req = request.get_json()
        ser.open()
        source = req["input"]["select"]
        if req["token"]["id"] == token:
            if source == "HDMI2":
                ser.write("\r*sour=hdmi2#\r")
                ser.flush()
                ser.close()
                return make_response(jsonify({"status" : {"success":True}}), 200)
            elif source == "HDMI":
                ser.write("\r*sour=hdmi#\r")
                ser.flush()
                ser.close()
                return make_response(jsonify({"status" : {"success":True}}), 200)
            elif source == "Component":
                ser.write("\r*sour=ypbr#\r")
                ser.flush()
                ser.close()
                return make_response(jsonify({"status" : {"success":True}}), 200)
            elif source == "Computer1":
                ser.write("\r*sour=RGB#\r")
                ser.flush()
                ser.close()
                return make_response(jsonify({"status" : {"success":True}}), 200)
            elif source == "Computer2":
                ser.write("\r*sour=RGB2#\r")
                ser.flush()
                ser.close()
                return make_response(jsonify({"status" : {"success":True}}), 200)
            else:
                ser.close()
                return make_response(jsonify({"status" : {"success":False}}), 400)
        else:
            ser.close()
            return make_response(jsonify({"status" : {"success":False}}), 400)

#Queries the status of the projector, and returns the current blank status,
#lamp hours, input, power status, and sources list.
@app.route('/lounge/projector', methods=["GET", "PUT"])
def lounge_proj():
        sources = {"Composite": None,
                "Computer 1": "Aux VGA",
                "Computer 2": None,
                "HDMI 1": None,
                "HDMI 2": "Receiver"}
        currentInput = lounge_proj_getCurrentSource()
        currentPower = lounge_proj_getCurrentPower()
        currentHours = lounge_proj_getCurrentHours()
        currentBlank = lounge_proj_getCurrentBlank()

        currentStatus = {"blank":currentBlank,
                "hours":currentHours,
                "input":currentInput,
                "power":currentPower,
                "sources": sources}
        return make_response(jsonify({"projector" : currentStatus, "status" : {"success" : True}}), 200)

#Returns the current blank status of the Projector
def lounge_proj_getCurrentBlank():
    ser.open()
    ser.write("\r*blank=?#\r")
    ser.flush()
    ser.readline()
    blankline = ser.readline()
    ser.close()
    if blankline.find("ON") > 0:
        return True
    else:
        return False

#Returns the current lamp hours of the Projector
def lounge_proj_getCurrentHours():
    ser.open()
    ser.write("\r*ltim=?#\r")
    ser.flush()
    ser.readline()
    hourline = ser.readline()
    ser.close()
    return hourline[6:-3]

#Returns the current power status of the Projector
def lounge_proj_getCurrentPower():
    ser.open()
    ser.write("\r*pow=?#\r")
    ser.flush()
    ser.readline()
    powline = ser.readline()
    if powline.find("ON") > 0:
        ser.close()
        return True
    else:
        ser.close()
        return False

#Returns the current source of the Projector
def lounge_proj_getCurrentSource():
    ser.open()
    ser.write("\r*sour=?#\r")
    ser.flush()
    ser.readline()
    sourceline = ser.readline()
    if sourceline.find("RGB") > 0:
        if sourceline.find("2") > 0:
            ser.close()
            return "Computer 2"
        else:
            ser.close()
            return "Computer 1"
    elif sourceline.find("HDMI") > 0:
        if sourceline.find("2") > 0:
            ser.close()
            return "HDMI 2"
        else:
            ser.close()
            return "HDMI 1"
    elif sourceline.find("YPBR") > 0:
        ser.close()
        return "Composite"
    else:
        ser.close()
        return "Error"

#Setup for GPIO Control
GPIO.setmode(GPIO.BOARD)
backRadiatorStatus = False;
backRadiator = 3
GPIO.setup(backRadiator, GPIO.OUT)

#Radiator Control
#
#Controls the radiator behind the risers via the GPIO on the Pi, using 
#the RPi.GPIO Python Library
@app.route('/lounge/radiator', methods=["GET", "PUT"])
def lounge_radiator():
    global backRadiatorStatus
    if request.method == 'GET':
        return make_response(jsonify({"status" : {"success" : True}, "radiator" : {"fan" : backRadiatorStatus}}), 200)
    else:
        req = request.get_json()
        if req["token"]["id"] == token:
            if req["radiator"]["fan"] == True:
                GPIO.output(backRadiator, True)
                backRadiatorStatus = True
            else:
                GPIO.output(backRadiator, False)
                backRadiatorStatus = False
            return make_response(jsonify({"status" : {"success" : True}}), 200)
        else:
            return make_response(jsonify({"status" : {"success" : False}}), 400)

if __name__ == '__main__':
	app.run(host='0.0.0.0', debug=True)
