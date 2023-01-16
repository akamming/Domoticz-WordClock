# WordClock Pluggin
#
# Author: akamming
#
"""
<plugin key="ESPWordClock" name="ESP8266 WordClock" author="akamming" version="0.0.1" wikilink="http://www.domoticz.com/wiki/plugins/plugin.html" externallink="https://github.com/akamming/WordclockV3">
    <description>
        <h2>WordClock</h2><br/>
        Commmand your wordclock using domoticz
        <h3>Features</h3>
        <ul style="list-style-type:square">
            <li>Feature one...</li>
            <li>Feature two...</li>
        </ul>
        <h3>Configuration</h3>
        Just enter the ipadress and let the plugin do the rest...
    </description>
    <params>
     <param field="Address" label="Hostname or IP Adress" width="200px" required="true" default="localhost"/>
     <param field="Port" label="Port" width="40px" required="true" default="8080"/>
     <param field="Mode1" label="poll time in seconds" required="true" default="3600"/>
    </params>
</plugin>
"""
import Domoticz
import requests
import json
import urllib.parse as parse
import urllib.request as request
import time

Debugging=True
Refreshtime=3600  #Get config from clock every 15 mins
LastRefresh=0

#CLOCKONOFF=1
FOREGROUND=2
BRIGHTNESS=3
BACKGROUND=4
SECONDS=5


def Debug(text):
    global Debug
    if (Debugging):
        Domoticz.Log("DEBUG: "+text)


def UpdateOnOffSensor(SensorName,UnitID,Value):
        #Creating devices in case they aren't there...
        if not (UnitID in Devices):
            Debug("Creating device "+SensorName)
            Domoticz.Device(Name=SensorName, Unit=UnitID, TypeName="Switch", Used=1).Create()
        newValue=0
        if (Value.lower()=="on" or Value.lower()=="yes"):
            newValue=1
        if newValue!=Devices[UnitID].nValue:
            Devices[UnitID].Update(nValue=newValue, sValue=str(Value))
            Domoticz.Log("Switch ("+Devices[UnitID].Name+")")

def UpdateRGBDevice(SensorName,UnitID,nValue,sValue,Color=""):
        #Creating devices in case they aren't there...
        if not (UnitID in Devices):
            Debug("Creating device "+SensorName)
            Domoticz.Device(Name=SensorName, Unit=UnitID, Type=241,Subtype=2,Switchtype=7,Used=1).Create()
        if (Color):
            Devices[UnitID].Update(nValue=nValue,sValue=str(sValue),Color=str(Color))
        else:
            Devices[UnitID].Update(nValue=nValue,sValue=str(sValue))

def UpdateDimmer(SensorName,UnitID,nValue,sValue):
        #Creating devices in case they aren't there...
        if not (UnitID in Devices):
            Debug("Creating device "+SensorName)
            Domoticz.Device(Name=SensorName, Unit=UnitID, Type=244,Subtype=62,Switchtype=7,Used=1).Create()
        Devices[UnitID].Update(nValue=nValue,sValue=str(sValue))


def HTTPRequest(command):
    resultJson = None
    url = "http://{}:{}/{}".format(Parameters["Address"], Parameters["Port"], command)
    try:
        response = requests.get(url,timeout=3)
        Debug("url = "+url)
        if (response.status_code==200):
            return response
        else:
            Domoticz.Error("Domoticz API: http error = {}".format(response.status_code))
    except Exception as e:
        Domoticz.Error("Error calling '{}'".format(url))
        Domoticz.Error("exception is '{}'".format(e))

def ExtractColorAndLevel(Palette):
    r=int(Palette["r"])
    g=int(Palette["g"])
    b=int(Palette["b"])

    # {"b":89,"cw":0,"g":225,"m":3,"r":255,"t":0,"ww":0}
    Level=max(r,g,b)
    Color = json.dumps({
          'm': 3, #mode 3: RGB
          'r':  255 if Level==0 else int(r*255/Level),
          'g':  255 if Level==0 else int(g*255/Level),
          'b':  255 if Level==0 else int(b*255/Level),
    })
    return Color,int(Level*100/255)
              
def GetConfig():
    Debug("GetConfig")
    response = HTTPRequest("getconfig")
    if response:
        try:
            resultJson = response.json()
            
            #Update ibrightness/nightmode
            if resultJson["nightmode"]==True:
                UpdateDimmer("Brightness",BRIGHTNESS,0,0)
                Debug("Updating with 0,0")
            else:
                UpdateDimmer("Brightness",BRIGHTNESS,1,str(int(resultJson["Brightness"])/255*100))
                Debug("Updating with "+str(int(resultJson["Brightness"])/255*100)+" and 1")

            #Update Foreground
            Color,Level=ExtractColorAndLevel(resultJson["foregroundcolor"])
            if Level==0:
                Debug("Updating foreground with 0,0")
                UpdateRGBDevice("Foreground",FOREGROUND,0,0)
            else:
                Debug("Updating foreground with "+str(Level)+" and "+str(Color))
                UpdateRGBDevice("Foreground",FOREGROUND,1,str(Level),Color)

            #Update Background 
            Color,Level=ExtractColorAndLevel(resultJson["backgroundcolor"])
            if Level==0:
                Debug("Updating background with 0,0")
                UpdateRGBDevice("Background",BACKGROUND,0,0)
            else:
                Debug("Updating foreground with "+str(Level)+" and "+str(Color))
                UpdateRGBDevice("Background",BACKGROUND,1,str(Level),Color)
            
            #Update Seconds
            Color,Level=ExtractColorAndLevel(resultJson["secondscolor"])
            if Level==0:
                Debug("Updating seconds with 0,0")
                UpdateRGBDevice("Seconds",SECONDS,0,0)
            else:
                Debug("Updating seconds with "+str(Level)+" and "+str(Color))
                UpdateRGBDevice("Seconds",SECONDS,1,Level,Color)
        except:
            Debug("An exception occurred while reading the output")
    else:
        Debug("No response")

def Hex(Color,Level):
   if int(Color*Level/100)<16: 
        return "0{:1x}".format(int(Color*Level/100))
   else:
        return "{:2x}".format(int(Color*Level/100))


def HexColor(Color,Level):
        ColorJson=json.loads(Color)
        return Hex(ColorJson["r"],Level) + Hex(ColorJson["g"],Level) + Hex(ColorJson["b"],Level)

class BasePlugin:
    enabled = False
    def __init__(self):
        #self.var = 123
        return

    def onStart(self):
        global LastRefresh
        global Refreshtime

        Domoticz.Log("onStart called")
        GetConfig()
        LastRefresh=time.time()
        DumpConfigToLog()
        if int(Parameters["Mode1"])>0:
            Refreshtime=int(Parameters["Mode1"])
            Debug("Refreshtime set to "+str(Refreshtime))


    def onStop(self):
        Domoticz.Log("onStop called")

    def onConnect(self, Connection, Status, Description):
        Domoticz.Log("onConnect called")

    def onMessage(self, Connection, Data):
        Domoticz.Log("onMessage called")

    def onCommand(self, Unit, Command, Level, Color):
        Domoticz.Log("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level) + ", Color: "+str(Color))
        
        if Unit in (FOREGROUND,BACKGROUND,SECONDS):
            #Create correct device string
            DeviceString="fg="
            if Unit==BACKGROUND:
                DeviceString="bg="
            if Unit==SECONDS:
                DeviceString="s="

            #Handle Set Level
            if Command=="Set Level":
                UpdateRGBDevice("Foreground",Unit,1,Level)
                response = HTTPRequest("setcolor?"+DeviceString+HexColor(Devices[Unit].Color,Level))

            #Handle Set Color
            if Command=="Set Color":
                UpdateRGBDevice("Foreground",Unit,1,Level,Color)
                response = HTTPRequest("setcolor?"+DeviceString+HexColor(Color,Level))

            if Command=="On":
                UpdateRGBDevice("Foreground",Unit,1,Level,Color)
                response = HTTPRequest("setcolor?"+DeviceString+HexColor(Devices[Unit].Color,Level))

            #Handle Off
            if Command=="Off":
                UpdateRGBDevice("Foreground",Unit,0,0)
                response = HTTPRequest("setcolor?"+DeviceString+"000000")

        if Unit==BRIGHTNESS:
            if Command=='Off':
                UpdateDimmer("Brightness",Unit,0,0)
                HTTPRequest("setnightmode?value=1")
            else:
                UpdateDimmer("Brightness",Unit,1,str(Level))
                HTTPRequest("setbrightness?value="+str(int(255*Level/100)))
                HTTPRequest("setnightmode?value=0")


    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Log("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(Priority) + "," + Sound + "," + ImageFile)

    def onDisconnect(self, Connection):
        Domoticz.Log("onDisconnect called")

    def onHeartbeat(self):
        global LastRefresh
        Domoticz.Log("onHeartbeat called")
        if Refreshtime>0 and time.time()-LastRefresh>Refreshtime:
            GetConfig()
            LastRefresh=time.time()
        else:
            Debug("ignoring heartbeat")


global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

    # Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Debug("Device Name:     '" + Devices[x].Name + "'")
        Debug("Device nValue:    " + str(Devices[x].nValue))
        Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Debug("Device LastLevel: " + str(Devices[x].LastLevel))
        Debug("Device Color      : " + str(Devices[x].Color))
    return
