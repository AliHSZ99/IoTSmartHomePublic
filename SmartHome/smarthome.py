import plotly.graph_objects as go
import dash
import dash_daq as daq
from dash import dcc
from dash import html
from dash.dependencies import Input, Output
import plotlyg

from collections import deque
import time
import board
import adafruit_dht

import RPi.GPIO as GPIO
import time
import random

import base64
import re

# MQTT
from paho.mqtt import client as mqtt_client

# Send email
import smtplib, ssl
from datetime import datetime

# Receive email
import imaplib
import email
from email.header import decode_header
import webbrowser
import os

# database
from tinydb import TinyDB, Query

db = TinyDB('userDb.json')

GPIO.setmode(GPIO.BCM)
enable=21
pin1=12
pin2=24
dhtpin=4
GPIO.setup(dhtpin, GPIO.IN)
GPIO.setup(enable, GPIO.OUT)
GPIO.setup(pin1, GPIO.OUT)
GPIO.setup(pin2, GPIO.OUT)

broker = '192.168.109.212'
port = 1883
lightTopic = "PhotoresistorInfo"
rfidTopic = "RFIDInfo"
# generate client ID with pub prefix randomly
client_id = f'python-mqtt-{random.randint(0, 1000)}'
username = 'emqx'
password = 'public'

class Light:
    lightIntensity = 0
    
class RFID:
    rfidVal = ""
    
class Temperature:
    temperature = 0

class FanAnswer:
    answer = ""

emailPort = 465  # For SSL
smtp_server = "smtp.gmail.com"
sender_email = "senderemail@gmail.com"  # Enter your address
receiver_email = "receiveremail@gmail.com"  # Enter receiver address
senderPassword = "senderPassword"
receiverPassword = "receiverPassword"

# datetime object containing current date and time
now = datetime.now()
dt_string = now.strftime("%H:%M:%S")

def receiveEmail():
    def clean(text):
        # clean text for creating a folder
        return "".join(c if c.isalnum() else "_" for c in text)

    # create an IMAP4 class with SSL 
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    # authenticate
    imap.login(sender_email, senderPassword)

    status, messages = imap.select("INBOX")
    # number of top emails to fetch
    N = 1
    # total number of emails
    messages = int(messages[0])

    for i in range(messages, messages-N, -1):
        # fetch the email message by ID
        res, msg = imap.fetch(str(i), "(RFC822)")
        for response in msg:
            if isinstance(response, tuple):
                # parse a bytes email into a message object
                msg = email.message_from_bytes(response[1])
                # decode the email subject
#                 subject, encoding = decode_header(msg["Subject"])[0]
#                 if isinstance(subject, bytes):
#                     # if it's a bytes, decode to str
#                     subject = subject.decode(encoding)
                # decode email sender
                From, encoding = decode_header(msg.get("From"))[0]
                if isinstance(From, bytes):
                    From = From.decode(encoding)
#                 print("Subject:", subject)
#                 print("From:", From)
                # if the email message is multipart
                if msg.is_multipart():
                    # iterate over email parts
                    for part in msg.walk():
                        # extract content type of email
                        content_type = part.get_content_type()
                        content_disposition = str(part.get("Content-Disposition"))
                        try:
                            # get the email body
                            body = part.get_payload(decode=True).decode()
                        except:
                            pass
                        if content_type == "text/plain" and "attachment" not in content_disposition:
                            # print text/plain emails and skip attachments
                            print(body)
                            FanAnswer.answer = body[0:3]
#                         elif "attachment" in content_disposition:
#                             # download attachment
#                             filename = part.get_filename()
#                             if filename:
#                                 folder_name = clean(subject)
#                                 if not os.path.isdir(folder_name):
#                                     # make a folder for this email (named after the subject)
#                                     os.mkdir(folder_name)
#                                 filepath = os.path.join(folder_name, filename)
#                                 # download attachment and save it
#                                 open(filepath, "wb").write(part.get_payload(decode=True))
                else:
                    # extract content type of email
                    content_type = msg.get_content_type()
                    # get the email body
                    body = msg.get_payload(decode=True).decode()
                    if content_type == "text/plain":
                        # print only text email parts
                        print(body)
                        FanAnswer.answer = body[0:3]
#                 if content_type == "text/html":
#                     # if it's HTML, create a new HTML file and open it in browser
#                     folder_name = clean(subject)
#                     if not os.path.isdir(folder_name):
#                         # make a folder for this email (named after the subject)
#                         os.mkdir(folder_name)
#                     filename = "index.html"
#                     filepath = os.path.join(folder_name, filename)
#                     # write the file
#                     open(filepath, "w").write(body)
#                     # open in the default browser
#                     webbrowser.open(filepath)
#                 print("="*100)
    # close the connection and logout
    imap.close()
    imap.logout()

# Connect MQTT
def connect_mqtt() -> mqtt_client:
    def on_connect(client, userdata, flags, rc):
        try:
            if rc == 0:
                print("Connected to MQTT Broker!")
            else:
                print("Failed to connect, return code %d\n", rc)
        except Exception as error:
            print("hello error")

    client = mqtt_client.Client(client_id)
    client.username_pw_set(username, password)
    client.on_connect = on_connect
    client.connect(broker, port)
    return client

def subscribe(client: mqtt_client):
    def on_message(client, userdata, msg):
#         Light.lightIntensity = msg.payload.decode()
# #         print("LIGHTT" + Light.lightIntensity)
#         return Light.lightIntensity
#         if (msg.payload.decode("utf-8").isdigit()) || strchr(msg.payload.decode("utf-8"), '.'):
#             Light.lightIntensity = msg.payload.decode("utf-8")
#         else:
#             RFID.rfidVal = msg.payload.decode("utf-8")
        
        if bool(re.search('\s', msg.payload.decode("utf-8"))) == True:
            RFID.rfidVal = msg.payload.decode("utf-8")
        else:
            Light.lightIntensity = msg.payload.decode("utf-8")

    client.subscribe(lightTopic)
    client.subscribe(rfidTopic)
    client.on_message = on_message
    
# def subscribe2(client: mqtt_client):
#     def on_message(client, userdata, msg):
#         RFID.rfidVal = msg.payload.decode()
# #         print("RFIDDDD" + RFID.rfidVal)
#         return RFID.rfidVal
# 
#     client.subscribe(rfidTopic)
#     client.on_message = on_message
#     return on_message

def readTempHumidity():
    # Initial the dht device, with data pin connected to:
    dhtDevice = adafruit_dht.DHT11(board.D4, False)
    Temperature.temperature = dhtDevice.temperature
    humidity = dhtDevice.humidity
    for i in range (0,1):
        
        try:
            Temperature.temperature = dhtDevice.temperature
            humidity = dhtDevice.humidity
            
        except RuntimeError as error:
            # Errors happen fairly often, DHT's are hard to read, just keep going
            continue
        
        except Exception as error:
            dhtDevice.exit()

    return [Temperature.temperature, humidity]
#     return [0, 1]



def runMotor():
    GPIO.output(pin1, 1)
    GPIO.output(pin2, 0)
    pwm=GPIO.PWM(enable, 50)
#     pwm.start(0)
#     pwm.ChangeDutyCycle(50)
    GPIO.output(enable, 1)
#     sleep(5)
#     GPIO.output(enable, 0)
#     GPIO.cleanup()
#     print("helloo")

app = dash.Dash(__name__)

app.layout = html.Div([
    html.Div(
        'Smart Home System',
        style = {'text-align':'center', 'text-shadow':'2px 2px #C2C2C2',
                 'color':'#00236B', 'fontSize':'70px', 'margin-bottom':'25px'}
    ),
    
    # div for all widgets, to apply flex
    html.Div([
        # div to encapsulate temp & humidity
        html.Div([
            html.Div([
                daq.Gauge(
                    id = "tempGauge",
                    label = "Temperature",
                    color = "#006400",
                    min = -20,
                    max = 50,
                    scale = {'start':-20, 'interval':5},
                    value = 0,
                    showCurrentValue = True,
                    units = "C",
                    size = 300)]
            ),
            
            html.Div([
                daq.Gauge(
                    id = "humidityGauge",
                    label = "Humidity",
                    color = "#00008B",
                    min = 0,
                    max = 100,
                    scale = {'start':0, 'interval':5},
                    value = 0,
                    showCurrentValue = True,
                    units = "%",
                    size = 300)], 
            ),
        ], style = {'margin-left':'10px', 'padding-left':'20px', 'padding-right':'20px',
                    'padding-top':'20px',
                    'box-shadow': '0 1px 6px rgba(0, 0, 0, 0.12)',
                    'background-color':'#FCFCFC'}),
        
        # div to put fan section under light section
        html.Div([
            # div to encapsulate light section
            html.Div([
                html.Div([
                    dcc.Textarea(
                        id = 'lightIntensity',
                        value = "Surrounding Light Intensity: 4000",
                        disabled = True,
                        style = {'margin':'20px', 'padding-top':'110px',
                                 'border':'none', 'resize':'none',
                                 'background-color': '#FCFCFC',
                                 'font-size':'25px',
                                 'text-align':'center'}
                    )
                ]),
                
                html.Img(
                    id = 'lightStatus',
                    src = app.get_asset_url('lightOn.png'),
                    width = 250,
                    style = {'margin-bottom':'30px'}
                )
            ], style = {'display':'flex', 'margin-left':'10px', 'padding-left':'20px',
                    'padding-right':'20px', 'padding-top':'20px',
                    'box-shadow': '0 1px 6px rgba(0, 0, 0, 0.12)',
                    'background-color':'#FCFCFC'}),
            
            html.Div([
                dcc.Textarea(
                    id = 'lightEmailSent',
                    value = "Email has been sent!",
                    disabled = True,
                    style = {'margin': '30px', 'padding-top':'20px',
                             'border': 'none', 'resize': 'none',
                             'font-size':'20px', 'font-style':'italic', 
                             'color':'#005509', 'text-align':'center',
#                              'box-shadow': '0 1px 6px rgba(0, 0, 0, 0.12)',
                             'background-color': 'white'}
                )],
            style = {'text-align':'center'}),
            
            # div to encapsulate fan section
            html.Div([
                html.Img(
                    id = 'fanStatus',
                    src = app.get_asset_url('fanOn.png'),
                    width = 250,
                    style = {'margin-bottom':'30px', 'margin-left':'10px'}
                ),
                    
                html.Div(
                    'Fan Status',
                    style = {'text-align':'center', 'color':'#1AA0Af',
                              'fontSize':'30px', 'padding':'110px', 'margin-left':'30px'}
                ),
            ], style = {'display':'flex', 'margin-left':'10px', 'padding-left':'20px',
                    'padding-right':'20px', 'padding-top':'20px',
                    'box-shadow': '0 1px 6px rgba(0, 0, 0, 0.12)',
                    'background-color':'#FCFCFC'}),
        ]),
        
        # div to encapsulate user information
        html.Div([
            html.Div([
                dcc.Textarea(
                    id = 'username',
                    value = "Welcome, user!",
                    disabled = True,
                    style = {'margin':'20px', 'padding-top':'55px',
                             'border':'none', 'resize':'none',
                             'background-color': '#FCFCFC',
                             'font-size':'38px',
                             'color':'#1AA0Af',
                             'text-align':'center'}
                )
            ]),
            
            html.Img(
                id = 'profilePicture',
                src = app.get_asset_url('aliPP.png'),
                width = 250,
                style = {'max-height':'250px', 'max-width':'300px', 'height':'auto',
                         'width':'auto', 'margin-bottom':'30px', 'margin-left':'150px'}
            ),
            
            html.Div([
                dcc.Textarea(
                    id = 'tempThresh',
                    value = "Temperature: 0",
                    disabled = True,
                    style = {'margin':'20px', 'padding-top':'10px', 'padding-left':'35px',
                             'border':'none', 'resize':'none',
                             'background-color': '#FCFCFC',
                             'font-size':'30px',
                             'color':'#006400',
                             'text-align':'center'}
                )
            ]),
            
            html.Div([
                dcc.Textarea(
                    id = 'lightThresh',
                    value = "Light Intensity: 0",
                    disabled = True,
                    style = {'margin':'20px', 'padding-top':'10px', 'margin-bottom':'0px',
                             'padding-left':'35px', 'border':'none', 'resize':'none',
                             'background-color': '#FCFCFC',
                             'font-size':'30px',
                             'color':'#00008B',
                             'text-align':'center'}
                )
            ]),
        ], style = {'margin-left':'10px', 'padding-left':'20px', 'padding-right':'20px',
                    'padding-top':'20px',
                    'box-shadow': '0 1px 6px rgba(0, 0, 0, 0.12)',
                    'background-color':'#FCFCFC'}),
    ], style = {'display':'flex'}),
    
    dcc.Interval(
        id = "interval",
        interval = 10000,
        n_intervals = 0
    )
])


@app.callback(
    Output('tempGauge', 'value'),
    Output('humidityGauge', 'value'),
    Output('lightIntensity', 'value'),
    Output('lightStatus', 'src'),
    Output('lightEmailSent', 'value'),
    Output('fanStatus', 'src'),
    Output('username', 'value'),
    Output('profilePicture', 'src'),
    Output('tempThresh', 'value'),
    Output('lightThresh', 'value'),
    Input('interval', 'n_intervals')
    )


def update_output(values):
    # FIRST GET ALL DATA
    values = readTempHumidity()
#     lightIntensity = int(float(Light.lightIntensity))
#     lightIntensityStr = "Surrounding Light Intensity: " + str(lightIntensity)
    lightIntensityStr = "Surrounding Light Intensity " + Light.lightIntensity
    lightIntensity = float(Light.lightIntensity)
#     print(Light.lightIntensity)
    print(lightIntensityStr)
    print("RFID:" + RFID.rfidVal)
    
    # THEN DETERMINE USER
    userName = ""
    temperatureThreshold = 0
    lightThreshold = 0
    userPicture = ""
    
    # For Ali (card)
    if (RFID.rfidVal == " 163 108 0 23"):
        rfidQuery = Query()
        result = db.search(rfidQuery.rfidTag == ' 163 108 0 23')
        
        userName = result[0]['name']
        temperatureThreshold = result[0]['temperature']
        lightThreshold = result[0]['light']
        userPicture = result[0]['image']
#         print(userName)
        userMessage = """\
            Subject: Smart Home User Alert! \n

            %s has just logged in at %s""" % (userName, dt_string)    
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_server, emailPort, context=context) as server:
            server.login(sender_email, senderPassword)        
            server.sendmail(sender_email, receiver_email, userMessage)
            server.quit()
#         print(result[0])
#         print(userName)
#         print(temperatureThreshold)
#         print(lightThreshold)
#         print(userPicture)
        
    
    # For Lisa (tag)
    elif (RFID.rfidVal == " 19 25 49 17"):
        rfidQuery = Query()
        result = db.search(rfidQuery.rfidTag == ' 19 25 49 17')
        
        userName = result[0]['name']
        temperatureThreshold = result[0]['temperature']
        lightThreshold = result[0]['light']
        userPicture = result[0]['image']
        
        userMessage = """\
            Subject: Smart Home User Alert! \n

            %s has just logged in at %s""" % (userName, dt_string)    
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_server, emailPort, context=context) as server:
            server.login(sender_email, senderPassword)        
            server.sendmail(sender_email, receiver_email, userMessage)
            server.quit()
        
#         print(result[0])
#         print(userName)
#         print(temperatureThreshold)
#         print(lightThreshold)
#         print(userPicture)
        
        print("FANNNNNNNNNNNNNNNNNNNNNNNNNNN " + FanAnswer.answer)
    # THEN PERFORM ACTIONS
    # If it's too dark, turn on LED
    if (lightIntensity < lightThreshold):
        try:
            print('helo')
            # If temp too high, turn motor on
            if (values[0] > temperatureThreshold):
                motorMessage = """\
                    Subject: Smart Home Temperature Alert! \n

                    The current temperature is %s degrees celcius, would you like to turn on the fan?""" % (Temperature.temperature)    
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(smtp_server, emailPort, context=context) as server:
                    server.login(sender_email, senderPassword)        
                    server.sendmail(sender_email, receiver_email, motorMessage)
                    server.quit()
                
                receiveEmail()
                if (FanAnswer.answer == "Yes"):
#                 if ("Yes" == "Yes"):
                    print("motor should be running")
                    runMotor()
                    return values[0], values[1], lightIntensityStr, app.get_asset_url('lightOn.png'), 'Email has been sent!', app.get_asset_url('fanOn.png'), 'Welcome, ' + userName + '!', app.get_asset_url(userPicture), 'Temperature: ' + str(temperatureThreshold), 'Light Intensity: ' + str(lightThreshold)
                else:
                    return values[0], values[1], lightIntensityStr, app.get_asset_url('lightOn.png'), 'Email has been sent!', app.get_asset_url('fanOff.png'), 'Welcome, ' + userName + '!', app.get_asset_url(userPicture), 'Temperature: ' + str(temperatureThreshold), 'Light Intensity: ' + str(lightThreshold)
                    
            else:
                return values[0], values[1], lightIntensityStr, app.get_asset_url('lightOn.png'), 'Email has been sent!', app.get_asset_url('fanOff.png'), 'Welcome, ' + userName + '!', app.get_asset_url(userPicture), 'Temperature: ' + str(temperatureThreshold), 'Light Intensity: ' + str(lightThreshold)
            
            
        finally:
            message = """\
                Subject: Smart Home Light Alert! \n

                The light just turned on! (%s).""" % (dt_string)
            
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_server, emailPort, context=context) as server:
                server.login(sender_email, senderPassword)        
                server.sendmail(sender_email, receiver_email, message)
                server.quit()
            print("grape")
    
    # If brightness is fine, turn LED off
    elif (lightIntensity >= lightThreshold):
        # If temp too high, turn motor on
        if (values[0] > temperatureThreshold):
            motorMessage = """\
                Subject: Smart Home Temperature Alert! \n

                The current temperature is %s degrees celcius, would you like to turn on the fan?""" % (Temperature.temperature)    
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_server, emailPort, context=context) as server:
                server.login(sender_email, senderPassword)        
                server.sendmail(sender_email, receiver_email, motorMessage)
                server.quit()
            
            receiveEmail()
            if (FanAnswer.answer == "Yes"):
#             if ("Yes" == "Yes"):
                print("motor should be running")
                runMotor()
                return values[0], values[1], lightIntensityStr, app.get_asset_url('lightOff.png'), '', app.get_asset_url('fanOn.png'), 'Welcome, ' + userName + '!', app.get_asset_url(userPicture), 'Temperature: ' + str(temperatureThreshold), 'Light Intensity: ' + str(lightThreshold)
            else:
                return values[0], values[1], lightIntensityStr, app.get_asset_url('lightOff.png'), '', app.get_asset_url('fanOff.png'), 'Welcome, ' + userName + '!', app.get_asset_url(userPicture), 'Temperature: ' + str(temperatureThreshold), 'Light Intensity: ' + str(lightThreshold)
                    
        else:
            return values[0], values[1], lightIntensityStr, app.get_asset_url('lightOff.png'), '', app.get_asset_url('fanOff.png'), 'Welcome, ' + userName + '!', app.get_asset_url(userPicture), 'Temperature: ' + str(temperatureThreshold), 'Light Intensity: ' + str(lightThreshold)

# MQTT
client = connect_mqtt()
subscribe(client)
# subscribe2(client)
client.loop_start()

if __name__ == "__main__":
    app.run_server(debug=True)
