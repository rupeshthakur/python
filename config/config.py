import time 

#==== Below setting needs to update
PORT = "5959"
HOST = '0.0.0.0'
ENV = "DEV"
today = time.strftime("%d-%m-%Y-%H:%M:%S")
date = time.strftime("%d-%m-%Y")
LOGFILE = "logs\\api.log"
DEBUG = True
CONTENT_TYPE = 'application/json'
SQLALCHEMY_DATABASE_URI = 'sqlite:///example.db'
SQLALCHEMY_TRACK_MODIFICATIONS = False