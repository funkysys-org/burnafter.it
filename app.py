import os, sys, urllib, json, random, re, time, datetime, subprocess, tempfile, time, secrets, io, base64
import boto3, redis, qrcode
from botocore.exceptions import ClientError
from botocore.client import Config
from flask import Flask, render_template, render_template_string, request, flash, redirect, session, g, url_for, jsonify, Response, send_from_directory, send_file
from flask_debugtoolbar import DebugToolbarExtension
from flask_session import Session
from datetime import timedelta
from passlib.apps import custom_app_context as pwd_context
from datetime import datetime
from unidecode import unidecode
from functools import wraps
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from flask_mobility import Mobility
#from PIL import Image
from io import BytesIO
#o = urlparse(request.base_url)
app = Flask(__name__)
Mobility(app)

#minio s3 ad-hoc config
s3config = Config(
   signature_version = 's3v4'
)
#use_redis = 1
use_redis = 0
config_file = 'config.json'
if not os.path.isfile(config_file):
    app.logger.error(
        "Your config.json file is missing." +
        "You need to create one in order for this demo app to run."
    )
else:
    #app.config.from_json(config_file)
    app.config.from_file(config_file, json.load)

app.config['SECRET_KEY'] = secrets.token_urlsafe(32)
app.secret_key = secrets.token_urlsafe(32)
#remove these four lines to disable redis-sessions
if use_redis == 1:
    app.config['VHOST_WEBSITE'] = "burnafter.it"
    app.config['SESSION_TYPE']="redis"
    app.config['SESSION_PERMANENT']=False
    app.config['SESSION_USE_SIGNER']=True
    app.config['SESSION_REDIS'] = redis.from_url('redis://' + app.config['REDIS_USER']  + ':' + app.config['REDIS_PASS'] + '@' + app.config['REDIS_HOST'] + ':' + app.config['REDIS_PORT'])
else:
    app.config['VHOST_WEBSITE'] = "burnafter.it"
    app.config['SESSION_TYPE'] = 'filesystem' 
    app.config['SESSION_PERMANENT']= False
    
server_session = Session(app)

@app.before_request
def pre_process_all_requests():
    app.config['VHOST_WEBSITE'] = request.host_url.split('/')[2]
    user = session.get('user')
    if user:
        g.current_user = user
        g.logged_in = True
    else:
        g.logged_in = False
        g.current_user = None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        if request.url.startswith('http://'):
            url = request.url.replace('http://', 'https://', 1)
        else:
            url = request.url
        if g.current_user is None:
            return redirect('https://' + app.config['VHOST_WEBSITE'] + '/?next=' + url)
        return f(*args, **kwargs)
    return decorated_function

def generate_stream(shouthash,shouttype):
    try:
        botoclient = boto3.client('s3',endpoint_url=app.config['S3_ENDPOINT_URL'], aws_access_key_id=app.config['S3_ACCESS_KEY'], aws_secret_access_key=app.config['S3_SECRET_KEY'], config=boto3.session.Config(signature_version='s3v4') )
        ext = '.wav'
        if shouttype == 'video':
            ext = '.mp4'
        object_data = botoclient.get_object(Bucket=app.config['S3_BUCKET'], Key=shouthash + ext)
        data = object_data['Body'].read(1024)
        while data:
            yield data
            data = object_data['Body'].read(1024)
    except:
         data = None

def add_user(username,email,password):
    # working fine but disabled, since all the processes of reset and mail notification have not yet been implemented
    #return False
    if not validate_user(username):
        try:
            with InfluxDBClient(url=app.config['INFLUX_ENDPOINT_URL'], token=app.config['INFLUX_TOKEN'], org=app.config['INFLUX_ORG']) as client:
                write_api = client.write_api(write_options=SYNCHRONOUS)
                hashedpass = pwd_context.hash(password)
                data = 'users,user=' + username + ',email=' + email + ' pass="' + hashedpass + '"'
                write_api.write(app.config['INFLUX_BUCKET'], app.config['INFLUX_ORG'], data)
            return True 
        except:
            print("puppa add_user")
            return False 
    else:
        return False

def validate_user(username):
    try:
        client = InfluxDBClient(url=app.config['INFLUX_ENDPOINT_URL'], token=app.config['INFLUX_TOKEN'], org=app.config['INFLUX_ORG'])
        response = client.query_api().query('from(bucket: "' + app.config['INFLUX_BUCKET'] +'") |> range(start: -30d) |> filter(fn: (r) => r["_measurement"] == "users") |> filter(fn: (r) => r["user"] == "' + username  + '") |> count()', org=app.config['INFLUX_ORG'])
        if response:
            return True
        else:
            return False
    except:
        return True

def validate_password(username,given_pass):
    try:
        client = InfluxDBClient(url=app.config['INFLUX_ENDPOINT_URL'], token=app.config['INFLUX_TOKEN'], org=app.config['INFLUX_ORG'])
        response = client.query_api().query('from(bucket: "' + app.config['INFLUX_BUCKET'] +'") |> range(start: -30d) |> filter(fn: (r) => r["_measurement"] == "users") |> filter(fn: (r) => r["user"] == "' + username  + '") |> last()', org=app.config['INFLUX_ORG'])
        user_password=(response[0].records[0].values['_value'])
        user_email=(response[0].records[0].values['email'])
        # Hash pw
        verified = pwd_context.verify(given_pass, user_password)
        if not verified:
            return False
        else:
            write_api = client.write_api(write_options=SYNCHRONOUS)
            hashedpass = pwd_context.hash(given_pass)
            data = ['users,user=' + username + ',email=' + user_email + ' pass="' + hashedpass + '"']
            write_api.write(bucket=app.config['INFLUX_BUCKET'], record=data)
            session["user"] = username
            session["email"] = user_email
            #session["email"] = user_email
            return True
        client.close()
    except:
        print("puppa validate_password")
        return False

def get_user_email(username):
    try:
        client = InfluxDBClient(url=app.config['INFLUX_ENDPOINT_URL'], token=app.config['INFLUX_TOKEN'], org=app.config['INFLUX_ORG'])
        response = client.query_api().query('from(bucket: "' + app.config['INFLUX_BUCKET'] +'") |> range(start: -30d) |> filter(fn: (r) => r["_measurement"] == "users") |> filter(fn: (r) => r["user"] == "' + username  + '") |> last()', org=app.config['INFLUX_ORG'])
        user_email=(response[0].records[0].values['email'])
        client.close()
        # Hash pw
        #hashedpass = pwd_context.hash(given_pass)
        #verified = pwd_context.verify(given_pass, hashedpass)
        verified = pwd_context.verify(given_pass, user_password)
        #if given_pass != user_password:
        if not verified:
            return False
        else:
            return True
    except:
        print("puppa validate_password")
        return False

def shout_is_valid(shouthash,username):
    try:
        client = InfluxDBClient(url=app.config['INFLUX_ENDPOINT_URL'], token=app.config['INFLUX_TOKEN'], org=app.config['INFLUX_ORG'])
        query_api = client.query_api()
        write_api = client.write_api(write_options=SYNCHRONOUS)
        try:
            p = Point("hit").tag("user", username).field("value", shouthash)
            write_api.write(bucket=app.config['INFLUX_BUCKET'], record=p)
        except:
            return False
        response = query_api.query('from(bucket:"'+ app.config['INFLUX_BUCKET']  +'") |> range(start: -240m) |> filter(fn: (r) => r["_measurement"] == "shout") |> filter(fn: (r) => r["_value"] == "' + shouthash  +'") |> count()')
        shout_exists=response[0].records[0]['_value']
        maxhits=response[0].records[0]['maxhits']
        try:
            maxtime=response[0].records[0]['maxtime']
        except:
            maxtime=240
        #print >> environ['wsgi.errors'], maxhits
        responsehit = query_api.query('from(bucket:"' + app.config['INFLUX_BUCKET'] + '") |> range(start: -240m) |> filter(fn: (r) => r["_measurement"] == "hit") |> filter(fn: (r) => r["_value"] == "'+ shouthash  +'") |> count()')
        totalhits=responsehit[0].records[0]['_value']
        client.close()
        if shout_exists > 0 and totalhits <= int(maxhits):
            return True
        else:
            return False 
    except:
        return False

def get_shouttext(shouthash,username):
    try:
        client = InfluxDBClient(url=app.config['INFLUX_ENDPOINT_URL'], token=app.config['INFLUX_TOKEN'], org=app.config['INFLUX_ORG'])
        query_api = client.query_api()
        write_api = client.write_api(write_options=SYNCHRONOUS)
        response = query_api.query('from(bucket:"'+ app.config['INFLUX_BUCKET']  +'") |> range(start: -240m) |> filter(fn: (r) => r["_measurement"] == "shouttext") |> filter(fn: (r) => r["shout"] == "' + shouthash  +'") |> filter(fn: (r) => r["_field"] == "value") |> distinct() |> yield(name: "distinct")')
        data = response[0].records[0]['_value']
        client.close()
        return data
    except:
        return "errors found"

def get_shoutphoto(shouthash):
    try:
        botoclient = boto3.client('s3',endpoint_url=app.config['S3_ENDPOINT_URL'], config=boto3.session.Config(signature_version='s3v4'), aws_access_key_id=app.config['S3_ACCESS_KEY'], aws_secret_access_key=app.config['S3_SECRET_KEY'] )
        ext = '.jpeg'
        object_data = botoclient.get_object(Bucket=app.config['S3_BUCKET'], Key=shouthash + ext)
        data = object_data['Body'].read()
        decoded_img = base64.b64encode(data).decode('ascii')
    except:
        decoded_img = ''
        data = None
    return str(decoded_img)

def random_qr(url='https://' + app.config['VHOST_WEBSITE']):
    qr = qrcode.QRCode(version=1,
                       error_correction=qrcode.constants.ERROR_CORRECT_L,
                       box_size=10,
                       border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image()
    return img

############# END FUNCTIONS ####################

@app.route("/favicon.ico")
def display_favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),'favicon.ico',mimetype='image/vnd.microsoft.icon')

@app.route('/get_qrimg/<shouttype>/<shouthash>')
def get_qrimg(shouttype,shouthash):
    img_buf = io.BytesIO()
    img = random_qr(url='https://' + app.config['VHOST_WEBSITE'] + '/' + shouttype + '/' + shouthash)
    img.save(img_buf)
    img_buf.seek(0)
    return send_file(img_buf, mimetype='image/png')

@app.route('/buildchat_qrurl/<chathash>')
def build_qrimg(chathash):
    img_buf = io.BytesIO()
    img = random_qr(url='https://' + app.config['VHOST_WEBSITE'] + '/chat/' + chathash)
    img.save(img_buf)
    img_buf.seek(0)
    return send_file(img_buf, mimetype='image/png')


#@app.route("/profile")
#@login_required
#def display_one_profile():
#    shouts=None
#    influxclient = InfluxDBClient( url=app.config['INFLUX_ENDPOINT_URL'], token=app.config['INFLUX_TOKEN'], org=app.config['INFLUX_ORG'] )
#    query_api = influxclient.query_api()
#    response = query_api.query('from(bucket:"'+ app.config['INFLUX_BUCKET']  +'") |> range(start: -30d) |> filter(fn: (r) => r["_measurement"] == "shout") |> filter(fn: (r) => r["user"] == "' + session["user"]  + '")')
#    shouts=[]
#    influxclient.close()
#    if response:
#        shouts=response[0].records
#    return render_template("user_profile.html",
#       username=session["user"],
#       email=session.get('email'),
#       shouts=shouts)


#@app.route("/register", methods=['POST'])
#def process_registration_form():
##        flash("Registration not yet active! Try again in few days!")
##        return redirect("/")
#    username = request.form["username"]
#    email = request.form["email"]
#    password = request.form["password"]
#    username_exists = validate_user(username)
#    if username_exists:
#        flash("{} already taken. Try again!".format(username))
#        return redirect("/")
#    new_user = add_user(username, email, password)
#    if new_user:
#        flash("Thanks for registering {}!".format(username))
#        session["user"] = username
#        return redirect("/profile")
#    else:
#        flash("Could not create user")
#        return redirect("/")
#
##@app.route("/login", methods=['POST'])
#def validate_login_info():
#    #form validation here to be added
#    username = request.form["username"]
#    password = request.form["password"]
#    # Form validation error messages
#    if validate_password(username, password):
#        #session["user"] = username
#        flash("Welcome {} !".format(username))
#        #update_user_db(username, password)#validate_password will keep user table updated
#        return redirect('https://' + app.config['VHOST_WEBSITE'] + '/')
#    else:
#        flash("Incorrect password. Try again.")
#        return redirect("/")
#
#@app.route("/logout")
#def logout_user():
#    try:
#        del session["user"]
#        flash("You have logged out.")
#        return redirect('https://' + app.config['VHOST_WEBSITE'] + '/')
#    except:
#        flash("Could not log you out!")
#        return redirect('https://' + app.config['VHOST_WEBSITE'] + '/')
#
###################################

@app.route("/")
def display_home():
    return render_template("home.html")

@app.route("/viewqr")
def display_viewqr():
    referrer = request.referrer
    return render_template("viewqr.html", url=referrer)

@app.route("/info/<string:topic>")
def display_info():
    return render_template("home.html")

@app.route("/message")
def display_sec():
    return render_template("message.html")

@app.route("/msg")
def display_sec_choosetype():
    return render_template("msg.html")

@app.route('/post', methods = ['POST'])
def shout_gen_shouter():
        maxhits = request.form['maxhits']
        maxtime = request.form['maxtime']
        mediatype = request.form['mediatype']
        if mediatype == "audio" or mediatype == "video":
            return render_template("shouter.html", maxtime=maxtime, maxhits=maxhits, mediatype=mediatype)
        else:
            return render_template(mediatype + "shouter.html", maxtime=maxtime, maxhits=maxhits)

@app.route('/post/<posttype>', methods = ['POST'])
def shout_gen_upload(posttype):
            #if request.MOBILE:
    if request.method == 'POST':
        username = "shout"
        if g.logged_in: 
            username = session["user"]
        ext = '.wav'
        if posttype == 'text':
            username = "shout"
            if g.logged_in: 
                username = session["user"]
            data = request.form['data']
            to = request.form['to']
            maxhits = request.form['maxhits']
            maxtime = request.form['maxtime']
            shouthash = secrets.token_urlsafe(36)
            try:
                influxclient = InfluxDBClient( url=app.config['INFLUX_ENDPOINT_URL'], token=app.config['INFLUX_TOKEN'], org=app.config['INFLUX_ORG'] )
                write_api = influxclient.write_api(write_options=SYNCHRONOUS)
                sequence = ["shouttext,user=" + username + ",shout=" + shouthash + " value=\"" + data + "\"",
            		"shout,user=" + username + ",maxhits=" + maxhits + ",maxtime=" + maxtime + ",type=text value=\"" + shouthash + "\""]
                write_api.write(bucket=app.config['INFLUX_BUCKET'], record=sequence)
                influxclient.close()
            except:
                return render_template("404.html", message="Could not insert shout into tsdb! shout " + shouthash ), 404
            return render_template('textshouter.html', data='https://' + app.config['VHOST_WEBSITE'] + '/stream_any/text/' + shouthash)
        elif posttype == 'video':
            ext = '.mp4'
        elif posttype == 'photo':
            ext = '.jpeg'
        elif posttype == 'audio':
            ext = '.wav'
        else:
            ext = '.null'
        to = request.form['to']
        maxhits = request.form['maxhits']
        maxtime = request.form['maxtime']
        shouthash = secrets.token_urlsafe(36)
        #botoclient = boto3.client('s3',endpoint_url=app.config['S3_ENDPOINT_URL'], aws_access_key_id=app.config['S3_ACCESS_KEY'], aws_secret_access_key=app.config['S3_SECRET_KEY'] )
        botoclient = boto3.client('s3',endpoint_url=app.config['S3_ENDPOINT_URL'], aws_access_key_id=app.config['S3_ACCESS_KEY'], aws_secret_access_key=app.config['S3_SECRET_KEY'], config=boto3.session.Config(signature_version='s3v4') )
        if posttype == 'photo':
            f = request.form['data']
        else:
            f = request.files['data']
        try:
            if posttype != 'photo':
                f.seek(0)
                rawdata=io.BytesIO(f.stream.read())
                rawsize=rawdata.getbuffer().nbytes ## refuse .. needed for minio upload 
                #result = botoclient.put_object(Body=io.BytesIO(f.stream.read()), Bucket=app.config['S3_BUCKET'], Key=shouthash + '' + ext)
                result = botoclient.put_object(Body=rawdata, Bucket=app.config['S3_BUCKET'], ContentLength=rawsize, Key=shouthash + '' + ext)
                res = result.get('ResponseMetadata')
                if res.get('HTTPStatusCode') != 200:
                    return render_template("404.html", message="Could not upload! shout " + shouthash ), 404
            else:
                if "data:image/jpeg;base64," in f or "data:image/png;base64," in f:
                    if "data:image/png;base64," in f:
                        ext = '.png'
                    decoded_img_str = f.replace("data:image/jpeg;base64,", "")
                    decoded_img = base64.b64decode(decoded_img_str.replace("data:image/png;base64,", ""))
                    #img = Image.open(BytesIO(decoded_img))
                    result = botoclient.put_object(Body=io.BytesIO(decoded_img), Bucket=app.config['S3_BUCKET'], Key=shouthash + ext)
                    res = result.get('ResponseMetadata')
                    if res.get('HTTPStatusCode') != 200:
                        return render_template("404.html", message="Could not upload! shout " + shouthash ), 404
            try:
                influxclient = InfluxDBClient( url=app.config['INFLUX_ENDPOINT_URL'], token=app.config['INFLUX_TOKEN'], org=app.config['INFLUX_ORG'] )
                write_api = influxclient.write_api(write_options=SYNCHRONOUS)
                p = ["shout,user=" + username + ",maxhits=" + maxhits + ",maxtime=" + maxtime + ",type=" + posttype + " value=\"" + shouthash + "\""]
                write_api.write(bucket=app.config['INFLUX_BUCKET'], record=p)
                influxclient.close()
            except:
                return render_template("404.html", message="Could not insert shout in database! shout " + shouthash ), 404
        #except S3Error as exc:
        except ClientError as e:
            #logging.error(e)
            #return False
            return render_template("404.html", message="Error in object storage operation! shout " + shouthash + "Error:" + str(e) ), 404
        return 'https://' + app.config['VHOST_WEBSITE'] + '/stream_any/' + posttype + '/' + shouthash
    else:
        return render_template('homepage.html')

@app.route("/chat", methods = ['GET'])
def display_esc_chat():
    uid_chars = ('a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z','1','2','3','4','5','6','7','8','9','0','A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z')
    #chathash = secrets.token_urlsafe(16)
    count=len(uid_chars)-1
    chathash=''
    for i in range(0,16):
        chathash+=uid_chars[random.randint(0,count)]
    #insert validity flag record somewhere
    return render_template("chat.html", chathash=chathash)

@app.route('/stream_any/<string:shouttype>/<string:shouthash>' ,methods = ['GET'])
def shoutplayer_new(shouttype,shouthash):
    valid = request.args.get("valid")
    if valid == "1":
        ua=request.headers.get('User-Agent')
        username = "shout"
        if g.logged_in: 
            username = session['user']
        if ( ua.startswith('Mozilla') or ua.startswith('Dalvik') ) and "bingpreview" not in ua.lower():
           if shout_is_valid(shouthash,username):
               if shouttype == 'text':
                   return render_template("streamtext.html", shouthash=shouthash,shouttext=get_shouttext(shouthash,username))
               elif shouttype == 'photo':
                   return render_template("streamphoto.html", shouthash=shouthash,shoutphoto=get_shoutphoto(shouthash))
               else:
                   return render_template("stream" + shouttype + ".html", shouthash=shouthash)
           else:
               return render_template("404.html", message="Burned! shout " + shouthash + " expired or already seen!"), 404
        else:
            #return render_template("404.html", message="" + shouthash + ""), 200
            return "no preview - private content", 200
    else:
        return render_template("preview.html", shouttype=shouttype, shouthash=shouthash)
        

@app.route('/streaming/<string:shouttype>/<string:shouthash>' ,methods = ['GET'])
def streamwav(shouthash,shouttype):
    if request.referrer:
        if request.referrer.startswith("https://" + app.config['VHOST_WEBSITE']):
            if shouttype == 'audio':
                return Response(generate_stream(shouthash, 'audio'), mimetype="audio/x-wav")
            elif shouttype == 'video':
                return Response(generate_stream(shouthash, 'video'), mimetype="video/webm")
            else:
                return render_template("404.html", message="You nasty boy!!! Keep trying!"), 404
        else:
            return render_template("404.html", message="You nasty boy!!! Keep trying!"), 404
    else:
        return render_template("404.html", message="You nasty boy!!! Keep trying!"), 404

###### VOCAL CHAT / EX VOCALLY

@app.route('/chat/post/<string:posttype>', methods = ['POST'])
def chat_gen_upload(posttype):
            #if request.MOBILE:
    if request.method == 'POST':
        username = "shout"
        if g.logged_in: 
            username = session["user"]
        ext = '.wav'
        if posttype == 'video':
            ext = '.mp4'
        elif posttype == 'photo':
            ext = '.jpeg'
        elif posttype == 'audio':
            ext = '.wav'
        else:
            ext = '.null'
        to = request.form['to']
        maxhits = request.form['maxhits']
        maxtime = request.form['maxtime']
        chathash = request.form['chathash']
        shouthash = secrets.token_urlsafe(36)
        #botoclient = boto3.client('s3',endpoint_url=app.config['S3_ENDPOINT_URL'], aws_access_key_id=app.config['S3_ACCESS_KEY'], aws_secret_access_key=app.config['S3_SECRET_KEY'] )
        botoclient = boto3.client('s3',endpoint_url=app.config['S3_ENDPOINT_URL'], aws_access_key_id=app.config['S3_ACCESS_KEY'], aws_secret_access_key=app.config['S3_SECRET_KEY'], config=boto3.session.Config(signature_version='s3v4') )
        if posttype == 'photo':
            f = request.form['data']
        else:
            f = request.files['data']
        try:
            if posttype != 'photo':
                f.seek(0)
                rawdata=io.BytesIO(f.stream.read())
                rawsize=rawdata.getbuffer().nbytes ## refuse .. needed for minio upload 
                #result = botoclient.put_object(Body=io.BytesIO(f.stream.read()), Bucket=app.config['S3_BUCKET'], Key=shouthash + '' + ext)
                result = botoclient.put_object(Body=rawdata, Bucket=app.config['S3_BUCKET'], Key=shouthash + '' + ext)
                res = result.get('ResponseMetadata')
                if res.get('HTTPStatusCode') != 200:
                    return render_template("404.html", message="Could not upload! shout " + shouthash ), 404
            else:
                if "data:image/jpeg;base64," in f or "data:image/png;base64," in f:
                    if "data:image/png;base64," in f:
                        ext = '.png'
                    decoded_img_str = f.replace("data:image/jpeg;base64,", "")
                    decoded_img = base64.b64decode(decoded_img_str.replace("data:image/png;base64,", ""))
                    #img = Image.open(BytesIO(decoded_img))
                    result = botoclient.put_object(Body=io.BytesIO(decoded_img), Bucket=app.config['S3_BUCKET'], Key=shouthash + ext)
                    res = result.get('ResponseMetadata')
                    if res.get('HTTPStatusCode') != 200:
                        return render_template("404.html", message="Could not upload! shout " + shouthash ), 404
            try:
                influxclient = InfluxDBClient( url=app.config['INFLUX_ENDPOINT_URL'], token=app.config['INFLUX_TOKEN'], org=app.config['INFLUX_ORG'] )
                write_api = influxclient.write_api(write_options=SYNCHRONOUS)
                p = ["chat_" + chathash +",user=" + username + ",maxhits=" + maxhits + ",maxtime=" + maxtime + ",type=" + posttype + " value=\"" + shouthash + "\""]
                write_api.write(bucket=app.config['INFLUX_BUCKET'], record=p)
                influxclient.close()
            except:
                return render_template("404.html", message="Could not insert shout in database! shout " + shouthash ), 404
        #except S3Error as exc:
        except ClientError as e:
            #logging.error(e)
            #return False
            return render_template("404.html", message="Error in object storage operation! shout " + shouthash + "Error:" + str(e) ), 404
        return 'https://' + app.config['VHOST_WEBSITE'] + '/stream_any/' + posttype + '/' + shouthash
    else:
        return redirect('/chat/' + chathash)

@app.route('/chat/<string:chathash>', methods = ['GET'])
def display_hashed_chat(chathash):
    shouts=None
    influxclient = InfluxDBClient( url=app.config['INFLUX_ENDPOINT_URL'], token=app.config['INFLUX_TOKEN'], org=app.config['INFLUX_ORG'] )
    query_api = influxclient.query_api()
    response = query_api.query('from(bucket:"'+ app.config['INFLUX_BUCKET']  +'") |> range(start: -5m) |> filter(fn: (r) => r["_measurement"] == "chat_' + chathash +'") |> group(columns: ["_measurement"]) |> sort(columns: ["_time"], desc: false)')
    shouts=[]
    influxclient.close()
    if response:
        shouts=response[0].records
    #return render_template("user_profile.html",
    return render_template("hashed_chat.html", shouts=shouts, chathash=chathash)

@app.route("/talkinloud")
def display_radio():
    return redirect('https://' + app.config['VHOST_WEBSITE'] + '/talkinloud/20090303')

@app.route("/talkinloud/<string:onair_date>", methods = ['GET'])
def cassettina(onair_date):
    if onair_date in ['20060921', '20061109', '20061114', '20061130', '20070111', '20070315', '20070419', '20080604', '20090303']: 
        data="'talk_" + onair_date + "-p1', 'talk_" + onair_date + "-p2'"
    elif onair_date in ['20061010', '20061024', '20061102', '20080402', '20080417']:
        data="'talk_" + onair_date + "-p1', 'talk_" + onair_date + "-p2', 'talk_" + onair_date + "-p3'"
    elif onair_date in ['20080410']:
        data="'talk_" + onair_date + "-p1', 'talk_" + onair_date + "-p2', 'talk_" + onair_date + "-p3', 'talk_" + onair_date + "-p4'"
    else:
        data="'talk_" + onair_date + "'"
    return render_template("cassettina.html", data=data, onair_date=onair_date )

if __name__ == "__main__":
#    app.run()
    app.run(host='0.0.0.0', port=1048)

