from flask import Flask, request
from flask_restful import Api
from flask import got_request_exception
import os
import rollbar
import rollbar.contrib.flask

app = Flask(__name__)
app.config['SECRET_KEY'] = '5791628bb0b13ce0c676dfde280ba245'
api = Api(app)

from creditriskapp import routes
