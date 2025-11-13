import os
import requests
import urllib.request
import yaml

from flask import Flask, render_template, jsonify, url_for, request
from flask_cors import CORS, cross_origin
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.firefox.options import Options
from time import sleep

from custom_libs.SQLUtils import SQLUtils as su

app = Flask(__name__)
CORS(app)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['CORS_HEADERS'] = 'Content-Type'

##################
# FUNCTIONS DEFS #
##################

cached_folder = "/home/pi/repos/viewer_app/static/cache/"
existing_files = os.listdir(cached_folder)
[os.remove(os.path.join(cached_folder, x)) for x in existing_files]

def load_creds():
    with open(os.environ['CREDS_PATH']) as file:
        creds = yaml.full_load(file)
    return {'un': creds['un_insta'], 'pw': creds['pw_insta']}

def insta_auth():
    creds = load_creds()

    options = Options()
    options.add_argument('-headless')

    driver = WebDriver(options=options)
    driver.get("https://www.instagram.com/accounts/login/")
    sleep(4)

    ## Find Login buttons
    while True:
        try:
            username_field = driver.find_element_by_name("username")
            password_field = driver.find_element_by_name("password")
            login_button = driver.find_element_by_xpath("//button[@type='submit']")
            break
        except Exception as err:
            print("Was not able to find buttons, waiting a second and trying again...")
            sleep(1)
    try:
        username_field.send_keys(creds['un'])
        password_field.send_keys(creds['pw'])
        login_button.click()
    except Exception as err:
        print("error trying to send keys to un and pw!\nERROR: {}".format(err))
    finally:
        driver.close()


def get_random_link(source: str = "main"):
    eng = su("strobot")
    if source == "main":
        raw_dat_out = eng.execute("SELECT * FROM single_viewer")
    elif source == "best":
        raw_dat_out = eng.execute("SELECT end_link, 'best' as table FROM single_best")

    link = raw_dat_out['end_link'][0]
    table = raw_dat_out['table'][0]

    if '/p/' in link:
        dl_link = insta_fresh(link)
        #####################
        print("piece: {}".format(link))
        print("url: {}".format(dl_link))

        if not dl_link:
            return get_random_link()

        if "accounts/login/" in dl_link:
            print("Encountered a stale insta session, reauthenticating...")
            insta_auth()
            dl_link = insta_fresh(link)

        filename = link.split('/p/')[1].replace("/", "")

        urllib.request.urlretrieve(dl_link, "static/cache/{}.jpg".format(filename))

        return jsonify({'link': url_for('static', filename="cache/{}.jpg".format(filename), _scheme='http', _external=True), 'table': table, 'original_link': link})

    elif 'i.redd.it' in link or 'reddituploads' in link or 'images2' in link:
        if 'i.redd.it' in link:
            filename = "iredd_{}".format(link.split(".")[-2].split("/")[-1])
        elif 'reddituploads' in link:
            filename = "rup_{}".format(link.split('/')[-1])
        elif 'images2' in link:
            filename = "img2_{}".format(link.split('/')[-1])

        try:
            test_resp = requests.get(link)
        except Exception as err:
            print("Could not resolve reddit hosted image: {}\nStatus: {}\nGood chance it's dead.\nERROR: {}".format(link, test_resp.status_code, err))
            return get_random_link()

        if test_resp.status_code != 200:
            kill_non_external(link=link, table_name=table)
            return get_random_link()

        urllib.request.urlretrieve(link, "static/cache/{}.jpg".format(filename))

        return jsonify({'link': url_for('static', filename="cache/{}.jpg".format(filename), _scheme='http', _external=True), 'table': table, 'original_link': link})

    elif 'redgif' in link:
        return get_random_link()

    elif (link.startswith("http://imgur") or link.startswith("https://imgur")):
        bits = link.split("//")
        new_ending = "i."+bits[-1]
        better_link = "//".join([bits[0], new_ending])

        test_resp = requests.get(better_link)
        if test_resp.url == "https://i.imgur.com/removed.png":
            kill_non_external(link=link, table_name=table)

            return get_random_link()

        return jsonify({'link': better_link, 'table': table, 'original_link': link})
    elif (link.startswith("http://i.imgur") or link.startswith("https://i.imgur")):
        test_resp = requests.get(link)
        if test_resp.url == "https://i.imgur.com/removed.png":
            kill_non_external(link=link, table_name=table)
            return get_random_link()
        if test_resp.status_code == 429:
            ## Too many requests, evidently, just skip it. There is a good chance it's been removed, but just in case let's just maintain the db entry
            return get_random_link()

        return jsonify({'link': link, 'table':table, 'original_link': link})
    else:
        return jsonify({'link': link, 'table': table, 'original_link': link})


def insta_fresh(img_link):
    pre_url = "https://www.instagram.com{}media/?size=l".format(img_link)
    request_data = requests.get(pre_url)
    if request_data.status_code != 200:
        return None

    return request_data.url

def kill_non_external(link: str, table_name: str):
    sql_check_cmd = "DELETE FROM {} WHERE end_link='{}'".format(table_name, link)
    try:
        sql_check = su("strobot").execute(sql_check_cmd)
    except Exception as err:
        print("Could not delete row!\n SQL CMD: {}\nERROR: {}".format(sql_check_cmd, err))
    else:
        print(sql_check_cmd)


##########
# ROUTES #
##########

@app.route("/")
@cross_origin()
def main_page():
    link_data = get_random_link(source="main")
    out_hash = {'status': 1, 'link': link_data.json['link'], 'table': link_data.json['table']}

    return render_template("main.html", response=out_hash)

@app.route("/best")
@cross_origin()
def bests_page():
    link_data = get_random_link(source="best")
    out_hash = {'status': 1, 'link': link_data.json['link'], 'table': link_data.json['table']}

    return render_template("best.html", response=out_hash)



###############
# API CALLERS #
###############

@app.route("/viewer_api", methods=["GET", "POST"])
@cross_origin()
def viewer_items():
    source = request.args.get('source')
    raw_dat_out = get_random_link(source=source)

    img_resp = requests.get(raw_dat_out.json['link'])
    print("image data: {}\n image_status: {}".format(raw_dat_out.json, img_resp))

    return raw_dat_out

@app.route("/viewer_post_api", methods=["GET", "POST"])
def post_link_api():
    link = request.args.get('link')
    table_name = request.args.get('table_name')
    sql_check_cmd = "DELETE FROM {} WHERE end_link='{}'".format(table_name, link)

    sql_check = su("strobot").execute(sql_check_cmd)

    print(sql_check_cmd)

    return jsonify({'args_lst':{x: request.args[x] for x in request.args}})

@app.route("/add_to_best", methods=["POST"])
def add_to_best():
    link = request.args.get('end_link')

    check_cmd = """SELECT end_link from best where end_link = '{}'""".format(link)
    check_result = su("strobot").execute(check_cmd)
    if check_result.empty:
        sql_cmd = """INSERT INTO best ("end_link") VALUES ('{}');""".format(link)

        sql_check = su("strobot").execute(sql_cmd)

        print(sql_cmd)

    return jsonify({'args_lst':{x: request.args[x] for x in request.args}})

