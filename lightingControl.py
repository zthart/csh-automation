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
        for light, value in req["lights"].items():
            print(light, value)

            if light == "L1":
                if value == True:
                    os.system("heyu on L1");
                elif value == False:
                    os.system("heyu off L1");
                else:
                    return make_response(jsonify({"status" : {"success" : False}}), 412)
            elif light == "L2":
                if value == True:
                    os.system("heyu on L2");
                elif value == False:
                    os.system("heyu off L2");
                else:
                    return make_response(jsonify({"status" : {"success" : False}}), 412)
            else:
                return make_response(jsonify({"status" : {"success" : False}}), 400)
        return make_response(jsonify({"status" : {"success" : True}}), 200)
    else:
        return make_response(jsonify({"status" : {"success" : False}}), 400)

if __name__ == '__main__':
	app.run(host='0.0.0.0', debug=True)
