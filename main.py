import subprocess, argparse, platform, logging, datetime, fnmatch, shutil, shlex, html, copy, time, json, os, re
from pathlib import Path
from lxml import etree
from os import walk
import gpxpy

class TrekviewCommand():
    def __init__(self, config):
        """"""

    def setConfig(self, config):
        self.__config = config

    def getConfig(self):
        return copy.deepcopy(self.__config)

    def removeEntities(self, text):
        text = re.sub('"', '', html.unescape(text))
        text = re.sub("'", '', html.unescape(text))
        return html.escape(text)

    def Log(self, msg, level="info"):
        if self.__config["debug"] == True and (self.__config["verbose"] == True):
            print(msg)
        if level == "info":
            logging.info(msg)
        if level == "warning":
            logging.warning(msg)
        if level == "error":
            logging.error(msg)
        if level == "critical":
            logging.critical(msg)

    def __subprocess(self, command, sh=0):
        self.Log('Executing subprocess', "info")
        ret = False
        try:
            cmd = command
            if sh == 0:
                cmd = shlex.split(" ".join(cmd))
            output = subprocess.run(cmd, capture_output=True)
            if output.returncode == 0:
                ret = output
            else:
                self.Log(output.stderr.decode('utf-8',"ignore"), "critical")
                raise Exception(output)
        except Exception as e:
            self.Log(str(e), "critical")
            ret = None
        except:
            self.Log("Error running subprocess. Please try again.", "critical")
            exit("Error running subprocess. Please try again.")
        return ret

    def _exiftool(self, command, sh=0):
        self.Log("Starting Exiftool", "info")
        if platform.system() == "Windows":
            exiftool = "exiftool.exe"
        else:
            exiftool = "exiftool"
        command.insert(0, exiftool)
        ret = self.__subprocess(command, sh)
        if ret == None:
            self.Log("Error occured while executing exiftool.", "critical")
            exit("Error occured while executing exiftool.")
        return ret

    def _ffmpeg(self, command, sh=0):
        self.Log("Starting Ffmpeg", "info")
        if platform.system() == "Windows":
            ffmpeg = "ffmpeg.exe"
        else:
            ffmpeg = "ffmpeg"
        command.insert(0, ffmpeg)
        if self.__config["verbose"] == False:
            command.insert(1, "-q")
        ret = self.__subprocess(command, sh)
        if ret == None:
            self.Log("Error occured while executing ffmpeg, please see logs for more info.", "critical")
            exit("Error occured while executing ffmpeg, please see logs for more info.")
        return ret

    def _checkFileExists(self, filename):
        self.Log("Checking if file exists", "info")
        try:
            video_file = Path(filename)
            if video_file.is_file():
                return True
            else:
                return False
        except:
            return False

class TrekviewPreProcess(TrekviewCommand):
    __TimeWrap = False
    def _preProcessExifToolExecute(self, filename):
        self.Log("Getting Pre Process Info", "info")
        cmd = ["-ee", "-j", "-DeviceName", "-ProjectionType", "-MetaFormat", "-StitchingSoftware", "-VideoFrameRate", "-SourceImageHeight", "-SourceImageWidth", filename]
        try:
            output = self._exiftool(cmd)
            if output.returncode == 0:
                exifPreProcessData = json.loads(output.stdout.decode('utf-8',"ignore"))
                if len(exifPreProcessData) > 0:
                    preProcessValidated = self.__validatePreProcessData(exifPreProcessData[0])
                    exifPreProcessData[0]["Timewrap"] = self.__TimeWrap
                    self.__printErrors(preProcessValidated)
                    return exifPreProcessData[0]
                else:
                    return None
        except Exception as e:
            self.Log(str(e), "critical")
            exit(str(e))
        except:
            self.Log("Unable to get video file metadata.", "critical")
            exit("Unable to get video file metadata.")
    """
        checkProjectionType function
        It will check if the ProjectionType is `equirectangular`
        return (True|False)
    """  
    def __checkProjectionType(self, data):
        self.Log("Checking Pre Process Projection Type", "info")
        if 'ProjectionType' in data:
            if data['ProjectionType'] == 'equirectangular':
                return True
            return False
        else:
            return False

    """
        checkDeviceName function
        It will check if the DeviceName is `Fusion` or `GoPro Max`
        return (True|False)
    """  
    def __checkDeviceName(self, data):
        self.Log("Checking Pre Process Device Name", "info")
        devices = ["Fusion", "GoPro Max"]
        if 'DeviceName' in data:
            if data['DeviceName'] in devices:
                self.__device = data['DeviceName']
                return True
            return False
        else:
            return False

    """
        checkMetaFormat function
        It will check if the MetaFormat is `gpmd`
        return (True|False)
    """  
    def __checkMetaFormat(self, data):
        self.Log("Checking Pre Process Meta Format", "info")
        if 'MetaFormat' in data:
            if data['MetaFormat'] == "gpmd":
                return True
            return False
        else:
            return False

    """
        checkStitchingSoftware function
        It will check if the StitchingSoftware is `Fusion Studio / GStreamer` or `Spherical Metadata Tool`
        return (True|False)
    """ 
    def __checkStitchingSoftware(self, data):
        self.Log("Checking Pre Process Stitching Software", "info")
        softwares = ["Fusion Studio / GStreamer", "Spherical Metadata Tool"]
        if 'StitchingSoftware' in data:
            if data['StitchingSoftware'] in softwares:
                return True
            return False
        else:
            return False

    """
        checkVideoFrameRate function
        It will check if the VideoFrameRate is greater than 5
        return (True|False)
    """ 
    def __checkVideoFrameRate(self, data):
        self.Log("Checking Pre Process Video FrameRate", "info")
        if 'VideoFrameRate' in data:
            if data['VideoFrameRate'] > 5:
                return True
            return False
        else:
            return False

    """
        validatePreProcessData function
        It will validate the metadata for `pre-process-1`
        returns a variable which contains all the error information. (Object)
    """ 
    def __validatePreProcessData(self, data):
        __TimeWrap = False
        self.Log("Validate Pre Process Video", "info")
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
        projection = self.__checkProjectionType(data)

        #Validate Critical Errors
        if projection is True:
            errors['critical']['projection']['errorStatus'] = False
        else:
            errors['critical']['projection']['errorStatus'] = True
            errors['criticalErrors'] = True

        devicename = self.__checkDeviceName(data)
        if devicename is True:
            errors['critical']['deviceName']['errorStatus'] = False
        else:
            errors['critical']['deviceName']['errorStatus'] = True
            errors['criticalErrors'] = True

        metaformat = self.__checkMetaFormat(data)
        if metaformat is True:
            errors['critical']['metaFormat']['errorStatus'] = False
        else:
            errors['critical']['metaFormat']['errorStatus'] = True
            errors['criticalErrors'] = True
            
        stitchingSoftware = self.__checkMetaFormat(data)
        if stitchingSoftware is True:
            errors['critical']['stitchingSoftware']['errorStatus'] = False
        else:
            errors['critical']['stitchingSoftware']['errorStatus'] = True
            errors['criticalErrors'] = True
            

        #Validate Non-Critical Errors
        videoFrameRate = self.__checkMetaFormat(data)
        if videoFrameRate is True:
            errors['non_critical']['videoFrameRate']['errorStatus'] = False
        else:
            errors['non_critical']['videoFrameRate']['errorStatus'] = True
            errors['nonCriticalErrors'] = True
            
        if metaformat is True and (self.__device == "GoPro Max"):
            errors['non_critical']['metaFormatMax']['errorStatus'] = True
            __TimeWrap = True
        else:
            errors['non_critical']['metaFormatMax']['errorStatus'] = False
            errors['nonCriticalErrors'] = True

        if (errors['criticalErrors'] == True) or (errors['nonCriticalErrors'] == True):
            errors['hasErrors'] = True
            
        return errors
    
    def __printErrors(self, errors):
        self.Log("Printing Critical/Non-Critical Errors", "info")
        if errors["hasErrors"] == True:
            if errors["criticalErrors"] == True:
                for k, v in errors["critical"].items():
                    if v["errorStatus"] == True:
                        self.Log("Critical Error: {}".format(v["error"]), "critical")
                        print("Critical Error: {}".format(v["error"]))
                exit('Script stopped due to critical error!')
            elif errors["nonCriticalErrors"] == True:
                for k, v in errors["non_critical"].items():
                    if v["errorStatus"] == True:
                        self.Log("Non-Critical Error: {}".format(v["error"]), "info")

class TrekviewProcessMp4(TrekviewCommand):

    def __getGPSw(self, el, nsmap, Timewrap=False):
        Track = "Track3"
        if Timewrap == True:
            Track = "Track2"
        data = {"GPSDateTime": "", "GPSData":[]}
        if el == None:
            return None
        else:
            data["GPSDateTime"] = el.text
        self.Log("#{}".format(el.text), "info")
        for i in range(0, 500):
            el = el.getnext()
            if el == None:
                break
            if el.tag == "{"+nsmap[Track]+"}GPSDateTime":
                break
            if el.tag == "{"+nsmap[Track]+"}GPSLatitude":
                data["GPSData"].append({"GPSLatitude": el.text})
            if el.tag == "{"+nsmap[Track]+"}GPSLongitude":
                data["GPSData"].append({"GPSLongitude": el.text})
            if el.tag == "{"+nsmap[Track]+"}GPSAltitude":
                data["GPSData"].append({"GPSAltitude": el.text})
        return data

    def _processXMLGPS(self, filename):
        output = self._exiftool(["-ee", "-G3", "-api", "LargeFileSupport=1", "-X", filename])
        if output is None:
            self.Log("Unable to get metadata information", "critical")
            exit("Unable to get metadata information")
        __config = self.getConfig()
        Track = "Track3"
        Timewrap = False
        if (__config["jsonData"]["Timewrap"] == True) and (__config["jsonData"]["Device"] == "GoPro Max"):
            Track = "Track2"
            Timewrap = True

        xmlData = output.stdout.decode('utf-8',"ignore")
        gpsData = []
        xmlFileName = os.getcwd() + os.sep + 'VIDEO_META.xml'
        with open(xmlFileName, "w") as f:
            f.write(xmlData)
            f.close()
            data = []
            tree = etree.parse(xmlFileName)
            root = tree.getroot()
            nsmap = root[0].nsmap

            for el in root[0]:
                if el.tag == "{"+nsmap[Track]+"}GPSDateTime":
                    data = self.__getGPSw(el, nsmap, Timewrap)
                    datag = []
                    j = 0
                    for i in range(0, len(data["GPSData"])):
                        if j >= len(data["GPSData"]):
                            break
                        datag.append({
                            "GPSLatitude": data["GPSData"][j]["GPSLatitude"],
                            "GPSLongitude": data["GPSData"][j+1]["GPSLongitude"],
                            "GPSAltitude": data["GPSData"][j+2]["GPSAltitude"]
                        })
                        j = j+3
                    gpsData.append({
                        "GPSDateTime": data["GPSDateTime"],
                        "GPSData": datag
                    })
            return gpsData
        return []
    def _breakIntoFrames(self, filename, frameRate, folder):
        if os.path.exists(folder):
            shutil.rmtree(folder)
        os.makedirs(folder, exist_ok=True) 
        cmd = ["-i", filename, "-r", str(frameRate), folder+os.sep+"img%d.jpg"]
        output = self._ffmpeg(cmd, 1)
        if output.returncode != 0:
            return False 
        else:
            return True

    def _getTimesBetween(self, start, end, frameRate):
        t_start = datetime.datetime.strptime(start, "%Y:%m:%d %H:%M:%S.%f")
        t_end = datetime.datetime.strptime(end, "%Y:%m:%d %H:%M:%S.%f")
        diff = t_end - t_start
        diff0 = diff/float(frameRate)
        times = []
        t = t_start
        for i in range(0, frameRate-1):
            t = t+diff0
            times.append(t)
        return times

class TrekViewGoProMp4(TrekviewPreProcess, TrekviewProcessMp4):
    def __init__(self, args):

        __configData = {
            "frameRate": args.frame_rate,
            "debug": args.debug,
            "verbose": args.verbose,
        }

        self.setConfig(__configData)
        
        self.__validate(args)

        imageFolder = os.getcwd() + os.sep + 'Img'
        filename = args.input
        frameRate = args.frame_rate

        preProcessDataJSON = self._preProcessExifToolExecute(args.input)
        if preProcessDataJSON is None:
            self.Log("Unable to get metadata from video.", "critical")
            exit("Unable to get metadata from video.")

        __configData["jsonData"] = preProcessDataJSON
        self.setConfig(__configData)

        framesBroken = self._breakIntoFrames(filename, frameRate, imageFolder)
        if framesBroken == False:
            self.Log("Unable to extract frames from video.", "critical")
            exit("Unable to extract frames from video.")
        images = fnmatch.filter(os.listdir(imageFolder), '*.jpg')
        imagesCount = len(images)
        preProcessDataXMLGPS = self._processXMLGPS(args.input)
        if len(preProcessDataXMLGPS) <= 0:
            self.Log("Unable to get metadata from video.", "critical")
            exit("Unable to get metadata from video.")

        start = datetime.datetime.strptime(preProcessDataXMLGPS[0]["GPSDateTime"], "%Y:%m:%d %H:%M:%S.%f")
        end = datetime.datetime.strptime(preProcessDataXMLGPS[-1]["GPSDateTime"], "%Y:%m:%d %H:%M:%S.%f")
        duration = end - start
        
        gpsData = []

        i = 0
        for data in preProcessDataXMLGPS:
            if i < len(preProcessDataXMLGPS)-1:

                gpsData.append({
                    "GPSDateTime": data["GPSDateTime"],
                    "GPSLatitude": data["GPSData"][0]["GPSLatitude"],
                    "GPSLongitude": data["GPSData"][0]["GPSLongitude"],
                    "GPSAltitude": data["GPSData"][0]["GPSAltitude"],
                })

                betweenTimes = self._getTimesBetween(
                    preProcessDataXMLGPS[i]["GPSDateTime"], 
                    preProcessDataXMLGPS[i+1]["GPSDateTime"], 
                    frameRate
                )
                gpsIncFr = frameRate-1
                gpsInc = frameRate-1
                for bt in betweenTimes:
                    gpsData.append({
                        "GPSDateTime": datetime.datetime.strftime(bt, "%Y:%m:%d %H:%M:%S.%f"),
                        "GPSLatitude": data["GPSData"][gpsInc]["GPSLatitude"],
                        "GPSLongitude": data["GPSData"][gpsInc]["GPSLongitude"],
                        "GPSAltitude": data["GPSData"][gpsInc]["GPSAltitude"],
                    })
                    gpsInc = gpsInc + gpsIncFr
            else:
                gpsData.append({
                    "GPSDateTime": data["GPSDateTime"],
                    "GPSLatitude": data["GPSData"][0]["GPSLatitude"],
                    "GPSLongitude": data["GPSData"][0]["GPSLongitude"],
                    "GPSAltitude": data["GPSData"][0]["GPSAltitude"],
                })
                bt = datetime.datetime.strptime(data["GPSDateTime"], "%Y:%m:%d %H:%M:%S.%f")
                betweenTimes = self._getTimesBetween(
                    data["GPSDateTime"], 
                    datetime.datetime.strftime(bt + datetime.timedelta(0,1), "%Y:%m:%d %H:%M:%S.%f"), 
                    frameRate
                )
                gpsIncFr = frameRate-1
                gpsInc = frameRate-1
                j = 0
                for ei in range(len(gpsData), imagesCount):
                    if gpsInc < len(data["GPSData"]):
                        if j < len(betweenTimes):
                            gpsData.append({
                                "GPSDateTime": datetime.datetime.strftime(betweenTimes[j], "%Y:%m:%d %H:%M:%S.%f"),
                                "GPSLatitude": data["GPSData"][gpsInc]["GPSLatitude"],
                                "GPSLongitude": data["GPSData"][gpsInc]["GPSLongitude"],
                                "GPSAltitude": data["GPSData"][gpsInc]["GPSAltitude"],
                            })
                            j = j+1
                        else:
                            os.unlink(imageFolder+os.sep+"img{}.jpg".format(ei+1))
                    else:
                        os.unlink(imageFolder+os.sep+"img{}.jpg".format(ei+1))
                        self.Log("No gps data available for this image.", "info")
                    gpsInc = gpsInc + gpsIncFr
            i = i+1
        images = fnmatch.filter(os.listdir(imageFolder), '*.jpg')
        imagesCount = len(images)
        metaData = {
            "gps": gpsData,
            "json": preProcessDataJSON
        }
        self.__injectMetadat(metaData, images, imageFolder)
        exit()
        
    def __injectMetadat(self, metaData, images, imageFolder):

        gpsMetaData = metaData["gps"]
        jsonMetaData = metaData["json"]

        gpx = gpxpy.gpx.GPX()

        # Create first track in our GPX:
        gpx_track = gpxpy.gpx.GPXTrack()
        gpx.tracks.append(gpx_track)

        # Create first segment in our GPX track:
        gpx_segment = gpxpy.gpx.GPXTrackSegment()
        gpx_track.segments.append(gpx_segment)

        for i in range(0, len(images)):
            
            tt = gpsMetaData[i]["GPSDateTime"].split(".")
            t = datetime.datetime.strptime(gpsMetaData[i]["GPSDateTime"], "%Y:%m:%d %H:%M:%S.%f")
            deg, minutes, seconds, direction = re.split('[deg\'"]+', gpsMetaData[i]["GPSLatitude"])
            a = (float(deg) + float(minutes)/60 + float(seconds)/(60*60)) * (-1 if direction in ['W', 'S'] else 1)
            deg, minutes, seconds, direction = re.split('[deg\'"]+', gpsMetaData[i]["GPSLongitude"])
            b = (float(deg) + float(minutes)/60 + float(seconds)/(60*60)) * (-1 if direction in ['W', 'S'] else 1)
            alt = gpsMetaData[i]["GPSAltitude"].split(" ")[0]
            gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(latitude=a, longitude=b, time=t, elevation=alt))

            self.Log("{} {} {} {} {}".format(gpsMetaData[i]["GPSDateTime"], gpsMetaData[i]["GPSLatitude"], a, gpsMetaData[i]["GPSLongitude"], b), "info")

            if i < len(gpsMetaData)-1:
                t1 = datetime.datetime.strptime(gpsMetaData[i+1]["GPSDateTime"], "%Y:%m:%d %H:%M:%S.%f")
                self.Log("{} {} {}".format(t, t1, t1-t), "info")

            cmdMetaData = [
                '-DateTimeOriginal="{0}Z"'.format(self.removeEntities(tt[0])),
                '-SubSecTimeOriginal="{0}"'.format(self.removeEntities(tt[1])),
                '-SubSecDateTimeOriginal="{0}Z"'.format(self.removeEntities(".".join(tt))),
                '-IFD0:Model="{}"'.format(self.removeEntities(jsonMetaData["DeviceName"])),
                '-XMP-GPano:StitchingSoftware="{}"'.format(self.removeEntities(jsonMetaData["StitchingSoftware"])),
                '-XMP-GPano:SourcePhotosCount="{}"'.format(2),
                '-XMP-GPano:UsePanoramaViewer="{}"'.format("true"),
                '-XMP-GPano:ProjectionType="{}"'.format(self.removeEntities(jsonMetaData["ProjectionType"])),
                '-XMP-GPano:CroppedAreaImageHeightPixels="{}"'.format(jsonMetaData["SourceImageHeight"]),
                '-XMP-GPano:CroppedAreaImageWidthPixels="{}"'.format(jsonMetaData["SourceImageWidth"]),
                '-XMP-GPano:FullPanoHeightPixels="{}"'.format(jsonMetaData["SourceImageHeight"]),
                '-XMP-GPano:FullPanoWidthPixels="{}"'.format(jsonMetaData["SourceImageWidth"]),
                '-XMP-GPano:CroppedAreaLeftPixels="{}"'.format(0),
                '-XMP-GPano:CroppedAreaTopPixels="{}"'.format(0),
                '-overwrite_original'
            ]
            
            cmdMetaData.append(imageFolder+os.sep+"img"+str(i+1)+".jpg")

            output = self._exiftool(cmdMetaData)
            if output.returncode != 0:
                self.Log(output, "error")
            else:
                self.Log(output, "info")

        time.sleep(2)

        gpxData = gpx.to_xml() 
        gpxFileName = os.getcwd() + os.sep + 'VIDEO_META.gpx'
        with open(gpxFileName, 'w') as f:
            f.write(gpxData)
            f.close()
            cmd = ["-geotag", gpxFileName, "'-geotime<${datetimeoriginal}-00:00'", '-overwrite_original', imageFolder]
            output = self._exiftool(cmd)
            if output.returncode != 0:
                self.Log(output, "error")
            else:
                self.Log(output, "info")


    def __validate(self, args):
        check = self._checkFileExists(args.input)
        if check == False:
            exit("{} does not exists.".format(args.input))
        if (args.frame_rate is not None):
            frameRate = int(args.frame_rate)
            if frameRate >= 10:
                exit("Frame rate value must be less than 10.")

        if (args.debug is not None):
            debug = True
        else:
            print("debug value is not provided, so by default debugging is off.")

        if (args.verbose is not None):
            quiet = False
        else:
            print("verbosity is not enabled, so by default is quiet.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str, help="Please input a valid video file.")
    parser.add_argument("-f", "--frame-rate", type=int, help="Frame rate for ffmpeg command.", default=1)
    parser.add_argument("-d", "--debug", action='store_true', help="Print out debuggin info.")
    parser.add_argument("-v", "--verbose", action='store_true', help="Use this option to enable verbosity or not.")
    args = parser.parse_args()
    if (args.input is not None):
        logging.basicConfig(filename='trekview-gopro.self.Log', format='%(asctime)s %(levelname)s: LineNo:%(lineno)d %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.DEBUG)
        goProMp4 = TrekViewGoProMp4(args)
    else:
        exit("Please use a valid video file.")
