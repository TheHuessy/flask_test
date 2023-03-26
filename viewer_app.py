import os
import requests
import urllib.request

from flask import Flask, render_template, jsonify, url_for
#from flask_cors import CORS
from flask_cors import CORS, cross_origin
from custom_libs.SQLUtils import SQLUtils as su


app = Flask(__name__)
CORS(app)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['CORS_HEADERS'] = 'Content-Type'
##################
# FUNCTIONS DEFS #
##################

def get_random_link():
    # raw_dat_out = su.SQLUtils("strobot").execute("SELECT end_link FROM single_viewer")
    raw_dat_out = su("strobot").execute("SELECT end_link FROM single_viewer")
    ######################
    print("RAW_DAT_OUT: {}".format(raw_dat_out))
    ######################
    link = raw_dat_out.values.flatten()[0]
    if '/p/' in link:
        dl_link = insta_fresh(link)
        #####################
        print("piece: {}".format(link))
        print("url: {}".format(dl_link))
        ####################
        if not dl_link:
            return get_random_link()
        cached_folder = "/home/pi/repos/viewer_app/static/cache/"
        existing_files = os.listdir(cached_folder)
        [os.remove(os.path.join(cached_folder, x)) for x in existing_files]
        filename = link.split('/p/')[1].replace("/", "")

        ##########################
        print("Attempting File Save {}".format(dl_link))
        ##########################

        urllib.request.urlretrieve(dl_link, "static/cache/{}.jpg".format(filename))

        # return url_for('static', filename="cache/{}.jpg".format(filename))
        # return url_for('static', filename="cache/{}.jpg".format(filename), _external=False)
        # return url_for('static', filename="cache/{}.jpg".format(filename), _external=True)
        # return url_for('static', filename="cache/{}.jpg".format(filename), _scheme='file', _external=True)
        # return url_for('static', filename="cache/{}.jpg".format(filename), _scheme='file', _external=False)
        return url_for('static', filename="cache/{}.jpg".format(filename), _scheme='http', _external=True)
    else:

        return link


def insta_fresh(img_link):
    pre_url = "https://www.instagram.com{}media/?size=l".format(img_link)

    ###########
    print("insta_fresh attempt for '{}' ...".format(pre_url))
    ###########

    request_data = requests.get(pre_url)

    ###########
    print("request value: {}".format(request_data))
    ###########

    if request_data.status_code != 200:
        return None
    return request_data.url


##########
# ROUTES #
##########

@app.route("/")
@cross_origin()
def main_page():
    out_hash = {'status': 1, 'link': get_random_link()}

    return(render_template("index.html", response=out_hash))


###############
# API CALLERS #
###############

@app.route("/viewer_api")
def viewer_items():
    raw_dat_out = get_random_link()

    #######################
    img_resp = requests.get(raw_dat_out)
    print("image data: {}\n image_status: {}".format(raw_dat_out, img_resp))
    #######################

    return(raw_dat_out)

