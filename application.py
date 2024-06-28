from flask import Flask
from flask import request

application = Flask(__name__)

@application.route("/", methods=['GET', 'POST'])
def main():
    return "Hello world!"

if __name__ == "__main__":
    application.run()