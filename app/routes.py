import os
from flask import render_template
from app import app

#app = flask.Flask("Test App")

@app.route('/')
def index_output():
    user = os.environ['USER']
    return(render_template('index_template_1.html', USER=user))

#if __name__ == "__main__":
#    app.run(host='0.0.0.0')
