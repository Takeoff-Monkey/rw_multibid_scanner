from flask import Flask

application = Flask(__name__)

@application.route("/")
def main():
    return "Hello world!"
