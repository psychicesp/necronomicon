from flask import Flask

def preach(config):
    app = Flask(__name__)


    @app.route('/')
    def hello():
        return 'Hello, World!'