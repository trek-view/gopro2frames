import subprocess, json, argparse, platform, copy, os, re, shutil, shlex, time, logging
from datetime import datetime, timedelta
from pathlib import Path
from lxml import etree
from os import walk

class TrekviewCommand():

    def _subprocess(self, command, sh=0):
        logging.info('Executing subprocess')
        ret = False
        try:
            cmd = command
            if sh == 0:
                cmd = shlex.split(" ".join(cmd))
            output = subprocess.run(cmd, capture_output=True)
            if output.returncode == 0:
                ret = output
            else:
                raise Exception(output)
        except Exception as e:
            logging.error(e.stderr.decode('utf-8',"ignore"))
            ret = None
        except:
            exit("Error:Please try again or check if `ExifTool`is installed or not.")
        return ret

    def _exiftool(self, command, sh=0):
        logging.info("Starting Exiftool")
        if platform.system() == "Windows":
            exiftool = "exiftool.exe"
        else:
            exiftool = "exiftool"
        command.insert(0, exiftool)
        ret = self._subprocess(command, sh)
        if ret == None:
            exit("Error occured while executing exiftool.")
        return ret

    def _ffmpeg(self, command, sh=0):
        logging.info("Starting Ffmpeg")
        if platform.system() == "Windows":
            ffmpeg = "ffmpeg.exe"
        else:
            ffmpeg = "ffmpeg"
        command.insert(0, ffmpeg)
        ret = self._subprocess(command, sh)
        if ret == None:
            exit("Error occured while executing exiftool, please see logs for more info.")
        return ret

class TrekviewPreProcess(TrekviewCommand):
    _TimeWrap = False
    """
        init function
        It checks if the video file is valid or not.
        If the video file is valid then it will execute exiftool to get the metadata
    """
    def __init__(self, filename):
        logging.info('Strarting Pre Process')
        filecheck = self.checkFileExists(filename)
        if filecheck == True:
            self.__filename = filename
            self.preProcessExifToolExecute()
        else:
            exit("Please provide a valid video file.")
    
    """
        checkFileExists function
        It checks if the video file is exists/valid or not.
        return (True|False)
    """
    def checkFileExists(self, filename):
        logging.info("Checking If file exists {}".format(filename))
        try:
            video_file = Path(filename)
            if video_file.is_file():
                return True
            else:
                return False
        except:
            return False

    """
        preProcessExifToolExecute function
        It will run exiftool to get all the data that is required for pre-process-1
    """            
    def preProcessExifToolExecute(self):
        logging.info("Getting Pre Process Info")
        cmd = ["-ee", "-j", "-DeviceName", "-ProjectionType", "-MetaFormat", "-StitchingSoftware", "-VideoFrameRate", self.__filename]
        output = self._exiftool(cmd)
        self.__exifPreProcessData = json.loads(output.stdout.decode('utf-8',"ignore"))
        if len(self.__exifPreProcessData) > 0:
            self.__exifPreProcessData = self.__exifPreProcessData[0]
        else:
            exit("Data not available")

    """
        getPreProcessData function
        It will return the data that is required for pre-process-1
        return (Object)
    """  
    def getPreProcessData(self):
        logging.info("Getting Pre Process Data")
        return copy.deepcopy(self.__exifPreProcessData)

    """
        checkProjectionType function
        It will check if the ProjectionType is `equirectangular`
        return (True|False)
    """  
    def checkProjectionType(self):
        logging.info("Checking Pre Process Projection Type")
        if 'ProjectionType' in self.__exifPreProcessData:
            if self.__exifPreProcessData['ProjectionType'] == 'equirectangular':
                return True
            return False
        else:
            return False

    """
        checkDeviceName function
        It will check if the DeviceName is `Fusion` or `GoPro Max`
        return (True|False)
    """  
    def checkDeviceName(self):
        logging.info("Checking Pre Process Device Name")
        devices = ["Fusion", "GoPro Max"]
        if 'DeviceName' in self.__exifPreProcessData:
            if self.__exifPreProcessData['DeviceName'] in devices:
                self.__device = self.__exifPreProcessData['DeviceName']
                return True
            return False
        else:
            return False

    """
        checkMetaFormat function
        It will check if the MetaFormat is `gpmd`
        return (True|False)
    """  
    def checkMetaFormat(self):
        logging.info("Checking Pre Process Meta Format")
        if 'MetaFormat' in self.__exifPreProcessData:
            if self.__exifPreProcessData['MetaFormat'] == "gpmd":
                return True
            return False
        else:
            return False

    """
        checkStitchingSoftware function
        It will check if the StitchingSoftware is `Fusion Studio / GStreamer` or `Spherical Metadata Tool`
        return (True|False)
    """ 
    def checkStitchingSoftware(self):
        logging.info("Checking Pre Process Stitching Software")
        softwares = ["Fusion Studio / GStreamer", "Spherical Metadata Tool"]
        if 'StitchingSoftware' in self.__exifPreProcessData:
            if self.__exifPreProcessData['StitchingSoftware'] in softwares:
                return True
            return False
        else:
            return False

    """
        checkVideoFrameRate function
        It will check if the VideoFrameRate is greater than 5
        return (True|False)
    """ 
    def checkVideoFrameRate(self):
        logging.info("Checking Pre Process Video FrameRate")
        if 'VideoFrameRate' in self.__exifPreProcessData:
            if self.__exifPreProcessData['VideoFrameRate'] > 5:
                return True
            return False
        else:
            return False

    """
        validatePreProcessData function
        It will validate the metadata for `pre-process-1`
        returns a variable which contains all the error information. (Object)
    """ 
    def validatePreProcessData(self):
        _TimeWrap = False
        logging.info("Validate Pre Process Video")
        errors = {
            "hasErrors":None,
            "criticalErrors":None,
            "nonCriticalErrors":None,
            "critical":{
                "projection": {
                    "errorStatus": True,
                    "error": "This does not appear to be a GoPro 360 video. Only mp4 videos with a 360 equirectangular projection are accepted. Please make sure you are uploading 360 mp4 videos from your camera."
                },
                "deviceName": {
                    "errorStatus": True,
                    "error": "This file does not look like it was captured using a GoPro camera. Only content taken using a GoPro 360 Camera are currently supported."
                },
                "metaFormat": {
                    "errorStatus": True,
                    "error": "Your video has no telemetry. You need to enable GPS on your GoPro to ensure GPS location is captured."
                },
                "stitchingSoftware": {
                    "errorStatus": True,
                    "error": "Only mp4's stitched using GoPro software are supported. Please use GoPro software to stitch your GoPro 360 videos."
                },
            },
            "non_critical":{
                "videoFrameRate": {
                    "errorStatus": True,
                    "error": "It appears the frame rate of this video is very low. You can continue, but the images in the Sequence might not render as expected."
                },
                "metaFormatMax": {
                    "errorStatus": True,
                    "error": "It appears this video was captured in timewarp mode. You can continue, but the images in the Sequence might not render as expected."
                },
            }
        }
        critical_errors = []
        non_critical_errors = []
        projection = self.checkProjectionType()

        #Validate Critical Errors
        if projection is True:
            errors['critical']['projection']['errorStatus'] = False
        else:
            errors['critical']['projection']['errorStatus'] = True
            errors['criticalErrors'] = True

        devicename = self.checkDeviceName()
        if devicename is True:
            errors['critical']['deviceName']['errorStatus'] = False
        else:
            errors['critical']['deviceName']['errorStatus'] = True
            errors['criticalErrors'] = True

        metaformat = self.checkMetaFormat()
        if metaformat is True:
            errors['critical']['metaFormat']['errorStatus'] = False
        else:
            errors['critical']['metaFormat']['errorStatus'] = True
            errors['criticalErrors'] = True
            
        stitchingSoftware = self.checkMetaFormat()
        if stitchingSoftware is True:
            errors['critical']['stitchingSoftware']['errorStatus'] = False
        else:
            errors['critical']['stitchingSoftware']['errorStatus'] = True
            errors['criticalErrors'] = True
            

        #Validate Non-Critical Errors
        videoFrameRate = self.checkMetaFormat()
        if videoFrameRate is True:
            errors['non_critical']['videoFrameRate']['errorStatus'] = False
        else:
            errors['non_critical']['videoFrameRate']['errorStatus'] = True
            errors['nonCriticalErrors'] = True
            
        if metaformat is True and (self.__device == "GoPro Max"):
            errors['non_critical']['metaFormatMax']['errorStatus'] = True
            _TimeWrap = True
        else:
            errors['non_critical']['metaFormatMax']['errorStatus'] = False
            errors['nonCriticalErrors'] = True

        if (errors['criticalErrors'] == True) or (errors['nonCriticalErrors'] == True):
            errors['hasErrors'] = True
            
        return errors

class TrekviewProcessMp4(TrekviewCommand):
    def __init__(self, filename, data):
        self.VideoData = data
        self._Timewrap = data["Timewrap"]
        logging.info("Starting Mp4 Process")
        if platform.system() == "Windows":
            self.__exiftool = "exiftool.exe"
        else:
            self.__exiftool = "exiftool"
        if platform.system() == "Windows":
            self.__ffmpeg = "ffmpeg.exe"
        else:
            self.__ffmpeg = "ffmpeg"
        filecheck = self.checkFileExists(filename)
        if filecheck == True:
            self.__filename = filename
            self.extractMetaData()
            self.breakIntoFrames()
        else:
            exit("Please provide a valid video file.")

    """
        checkFileExists function
        It checks if the video file is exists/valid or not.
        return (True|False)
    """
    def checkFileExists(self, filename):
        logging.info("Checking if file exists")
        try:
            video_file = Path(filename)
            if video_file.is_file():
                return True
            else:
                return False
        except:
            return False

    def extractMetaData(self):
        logging.info("Extracting Vide Meta Data")
        xmlFile = os.getcwd() + os.sep + 'VIDEO_META.xml'
        cmd = ["-ee", "-G3", "-api", "LargeFileSupport=1", "-X", self.__filename]
        output = self._exiftool(cmd)
        with open(xmlFile, "w") as f:
            self.__xmlOutput = output.stdout
            f.write(self.__xmlOutput.decode('utf-8'))  
        return True
    
    def breakIntoFrames(self):
        logging.info('Start breaking frames')
        self.__folderName = os.getcwd() + os.sep + "Img"
        root = etree.fromstring(self.__xmlOutput)
        if self._Timewrap == True:
            Track = "Track2"
        else:
            Track = "Track3"
        DTO = root.xpath('.//'+Track+':GPSDateTime', namespaces = {Track:'http://ns.exiftool.org/QuickTime/'+Track+'/1.0/'})
        jDTO = self.parseJsonForGPS()
        _jDTO = []
        for k, v in jDTO.items():
            _kv = {}
            for value in v:
                for key in value:
                    _kv[key] = value[key]
            _jDTO.append(_kv)

        try:
            if os.path.exists(self.__folderName):
                shutil.rmtree(self.__folderName)
            os.makedirs(self.__folderName, exist_ok=True) 
            cmd = [self.__ffmpeg, "-i", self.__filename, "-r", "5", self.__folderName+os.sep+"img%d.jpg"]
            output = subprocess.run(cmd, capture_output=True)
            if output.returncode != 0: 
                raise Exception(output)
            else:
                images = next(walk(self.__folderName), (None, None, []))[2]
                for img in images:
                    iDM = self.injectDateTimeMetadata(self.__folderName+os.sep+img, _jDTO)
                    if iDM == None:
                        logging.error('Unable to get GPS Date Time for file: {}'.format(self.__folderName+os.sep+img))
                if iDM != None:
                    try:
                        cmd = shlex.split(self.__exiftool+" '-DateTimeOriginal+<0:0:${filesequence;$_*=0.2}' "+self.__folderName)
                        output = subprocess.run(cmd, capture_output=True)
                        if output.returncode == 0:
                            for img in images:
                                try:
                                    cmd = [self.__exiftool, "-ee", "-j", "-DateTimeOriginal", self.__folderName+os.sep+img]
                                    output = subprocess.run(cmd, capture_output=True)
                                    if output.returncode == 0:
                                        img_dateTimeOriginal= json.loads(output.stdout.decode('utf-8',"ignore"))
                                        if len(img_dateTimeOriginal) > 0:
                                            img_dateTimeOriginal = img_dateTimeOriginal[0]["DateTimeOriginal"]
                                            for _val in _jDTO:
                                                _match = False
                                                atd = time.strptime(_val["GPSDateTime"], "%Y:%m:%d %H:%M:%S.%f")
                                                btd = time.strptime(img_dateTimeOriginal, "%Y:%m:%d %H:%M:%S")
                                                if (btd <= atd) == True:
                                                    _match = True
                                                    self.getGPSValues(_val, self.__folderName+os.sep+img)
                                                    break
                                            if _match == False:
                                                self.getGPSValues(_jDTO[-1], self.__folderName+os.sep+img)
                                    else:
                                        raise Exception(output)
                                except Exception as e:
                                    exit("Error: {}".format( e.stderr.decode('utf-8',"ignore")))
                                except:
                                    exit("Error:Please try again or check if `ExifTool`is installed or not.")
                        self.injectMetadata(root)
                    except Exception as e:
                        exit( e.stderr.decode('utf-8',"ignore"))
                    except:
                        exit("Error occurred. Please try again or check if `ExifTool`is installed or not.")
        except Exception as e:
            exit("Error: {}".format( e.stderr.decode('utf-8',"ignore")))
        except:
            exit("Error occurred. Please try again or check if `Ffmpeg`is installed or not.")
        if iDM == None:
            exit("Unable to get GPS DateTime")
        return True
    
    def parseJsonForGPS(self):
        output = self._exiftool(["-ee", "-G3", "-api", "LargeFileSupport=1", "-j", self.__filename])
        with open("fileexiftool.json", "w") as f:
            f.write(json.dumps(output.stdout.decode('utf-8')))
        jsonData = json.loads(output.stdout.decode('utf-8',"ignore"))  
        if len(jsonData) > 0:
            jsonData = jsonData[0]
        else:
            return None
        gpsDataString = []
        gpsData = {}
        for k,v in jsonData.items():
            data = k.split(":")
            if len(data) > 1:
                if data[1] == "GPSDateTime":
                    gpsDataString.append(k)
        for gpsString in gpsDataString:
            g1Data = gpsString.split(":")
            for k,v in jsonData.items():
                g2Data = k.split(":")
                if len(g2Data) > 1:
                    if g1Data[0] == g2Data[0]:
                        if g1Data[0] in gpsData:
                            if g2Data[1] in ["GPSAltitude", "GPSLongitude", "GPSLatitude", "GPSDateTime"]:
                                gpsData[g1Data[0]].append({g2Data[1]:v})
                        else:
                            gpsData[g1Data[0]] = []
        return gpsData

    def getSphericalMetaData(self, root):
        logging.info("Getting Spherical Meta Data")

        output = self._exiftool(["-ee", "-G3", "-api", "LargeFileSupport=1", "-j", "-StitchingSoftware", "-ProjectionType","-SourceImageHeight","-SourceImageWidth", self.__filename])
        jsonData = json.loads(output.stdout.decode('utf-8',"ignore"))

        if len(jsonData) > 0:
            jsonData = jsonData[0]
        else:
            return None
        data = {}

        GSpherical = [
            {
                "video":"StitchingSoftware",
                "image":"XMP-GPano:StitchingSoftware",
                "value":""
            },
            {
                "video":"",
                "image":"XMP-GPano:SourcePhotosCount",
                "value":2
            },
            {
                "video":"",
                "image":"XMP-GPano:UsePanoramaViewer",
                "value":"true"
            },
            {
                "video":"ProjectionType",
                "image":"XMP-GPano:ProjectionType",
                "value":""
            },
        ]
        Track = [
            {
                "video":"SourceImageHeight",
                "image":"XMP-GPano:CroppedAreaImageHeightPixels",
                "value":""
            },
            {
                "video":"SourceImageWidth",
                "image":"XMP-GPano:CroppedAreaImageWidthPixels",
                "value":""
            },
            {
                "video":"SourceImageHeight",
                "image":"XMP-GPano:FullPanoHeightPixels",
                "value":""
            },
            {
                "video":"SourceImageWidth",
                "image":"XMP-GPano:FullPanoWidthPixels",
                "value":""
            },
            {
                "video":"",
                "image":"XMP-GPano:CroppedAreaLeftPixels",
                "value":0
            },
            {
                "video":"",
                "image":"XMP-GPano:CroppedAreaTopPixels",
                "value":0
            },
        ]

        for i in GSpherical:
            if i["video"] != "":
                try:
                    data[i["image"]] = jsonData["Main:"+i["video"]]
                except:
                    """"""
            else:
                data[i["image"]] = i["value"]

        for i in Track:
            if i["video"] != "":
                try:
                    data[i["image"]] = jsonData["Main:"+i["video"]]
                except:
                    """"""
            else:
                data[i["image"]] = i["value"]
        return data

    def getAdditionalMetaData(self, root):
        logging.info("Getting Additional Meta Data")
        data = {}
        data["IFD0:Model"] = self.VideoData["DeviceName"]
        return data

    def getGPSValues(self, data, image):
        logging.info("Getting GPS Value Data")
        metadata = [
            {
                "video":"GPSDateTime",
                "image":["GPS:GPSDateStamp", "GPS:GPSTimeStamp"],
                "value":""
            },
            {
                "video":"GPSLatitude",
                "image":["GPS:GPSLatitude", "GPS:GPSLatitudeRef"],
                "value":""
            },
            {
                "video":"GPSLongitude",
                "image":["GPS:GPSLongitude", "GPS:GPSLongitudeRef"],
                "value":""
            },
            {
                "video":"GPSAltitude",
                "image":["GPS:GPSAltitude", "GPS:GPSAltitudeRef"],
                "value":""
            },
        ]
        _data = {}
        for mdata in metadata:
            value = data[mdata["video"]]
            value = value.split(" ")
            if mdata["video"] == "GPSDateTime":
                _data[mdata["image"][0]] = "\""+value[0]+"\""
                _data[mdata["image"][1]] = "\""+value[1]+"\""
                continue
            ref = value.pop()
            value.append(ref)
            
            if( mdata["image"][1] =="GPS:GPSAltitudeRef"):
                _data[mdata["image"][1]] = "\"Above Sea Level\""
            elif( mdata["image"][1] =="GPS:GPSLatitudeRef"):
                ref = self.latLongLocation(ref)
                _data[mdata["image"][1]] = "\""+ref+"\""
            elif( mdata["image"][1] =="GPS:GPSLongitudeRef"):
                ref = self.latLongLocation(ref)
                _data[mdata["image"][1]] = "\""+ref+"\""
            else:
                _data[mdata["image"][1]] = "\""+ref+"\""

            _data[mdata["image"][0]] = "\""+" ".join(value)+"\""
        data = _data
        if len(data) > 1:
            cmd = [] 
            for flag in [data]:
                for key, value in flag.items():
                    cmd.append("-"+key+"="+value)
            cmd.append(image)
            output = self._exiftool(cmd, 1)
            output = self._exiftool(['-ee', '-GPS:GPSAltitudeRef="Above Sea Level"', image])
        return True

    def latLongLocation(self, x):
        return {
            'E': "East",
            'W': "West",
            'N': "North",
            'S': "South"
        }.get(x, "") 
    
    def getDateTimeFirstImageMetaData(self, data):
        logging.info("Getting DateTime First Image Meta Data")
        image1 = None
        if len(data) > 0:
            image1 = data[0]["GPSDateTime"]
            dateTimeValue = image1.split('.')
            if len(dateTimeValue) > 1:
                DateTimeOriginal = dateTimeValue[0]+"Z"
                SubSecTimeOriginal = dateTimeValue[1]
                SubSecDateTimeOriginal = dateTimeValue[0]+"."+dateTimeValue[1]+"Z"
                image1 = {"DateTimeOriginal":DateTimeOriginal, "SubSecTimeOriginal":SubSecTimeOriginal, "SubSecDateTimeOriginal":SubSecDateTimeOriginal}
            else:
                image1 = None
        return image1
    
    def injectDateTimeMetadata(self, img, data):
        logging.info("Injecting Date Time Meta data")
        image1     = self.getDateTimeFirstImageMetaData(data)
        if image1 == None:
            return None
        cmd = [] 
        for flag in [image1]:
            for key, value in flag.items():
                cmd.append("-"+key+"=\""+value+"\"")
        cmd.append(img)
        output = self._exiftool(cmd)
        return output
    
    def injectMetadata(self, root):
        logging.info('Injecting metadata Spherical & additional')
        spherical  = self.getSphericalMetaData(root)
        additional = self.getAdditionalMetaData(root)
        data = [
            spherical,
            additional
        ]
        cmd = [] 
        for flag in data:
            for key, value in flag.items():
                if (type(value) == int) or (type(value) == float):
                    cmd.append("-"+key+"="+str(value))
                else:
                    cmd.append("-"+key+"=\""+str(value)+"\"")
        cmd.append(self.__folderName)
        output = self._exiftool(cmd, 1)

def printErrors(errors):
    logging.info("Printing Critical/Non-Critical Errors")
    if errors["hasErrors"] == True:
        if errors["criticalErrors"] == True:
            for k, v in errors["critical"].items():
                if v["errorStatus"] == True:
                    print("Critical Error: {}".format(v["error"]))
            exit('Script stopped due to critical error!')
        elif errors["nonCriticalErrors"] == True:
            for k, v in errors["non_critical"].items():
                if v["errorStatus"] == True:
                    print("Non-Critical Error: {}".format(v["error"]))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", type=str, help="Please input a valid video file.")
    args = parser.parse_args()
    if (args.input is not None):
        logging.basicConfig(filename='trekview-gopro.log', format='%(asctime)s %(levelname)s: LineNo:%(lineno)d %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.DEBUG)
        logging.info('Script started for file {}'.format(args.input))
        preProcess = TrekviewPreProcess(args.input)
        data = preProcess.getPreProcessData()
        data["Timewrap"] = preProcess._TimeWrap
        preProcessValidated = preProcess.validatePreProcessData()
        print(data)
        printErrors(preProcessValidated)
        mp4Video = TrekviewProcessMp4(args.input, data)
        print(data)
        printErrors(preProcessValidated)
        print("Done! You can now see your images in Img folder.")
        
