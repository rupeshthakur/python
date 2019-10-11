#!/usr/bin/python
#==== Python FLask API modules ==========
from flask import Flask, request, Response, jsonify, json, Blueprint, current_app, make_response, render_template
from werkzeug.contrib.fixers import ProxyFix
#=======Flask Security =========
#from flask_security import auth_token_required, utils
import base64
from six import string_types
#=====Log related modules ==============
import logging
import sys
from time import strftime
#===CORS related modules =================
# from flask_cors import CORS
from datetime import datetime, timedelta
from functools import update_wrapper
import socket
# from logstashHandler import logstashHandler
from json import dumps
import math
import re
import os
#====DB related modules========
from flask_sqlalchemy import SQLAlchemy

# Import custom modules & packages.
from classifier import model

# Load classifier
clf = model.Model()
text_clf = clf.loadmodel()
le = clf.loadcategory()
#============================================
class ReverseProxied(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        script_name = environ.get('HTTP_X_SCRIPT_NAME', '')
        if script_name:
            environ['SCRIPT_NAME'] = script_name
            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]
        scheme = environ.get('HTTP_X_SCHEME', '')
        if scheme:
            environ['wsgi.url_scheme'] = scheme
        return self.app(environ, start_response)
#==============Flask main Object===============
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)
app.wsgi_app = ReverseProxied(app.wsgi_app)
#==============CORS settings ==================
#CORS(app, headers=['Content-Type'])
# CORS(app)
#==============Environment Specific Config File=========
app.config.from_pyfile(sys.argv[1])

#============= Configfile variables ==================
host = app.config['HOST']
port = app.config['PORT']
debugger = app.config['DEBUG']
logfile = app.config['LOGFILE']
dir_path = os.path.dirname(os.path.realpath(__file__))
logfile = dir_path + os.sep+logfile
db = SQLAlchemy(app)
#==============local file Logger==========================
logFormatStr = ('[%(asctime)s]-[p%(process)s]-[%(filename)s-%(lineno)s-%(module)s-%(funcName)s]-[%(pathname)s]-[%(name)s]-[%(levelname)s]-[%(message)s]')
formatter = logging.Formatter(logFormatStr)
streamHandler = logging.StreamHandler()
info = app.logger.info
error = app.logger.error
warning = app.logger.warning
logging.basicConfig(format=logFormatStr, filename=logfile, level=logging.DEBUG)
streamHandler.setLevel(logging.DEBUG)
streamHandler.setFormatter(formatter)
app.logger.addHandler(streamHandler)
#==============End Configuration==============
def crossdomain(origin=None, methods=None, headers=None, max_age=21600, attach_to_all=True, automatic_options=True):
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, string_types):
        headers = ', '.join(x.upper() for x in headers)
        print(headers)
    if not isinstance(origin, string_types):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        if methods is not None:
            return methods

        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']
    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers
            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
                #h['Access-Control-Allow-Headers'] = "Content-Type"
            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)
    return decorator

def save_prediction(data):
    # with sqlite3.connect('example.db') as conn:
    #     c = conn.cursor()
    #     c.execute("INSERT INTO stocks VALUES (datetime('now'),'BUY','RHAT',100,35.14)")
    #     conn.commit()
    try:
        prediction = Prediction(
            id=data['id'],
            title=data['title'],
            body=data['body'],
            category=data['category'],
            insert_datetime=datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            )
        db.session.add(prediction)
        db.session.commit()
    except Exception as e:
        warning(e)

class Prediction(db.Model):
    id = db.Column(db.String(20), primary_key=True)
    title = db.Column(db.Text, nullable=False)
    body = db.Column(db.Text)
    category = db.Column(db.String(15))
    insert_datetime = db.Column(db.String(20))


class TicketNumber:
    def __init__(self):
        _record = Prediction.query.filter(Prediction.id.startswith('ID-')).order_by(Prediction.id.desc()).first()
        _tag, _seq = _record.id.split(sep='-')
        self.current_number=int(_seq)

    def nextnumber(self):
        num=self.current_number + 1
        self.current_number = num
        return num
    
    def get_ticket_number(self):
        return self.current_number

#===============Router======================
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/predict', methods=['GET', 'POST', 'OPTIONS'])
@crossdomain(origin='*', headers='Content-Type')
def predict_api():
    '''
    request.json is the json payload sent by client
    request.headers will have header settings
    Response first parameter is json payload.

    '''
    info("Function pridict executing...")
    print(request.json)
    try:
        if request.method == "POST" and request.headers['Content-Type'] == app.config["CONTENT_TYPE"]:
            user_payload = request.json
            '''
            Custom Modification to go here for POST call
            '''
            if user_payload['title']:
                prediction = text_clf.predict([user_payload['title']])
                prediction = list(map(int,prediction)) 
                probability = text_clf.predict_proba([user_payload['title']]).tolist()
                probability_in_percent = [math.floor(x*100) for x in probability[0]]
                info(prediction)
                info(probability)
                prediction_inverse = le.inverse_transform(prediction)
                prediction_categories = le.classes_.tolist()
                info(prediction_inverse)
                # Prepare record to save in DB, before return
                record = {}
                # Set appropriate Ticket ID
                '''Using UI, generate automatically,
                if via api, use from API payload
                '''
                try:
                    record['id'] = user_payload['id']
                except:
                    record['id'] = 'ID' + '-' + str(t_seq.nextnumber())
                record['title'] = user_payload['title']
                record['body'] = user_payload['description']
                record['category'] = prediction_inverse[0]
                # Save to DB
                save_prediction(record)
                # Return the response if error return in the Exception.
                return Response(json.dumps({
                    "category": prediction_inverse[0],
                    "probability":probability_in_percent,
                    "categories":prediction_categories
                    }),
                    status=200, 
                    mimetype='application/json')
            else:
                return Response(json.dumps({
                    "category": "Please fill Title & Description",
                    "probability":"NULL",
                    "categories": [0,0,0] 
                    }),
                    status=200,
                    mimetype='application/json')
        if request.method == 'GET' and request.headers['Content-Type'] == app.config["CONTENT_TYPE"]:
            user_payload = request.json
            '''
            Custom Modification to go here for GET call
            '''
            return Response(json.dumps({"result":"ok"}), status=200, mimetype='application/json')
    except Exception as e:
        error("Exception detected. Error is : {}".format(e))
        '''
        Custom Modification end here
        '''
        return Response(json.dumps({"result":"Error"}), status=401, mimetype='application/json')
    return Response(json.dumps({"result":"not ok"}), status=400, mimetype='application/json')


#===============Main method==============================
if __name__ == "__main__":
    print("...Connecting DB")
    db.create_all()
    t_seq = TicketNumber()
    print("...Ticket Sequence Number is ID-{0}".format(t_seq.get_ticket_number()))
    print("** API running on port: " + port)
    app.run(host, int(port), debug=True)

