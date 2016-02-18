#!/usr/bin/env python

import serial
import time
from flask import request
from flask import Flask
from flask import jsonify
from flask import make_response


app = Flask(__name__)

inputa = "4f:82:21:00"
inputb = "4f:82:22:00"
inputc = "4f:82:23:00"
#inputd = "4f:82:24:00"

token = "<API KEY>"

lastLogCallback = ""

inputs = {1:(inputa, "1. Media PC"),
2:(inputb, "2. Aux HDMI"), 
3:(inputc, "3. Chromecast")}
#4:(inputd, "4. Sets the active input on the receiver to this machine - debug only")

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
    global lastLogCallback  
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
      #Pull log message to lastLogCallback
      lastLogCallback = message
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

ser.isOpen()

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
#service is running on. There is no handled input to switch to this 
#machine in an effort to prevent people from attempting to login to the 
#pi to change settings.
#
#Interesting to note, occasionally the Physicall Addresses would switch
#to addresses that started with 1, instead of 2 (e.g. 1.3.0.0).
#I don't know why this happens, a call to lib.lib.GetDevicePhysicalAddress(1)
#returns 5120 in this instance. Check for that.

@app.route('/lounge/receiver/input', methods=["GET", "PUT"])
def lounge_input():
	#store request json
	req = request.get_json()
	input = req["input"]["select"]
	if req["token"]["id"] == token:
		if input == "MediaPC":
			#Change to MediaPC (2.1.0.0)
			lib.ProcessCommandTx("1f:82:21:00")
		elif input == "AuxHDMI":
			#Change to AuxHDMI (2.2.0.0)
			lib.ProcessCommandTx("1f:82:22:00")
		elif input == "Chromecast":
			#Change to Chromecast (2.3.0.0)
			lib.ProcessCommandTx("1f:82:23:00")
		elif input == "Admin":
			#Change to Chromecast (2.4.0.0)
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
#Attempted to treat input status the same way as audio status. Did not work
#def lounge_rinput_status():
#	time.sleep(.25)
#	lib.ProcessCommandTx("1f:85")
#	time.sleep(.25)
#	input_status = lib.lib.GetActiveSource()
#	return input_status

#Projector Control - Old
#
#This is the old implementation of the Projector Control, and has
#yet to be implemented according to the API.
 
@app.route('/proj/on')
def lounge_proj_on():
	ser.write("\r*pow=on#\r")
	return make_response("okay", 200)

@app.route('/proj/off')
def lounge_proj_off():
	ser.write("\r*pow=off#\r")
	return make_response("okay", 200)	

@app.route('/test')
def send_test():
	return make_response(str(lib.lib.GetDevicePhysicalAddress(1)), 200)

if __name__ == '__main__':
	app.run(host='0.0.0.0', debug=True)
