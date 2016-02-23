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
		if req["lights"]["L1"] == "true":
			os.system("heyu on L1")
		else:
			os.system("heyu off L1")
		if req["lights"]["L2"] == "true":
			os.system("heyu on L2")
		else:
			os.system("hey off L2")
		return make_response(jsonify({"status" : {"success" : True}}), 200)
	else:
		return make_response(jsonify({"status" : {"success" : False}}), 400)

if __name__ == '__main__':
	app.run(host='0.0.0.0', debug=True)
