#!/usr/bin/env python

import os
import sys
from flask import request
from flask import Flask
from flask import jsonify
from flask import make_response

app = Flask(__name__)

token = "<API KEY>"

@app.route('/lounge/lights', methods=["GET","PUT"])
def lounge_lights():
	req = request.get_json()
	if req["token"]["id"] == token:
		if req["lights"]["L1"] == True:
			os.system("heyu on L1")
		elif req["lights"]["L1"] == False:
			os.system("heyu off L1")
		else:
			return make_response(jsonify({"status" : {"success" : False}}), 412)
		if req["lights"]["L2"] == True:
			os.system("heyu on L2")
		elif req["lights"]["L2"] == False:
			os.system("heyu off L2")
		else:
			return make_response(jsonify({"status" : {"success" : False}}), 412)
		return make_response(jsonify({"status" : {"success" : True}}), 200)
	else:
		return make_response(jsonify({"status" : {"success" : False}}), 400)

if __name__ == '__main__':
	app.run(host='0.0.0.0', debug=True)
