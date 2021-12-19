from flask import Flask, render_template, jsonify
from custom_libs import SQLUtils as su


app = Flask(__name__)

##################
# FUNCTIONS DEFS #
##################

def get_random_link():
    raw_dat_out = su.SQLUtils().execute("SELECT end_link FROM single_viewer")
    data_out = raw_dat_out.values.flatten()

    return(data_out[0])


##########
# ROUTES #
##########

@app.route("/")
def hello_world():
    out_hash = {'status': 1, 'link': get_random_link()}

    return(render_template("index.html", response=out_hash))


###############
# API CALLERS #
###############

@app.route("/viewer_api")
def viewer_items():
    raw_dat_out = get_random_link()

    return(raw_dat_out)

