import subprocess, argparse, platform, logging, datetime, fnmatch, shutil, shlex, html, copy, time, json, csv, os, re
from pathlib import Path
from lxml import etree
from os import walk
import itertools
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

    def latLngToDecimal(self, latLng):
        deg, minutes, seconds, direction = re.split('[deg\'"]+', latLng)
        return (float(deg.strip()) + float(minutes.strip())/60 + float(seconds.strip())/(60*60)) * (-1 if direction.strip() in ['W', 'S'] else 1)

    def latLngToDirection(self, latLng):
        deg, minutes, seconds, direction = re.split('[deg\'"]+', latLng)
        return direction.strip()

    def __subprocess(self, command, sh=0):
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
                logging.critical(output.stderr.decode('utf-8',"ignore"))
                raise Exception(output.stderr.decode('utf-8',"ignore"))
        except Exception as e:
            if type(e) is TypeError:
                logging.error(str(e))
            else:
                logging.error(e.stderr.decode('utf-8',"ignore"))
            ret = None
        except:
            logging.critical("Error running subprocess. Please try again.")
            exit("Error running subprocess. Please try again.")
        return ret

    def _exiftool(self, command, sh=0):
        logging.info("Starting Exiftool")
        if platform.system() == "Windows":
            exiftool = "exiftool.exe"
        else:
            exiftool = "exiftool"
        command.insert(0, exiftool)
        ret = self.__subprocess(command, sh)
        if ret == None:
            logging.critical("Error occured while executing exiftool.")
            exit("Error occured while executing exiftool.")
        return ret

    def _ffmpeg(self, command, sh=0):
        logging.info("Starting Ffmpeg")
        if platform.system() == "Windows":
            ffmpeg = "ffmpeg.exe"
        else:
            ffmpeg = "ffmpeg"
        command.insert(0, ffmpeg)
        command.insert(len(command)-1, "-q:v")
        command.insert(len(command)-1, str(self.__config["quality"]))
        ret = self.__subprocess(command, sh)
        if ret == None:
            logging.critical("Error occured while executing ffmpeg, please see logs for more info.")
            exit("Error occured while executing ffmpeg, please see logs for more info.")
        return ret

    def _checkFileExists(self, filename):
        logging.info("Checking if file exists")
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
        logging.info("Getting Pre Process Info")
        cmd = ["-ee", "-j", "-G1:3","-DeviceName", "-ProjectionType", "-MetaFormat", "-StitchingSoftware", "-VideoFrameRate", "-SourceImageHeight", "-SourceImageWidth", "-FileSize", "-FileType", "-FileTypeExtension", "-CompressorName", filename]
        try:
            output = self._exiftool(cmd)
            if output.returncode == 0:
                exifPreProcessData = json.loads(output.stdout.decode('utf-8',"ignore"))
                
                if len(exifPreProcessData) > 0:
                    
                    jsonData = {
                        "SourceFile": "",
                        "DeviceName": "",
                        "StitchingSoftware": "",
                        "ProjectionType": "",
                        "MetaFormat": [],
                        "VideoFrameRate": "",
                        "SourceImageHeight": "",
                        "SourceImageWidth": "",
                        "FileSize": "",
                        "FileType": "",
                        "FileTypeExtension": "",
                        "CompressorName": "",
                        "Track": "Track3",
                    }

                    for key, value in exifPreProcessData[0].items():
                        keyInfo = key.split(":")
                        kName = keyInfo[-1]
                        if kName != "CompressorName":
                            if kName == "MetaFormat":
                                jsonData[kName].append(value)
                                if value == "gpmd":
                                    jsonData["Track"] = keyInfo[0]
                            else:
                                jsonData[kName] = value
                    
                    for key, value in exifPreProcessData[0].items():
                        keyInfo = key.split(":")
                        kName = keyInfo[-1]
                        if kName == "CompressorName" and key == "Track1:Main:CompressorName":
                            jsonData[kName] = value
                            break
                    preProcessValidated = self.__validatePreProcessData(jsonData)
                    if (jsonData["ProjectionType"] == "equirectangular") and self.__checkMetaFormat and jsonData["DeviceName"].strip() == 'GoPro Max':
                        self.__TimeWrap = False
                        jsonData["Timewrap"] = self.__TimeWrap
                        #jsonData["Track"] = "Track2"
                    else:
                        self.__TimeWrap = False
                        jsonData["Timewrap"] = self.__TimeWrap

                    self.__printErrors(preProcessValidated)
                    return jsonData
                else:
                    return None
        except Exception as e:
            logging.critical(str(e))
            exit(str(e))
        except:
            logging.critical("Unable to get video file metadata.")
            exit("Unable to get video file metadata.")
    """
        checkProjectionType function
        It will check if the ProjectionType is `equirectangular`
        return (True|False)
    """  
    def __checkProjectionType(self, data):
        logging.info("Checking Pre Process Projection Type")
        if 'ProjectionType' in data:
            if data['ProjectionType'] == 'equirectangular':
                return True
            else:
                if self.__checkMetaFormat(data):
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
        logging.info("Checking Pre Process Device Name")
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
        logging.info("Checking Pre Process Meta Format")
        if 'MetaFormat' in data:
            if "gpmd" in data['MetaFormat']:
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
        logging.info("Checking Pre Process Stitching Software")
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
        logging.info("Checking Pre Process Video FrameRate")
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

        if projection is True and (metaformat is True) and (self.__device.strip() == "GoPro Max"):
            errors['non_critical']['metaFormatMax']['errorStatus'] = True
            __TimeWrap = True
        else:
            errors['non_critical']['metaFormatMax']['errorStatus'] = False
            errors['nonCriticalErrors'] = True

        if (errors['criticalErrors'] == True) or (errors['nonCriticalErrors'] == True):
            errors['hasErrors'] = True
            
        return errors
    
    def __printErrors(self, errors):
        logging.info("Printing Critical/Non-Critical Errors")
        if errors["hasErrors"] == True:
            if errors["criticalErrors"] == True:
                for k, v in errors["critical"].items():
                    if v["errorStatus"] == True:
                        logging.critical("Critical Error: {}".format(v["error"]))
                        print("Critical Error: {}".format(v["error"]))
                exit('Script stopped due to critical error!')
            elif errors["nonCriticalErrors"] == True:
                for k, v in errors["non_critical"].items():
                    if v["errorStatus"] == True:
                        logging.info("Non-Critical Error: {}".format(v["error"]))

class TrekviewProcessMp4(TrekviewCommand):

    """
        __getGPSw function
        This helper function is used to get gps data of a particular block.
    """ 

    def __getGPSw(self, el, nsmap):
        __config = self.getConfig()
        Track = __config["jsonData"]["Track"]
        data = {"GPSDateTime": "", "GPSData":[]}
        if el == None:
            return None
        else:
            data["GPSDateTime"] = el.text
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

    """
        _processXMLGPS function
        This function is used to process xml and extract all the metadata related to gps.
    """ 

    def _processXMLGPS(self, filename):
        output = self._exiftool(["-ee", "-G3", "-api", "LargeFileSupport=1", "-X", filename])
        if output is None:
            logging.critical("Unable to get metadata information")
            exit("Unable to get metadata information")
        __config = self.getConfig()
        Track = __config["jsonData"]["Track"]
        xmlData = output.stdout.decode('utf-8',"ignore")
        gpsData = []
        xmlFileName = __config["imageFolderPath"] + os.sep + __config["imageFolder"] + '.xml'
        with open(xmlFileName, "w") as f:
            f.write(xmlData)
            f.close()
            data = []
            tree = etree.parse(xmlFileName)
            root = tree.getroot()
            nsmap = root[0].nsmap
            for el in root[0]:
                if el.tag == "{"+nsmap[Track]+"}GPSDateTime":
                    data = self.__getGPSw(el, nsmap)
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
            #os.unlink(xmlFileName)
            return gpsData
        return []

    """
        _breakIntoFrames function
        This function is used to extract all the images using ffmpeg.
    """ 

    def _breakIntoFrames(self, filename, frameRate, folderPath, imageFolder):
        if os.path.exists(folderPath):
            shutil.rmtree(folderPath)
        os.makedirs(folderPath, exist_ok=True) 
        __config = self.getConfig()
        test_str = ""
        if __config["debug"] is True:
            if "timeWarp" in __config:
                tw = "-t_{}x".format(__config["timeWarp"])
            else:
                tw = ""
            test_str = "-q_{}-r_{}fps{}".format(__config["quality"], __config["frameRate"], tw)
        cmd = ["-i", filename, "-r", str(frameRate), folderPath+os.sep+"{}{}_%06d.jpg".format(imageFolder, test_str)]
        output = self._ffmpeg(cmd, 1)
        if output.returncode != 0:
            return False 
        else:
            return True

    """
        _getTimesBetween function
        This function is used to get times between a start time and end time.
    """ 

    def _getTimesBetween(self, start, end, frameRate, frlen):
        print(start, end)
        t_start = datetime.datetime.strptime(start, "%Y:%m:%d %H:%M:%S.%f")
        t_end = datetime.datetime.strptime(end, "%Y:%m:%d %H:%M:%S.%f")
        diff = t_end - t_start
        diff0 = diff/float(frameRate)
        
        times = []
        t = t_start
        frange = round(frlen/frameRate)
        for i in range(0, frameRate-1):
            t = t+diff0
            times.append(t)
        return times

class TrekViewGoProMp4(TrekviewPreProcess, TrekviewProcessMp4):
    """
        __init__ function
        Main entry point where if validation passes images are extracted using ffmpeg and then metadata is injected using exiftool. 
    """  
    def __init__(self, args, dateTimeCurrent):
        self.__allGPSPoints = []

        __configData = {
            "frameRate": args.frame_rate,
            "debug": args.debug,
            "quality": args.quality,
        }

        self.setConfig(__configData)

        self.__validate(args)

        filename = args.input
        frameRate = args.frame_rate
        imageFolder = os.path.basename(filename).split(".")[0]
        imageFolderPath = os.getcwd() + os.sep + imageFolder+"_"+dateTimeCurrent

        preProcessDataJSON = self._preProcessExifToolExecute(args.input)

        if preProcessDataJSON is None:
            logging.critical("Unable to get metadata from video.")
            exit("Unable to get metadata from video.")

        FileType = ["MP4", "360"]
        if preProcessDataJSON["FileType"].strip() not in FileType:
            logging.critical("The following filetype {} is not supported. Please upload only .mp4 or .360 videos.".format(preProcessDataJSON["FileType"]))
            exit("The following filetype {} is not supported. Please upload only .mp4 or .360 videos.".format(preProcessDataJSON["FileType"]))
        if preProcessDataJSON["FileType"].strip() == "360":
            if preProcessDataJSON["CompressorName"] == "H.265":
                logging.critical("This does not appear to be a GoPro .360 file. Please use the .360 video created from your GoPro camera only.")
                exit("This does not appear to be a GoPro .360 file. Please use the .360 video created from your GoPro camera only.")
        
        fileStat = os.stat(filename)
        if fileStat.st_size > 1000000000:
            logging.critical("The following file {} is too large. The maximum size for a single video is 5GB".format(filename))
            exit("The following file {} is too large. The maximum size for a single video is 5GB".format(filename))

        __configData["jsonData"] = preProcessDataJSON
        __configData["imageFolder"] = imageFolder
        __configData["imageFolderPath"] = imageFolderPath
        if args.time_warp is not None:
            __configData["timeWarp"] = int(args.time_warp.replace("x", ""))
        
        self.setConfig(__configData)

        framesBroken = self._breakIntoFrames(filename, frameRate, imageFolderPath, imageFolder)
        if framesBroken == False:
            logging.critical("Unable to extract frames from video.")
            exit("Unable to extract frames from video.")
        images = fnmatch.filter(os.listdir(imageFolderPath), '*.jpg')
        imagesCount = len(images)
        
        preProcessDataXMLGPS = self._processXMLGPS(args.input)
        if len(preProcessDataXMLGPS) <= 0:
            logging.critical("Unable to get metadata from video.")
            exit("Unable to get metadata from video.")
        images.sort()
        print("Total images: {}".format(imagesCount))
        times = self.getLinearTimes(preProcessDataXMLGPS, frameRate, images)
        if args.time_warp is not None:
            iImages = self.extractTimewrapXMLData(preProcessDataXMLGPS, images, frameRate, copy.deepcopy(__configData))
        else:
            iImages = []
            gpsPoints = self.extractXMLDataNormal(preProcessDataXMLGPS, images, frameRate, copy.deepcopy(__configData))
            gpsData = self.mapGPSPointsToTimes(times, gpsPoints)
            for data in gpsData:
                iImages.append({
                    "image": data["image"],
                    "GPSDateTime": datetime.datetime.strftime(data["time"], "%Y:%m:%d %H:%M:%S.%f"),
                    "GPSLatitude": data["GPSData"]["GPSLatitude"],
                    "GPSLongitude": data["GPSData"]["GPSLongitude"],
                    "GPSAltitude": data["GPSData"]["GPSAltitude"],
                })
        
        metaData = {
            "gps": iImages,
            "json": preProcessDataJSON
        }
        self.__injectMetadata(metaData, iImages, imageFolderPath)

    """
        extractTimewrapXMLData function
        This function is used to get GPS Data from video xml for timewarp video
    """ 

    def extractTimewrapXMLData(self, preProcessDataXMLGPS, images, frameRate, __configData):
        i = 0
        iCounter = 0
        iImages = []
        tw = __configData["timeWarp"]
        tdiff = tw/float(frameRate)
        _gpsDataInitial = {}
        initialTime = preProcessDataXMLGPS[0]["GPSDateTime"]
        initialTime = None
        betweenTimes = []
        for data in preProcessDataXMLGPS:
            dTime = datetime.datetime.strptime(data["GPSDateTime"], "%Y:%m:%d %H:%M:%S.%f")
            if initialTime is None:
                initialTime = dTime
            _gpsDataInitial[dTime] = data["GPSData"][0]
            betweenTimes.append(dTime)
        t  = 0
        lst = None
        for i in range(0, len(images)):
            t = initialTime+datetime.timedelta(0, t) 
            if len(betweenTimes) < 1:
                break
            z = min(betweenTimes, key=lambda x: abs(x - t))
            for j in range(0, len(betweenTimes)):
                if z == betweenTimes[j]:
                    del betweenTimes[j]
                    break
            iImages.append({
                "image": images[iCounter],
                "GPSDateTime": datetime.datetime.strftime(z, "%Y:%m:%d %H:%M:%S.%f"),
                "GPSLatitude": _gpsDataInitial[z]["GPSLatitude"],
                "GPSLongitude": _gpsDataInitial[z]["GPSLongitude"],
                "GPSAltitude": _gpsDataInitial[z]["GPSAltitude"],
            })
            initialTime = t
            lst = t
            t = tdiff
            iCounter = iCounter+1
            print("{} {} {} {} {}".format(datetime.datetime.strftime(initialTime, "%Y:%m:%d %H:%M:%S.%f"), datetime.datetime.strftime(z, "%Y:%m:%d %H:%M:%S.%f"), _gpsDataInitial[z]["GPSLatitude"], _gpsDataInitial[z]["GPSLongitude"], _gpsDataInitial[z]["GPSAltitude"]))


        while iCounter < len(images):
            logging.error("File deleted as no gps data available. "+__configData["imageFolderPath"]+os.sep+"{}".format(images[iCounter]))
            print("File deleted as no gps data available. "+__configData["imageFolderPath"]+os.sep+"{}".format(images[iCounter]))
            os.unlink(__configData["imageFolderPath"]+os.sep+"{}".format(images[iCounter]))
            iCounter = iCounter+1
        return iImages
    
    """
        getLinearTimes function
        This function is used to get linear timestamp at a constant step level
    """ 

    def getLinearTimes(self, preProcessDataXMLGPS, frameRate, images):
        times = []
        if len(preProcessDataXMLGPS) > 0:
            diff = (100.0/float(frameRate))/100.0
            t = datetime.datetime.strptime(preProcessDataXMLGPS[0]["GPSDateTime"], "%Y:%m:%d %H:%M:%S.%f")
            times.append({"time":t, "image":images[0]})
            for i in range(1, len(images)):
                t = t+datetime.timedelta(0, diff)
                times.append({"time":t, "image":images[i]})
        return times

    """
        extractXMLData function
       This function is used to get GPS Data from video xml
    """ 

    def extractXMLData(self, preProcessDataXMLGPS, images, frameRate, __configData):
        gpsData = []
        i = 0
        iCounter = 0
        iImages = []
        times = self.getLinearTimes(preProcessDataXMLGPS, frameRate, len(images))
        print(len(times), times)
        exit()
        for data in preProcessDataXMLGPS:
            print("****")
            _gpsData = {}
            bt1 = preProcessDataXMLGPS[i]["GPSDateTime"]
            if i < len(preProcessDataXMLGPS)-1:
                bt2 = preProcessDataXMLGPS[i+1]["GPSDateTime"]
                _gpsData = self.getGpsData(data["GPSData"], bt1, bt2, frameRate, copy.deepcopy(__configData))
            else:
                _gpsData = self.getGpsData(data["GPSData"], data["GPSDateTime"], None, frameRate, copy.deepcopy(__configData))
            for k, vData in _gpsData.items():
                if iCounter >= len(images):
                    break
                if vData is not None:
                    iImages.append({
                        "image": images[iCounter],
                        "GPSDateTime": datetime.datetime.strftime(k, "%Y:%m:%d %H:%M:%S.%f"),
                        "GPSLatitude": vData["GPSLatitude"],
                        "GPSLongitude": vData["GPSLongitude"],
                        "GPSAltitude": vData["GPSAltitude"],
                    })
                    lat = vData["GPSLatitude"]
                    lng = vData["GPSLongitude"]
                else:
                    logging.error("File deleted as no gps data available. "+__configData["imageFolderPath"]+os.sep+"{}".format(images[iCounter]))
                    print("File deleted as no gps data available. "+__configData["imageFolderPath"]+os.sep+"{}".format(images[iCounter]))
                    os.unlink(__configData["imageFolderPath"]+os.sep+"{}".format(images[iCounter]))
                    lat = "N/A"
                    lng = "N/A"
                #print(len(data["GPSData"]), datetime.datetime.strftime(k, "%Y:%m:%d %H:%M:%S.%f"), "\""+lat+"\",", "\""+lng+"\"", "image:"+str(iCounter+1))
                iCounter = iCounter+1
            i = i+1

        while iCounter < len(images):
            logging.error("File deleted as no gps data available. "+__configData["imageFolderPath"]+os.sep+"{}".format(images[iCounter]))
            print("File deleted as no gps data available. "+__configData["imageFolderPath"]+os.sep+"{}".format(images[iCounter]))
            os.unlink(__configData["imageFolderPath"]+os.sep+"{}".format(images[iCounter]))
            iCounter = iCounter+1
        return iImages

    """
        extractXMLDataNormal function
       This function is used to get GPS Data from video xml for non timewarp video
    """ 

    def extractXMLDataNormal(self, preProcessDataXMLGPS, images, frameRate, __configData):
        i = 0
        gpsPoints = {}
        for data in preProcessDataXMLGPS:
            _gpsData = {}
            bt1 = preProcessDataXMLGPS[i]["GPSDateTime"]
            if i < len(preProcessDataXMLGPS)-1:
                bt2 = preProcessDataXMLGPS[i+1]["GPSDateTime"]
                _gpsData = self.getGpsData(data["GPSData"], bt1, bt2, frameRate, copy.deepcopy(__configData))
            else:
                _gpsData = self.getGpsData(data["GPSData"], bt1, None, frameRate, copy.deepcopy(__configData))
            for k, v in _gpsData.items():
                gpsPoints[k] = v
            i = i+1
        return gpsPoints

    """
        mapGPSPointsToTimes function
       This function is used to get map photo time to the closest gps time available
    """ 

    def mapGPSPointsToTimes(self, times, gpsPoints):
        betweenTimes = []
        gpsData = []
        for k, v in gpsPoints.items():
            betweenTimes.append(k)
        for tdict in times:
            t = tdict["time"]
            z = min(betweenTimes, key=lambda x: abs(x - t))
            gpsData.append({"time":t, "image": tdict["image"], "GPSData": gpsPoints[z]})
            print("{} {} {} {} {}".format(datetime.datetime.strftime(t, "%Y:%m:%d %H:%M:%S.%f"), datetime.datetime.strftime(z, "%Y:%m:%d %H:%M:%S.%f"), gpsPoints[z]["GPSLatitude"], gpsPoints[z]["GPSLongitude"], gpsPoints[z]["GPSAltitude"]))
        return gpsData

    """
       getGpsDataOld function
       This function is used to get map photo time to the closest gps time available
       This function needs to be removed in future
    """ 

    def getGpsDataOld(self, gpsData, startTime, endTime, frameRate, configData):
        t_start = datetime.datetime.strptime(startTime, "%Y:%m:%d %H:%M:%S.%f")
        if endTime is not None:
            t_end = datetime.datetime.strptime(endTime, "%Y:%m:%d %H:%M:%S.%f")
        else:
            t_end = None
        timeDifference = self.getGpsDataTimeDifference(t_start, t_end, frameRate, len(gpsData))
        if t_end is None:
            if len(timeDifference) > 0:
                t_end = timeDifference[-1]
            else:
                t_end = None
        timePoints = self.getGpsDataTimePoints(gpsData, t_start, t_end, frameRate, configData)
        data = {
            "timeDifference": timeDifference,
            "timePoints": timePoints
        }
        betweenTimes = []
        gpsDataLatest = {}
        for k, v in data["timePoints"].items():
            betweenTimes.append(k)
        for t in data["timeDifference"]:
            z = min(betweenTimes, key=lambda x: abs(x - t))
            gpsDataLatest[t] = data["timePoints"][z]
            print("{} {} {} {} {}".format(datetime.datetime.strftime(t, "%Y:%m:%d %H:%M:%S.%f"), datetime.datetime.strftime(z, "%Y:%m:%d %H:%M:%S.%f"), data["timePoints"][z]["GPSLatitude"], data["timePoints"][z]["GPSLongitude"], data["timePoints"][z]["GPSAltitude"]))
        return gpsDataLatest

    """
       getGpsData function
       This function is used to get all gps time in xml
    """ 

    def getGpsData(self, gpsData, startTime, endTime, frameRate, configData):
        t_start = datetime.datetime.strptime(startTime, "%Y:%m:%d %H:%M:%S.%f")
        if endTime is not None:
            t_end = datetime.datetime.strptime(endTime, "%Y:%m:%d %H:%M:%S.%f")
        else:
            t_end = None
        timeDifference = self.getGpsDataTimeDifference(t_start, t_end, frameRate, len(gpsData))
        if t_end is None:
            if len(timeDifference) > 0:
                t_end = timeDifference[-1]
            else:
                t_end = None
        timePoints = self.getGpsDataTimePoints(gpsData, t_start, t_end, frameRate, configData)
        return timePoints

    """
       getGpsDataTimeDifference function
       This function is used to get all times seperated at a constant step space.
    """ 

    def getGpsDataTimeDifference(self, startTime, endTime, frameRate, frlen):
        t_start = startTime
        if endTime is not None:
            diff = (100.0/float(frameRate))/100.0
        else:
            diff = 0.05
        times = []
        t = t_start
        times.append(t)
        for i in range(0, frameRate-1):
            t = t+datetime.timedelta(0, diff)
            times.append(t)
        return times


    """
       getGpsDataTimePoints function
       This function is used to get all the gps points with a calculated timestamp in between a start time and end time
    """

    def getGpsDataTimePoints(self, gpsData, startTime, endTime, frameRate, configData):
        print("{} -- {}".format(startTime, endTime))
        frlen = len(gpsData)
        data = {}
        t_start = startTime
        t = t_start
        i = 0 
        data[t] = gpsData[i]
        if endTime is None:
            return data
        t_end = endTime
        diff = (t_end - t_start)/float(frlen)
        print("diff: ", diff)
        while i < frlen-1:
            t = t+diff
            #print("{} {}".format(t, diff))
            data[t] = gpsData[i]
            #print("{} {} {}".format(t, gpsData[i]["GPSLatitude"], gpsData[i]["GPSLongitude"]))
            i = i+1
        for k, v in data.items():
            print("#{} {} {}".format(k, v["GPSLatitude"], v["GPSLongitude"]))
            self.__allGPSPoints.append({
                "GPSDateTime": k,
                "GPSLatitude": v["GPSLatitude"],
                "GPSLongitude": v["GPSLongitude"],
                "GPSAltitude": v["GPSAltitude"] 
            })
        print("Count: {} {}".format(len(data), len(gpsData)))
        return data

    """
       __injectMetadata function
       This function is used to inject collected metadata inside of all the images available.
    """

    def __injectMetadata(self, metaData, images, imageFolder):

        gpsMetaData = metaData["gps"]
        jsonMetaData = metaData["json"]

        __config = self.getConfig()

        for img in images:
            logging.info("# image: {}, GPSDateTime: {}, GPSLatitude: {}, GPSLongitude: {}, GPSAltitude: {}".format(img["image"], img["GPSDateTime"], img["GPSLatitude"], img["GPSLongitude"], img["GPSAltitude"]))
            tt = img["GPSDateTime"].split(".")
            ttz = img["GPSDateTime"].split(" ")
            alt = img["GPSAltitude"].split(" ")[0]
            latRef = self.latLngToDirection(img["GPSLatitude"])
            lngRef = self.latLngToDirection(img["GPSLongitude"])
            altRef = 0 if float(alt) > 0.0 else -1
            cmdMetaData = [
                '-DateTimeOriginal="{0}Z"'.format(self.removeEntities(tt[0])),
                '-SubSecTimeOriginal="{0}"'.format(self.removeEntities(tt[1])),
                '-SubSecDateTimeOriginal="{0}Z"'.format(self.removeEntities(".".join(tt))),
                '-IFD0:Model="{}"'.format(self.removeEntities(jsonMetaData["DeviceName"])),
            ]
            if __config["jsonData"]["ProjectionType"] == "equirectangular":
                cmdMetaData.append('-XMP-GPano:StitchingSoftware="{}"'.format(self.removeEntities(jsonMetaData["StitchingSoftware"])))
                cmdMetaData.append('-XMP-GPano:SourcePhotosCount="{}"'.format(2))
                cmdMetaData.append('-XMP-GPano:UsePanoramaViewer="{}"'.format("true"))
                cmdMetaData.append('-XMP-GPano:ProjectionType="{}"'.format(self.removeEntities(jsonMetaData["ProjectionType"])))
                cmdMetaData.append('-XMP-GPano:CroppedAreaImageHeightPixels="{}"'.format(jsonMetaData["SourceImageHeight"]))
                cmdMetaData.append('-XMP-GPano:CroppedAreaImageWidthPixels="{}"'.format(jsonMetaData["SourceImageWidth"]))
                cmdMetaData.append('-XMP-GPano:FullPanoHeightPixels="{}"'.format(jsonMetaData["SourceImageHeight"]))
                cmdMetaData.append('-XMP-GPano:FullPanoWidthPixels="{}"'.format(jsonMetaData["SourceImageWidth"]))
                cmdMetaData.append('-XMP-GPano:CroppedAreaLeftPixels="{}"'.format(0))
                cmdMetaData.append('-XMP-GPano:CroppedAreaTopPixels="{}"'.format(0))
            cmdMetaData.append('-overwrite_original')
            cmdMetaData.append(imageFolder+os.sep+"{}".format(img["image"]))
            output = self._exiftool(cmdMetaData)
            if output.returncode != 0:
                logging.error(output)
            else:
                logging.info(output)
            cmdstr = {
                "-GPSLatitude=": img["GPSLatitude"],
                "-GPSLatitudeRef=": latRef,
                "-GPSLongitude=": img["GPSLongitude"],
                "-GPSLongitudeRef=": lngRef,
                "-GPSAltitude=": img["GPSAltitude"],
                "-GPSAltitudeRef=": altRef,
                "-GPSDateStamp=": self.removeEntities(tt[0]),
                "-GPSTimeStamp=": self.removeEntities(ttz[1]),
            }
            cmdMetaDataLatLng = []
            for k, v in cmdstr.items():
                if type(v) is str:
                    cmdMetaDataLatLng.append(k+"\""+v+"\"")
                else:
                    cmdMetaDataLatLng.append(k+str(v))

            cmdMetaDataLatLng.append('-overwrite_original')
            cmdMetaDataLatLng.append(imageFolder+os.sep+"{}".format(img["image"]))
            output = self._exiftool(cmdMetaDataLatLng, 1)
            if output.returncode != 0:
                logging.error(output)
            else:
                logging.info(output)
        
        self.__createGeotagGPX(__config, images, imageFolder + os.sep + __config["imageFolder"] + "_photos")

        self.__createGPXAllPoints(__config, self.__allGPSPoints, imageFolder + os.sep + __config["imageFolder"] + "_video")

        self.__cammCsv( images, imageFolder )

    def __createGeotagGPX(self, __config, images, name):
        gpx = gpxpy.gpx.GPX()

        # Create first track in our GPX:
        gpx_track = gpxpy.gpx.GPXTrack()
        gpx.tracks.append(gpx_track)

        # Create first segment in our GPX track:
        gpx_segment = gpxpy.gpx.GPXTrackSegment()
        gpx_track.segments.append(gpx_segment)

        for point in images:
            a = self.latLngToDecimal(point["GPSLatitude"])
            b = self.latLngToDecimal(point["GPSLongitude"])
            alt = point["GPSAltitude"].split(" ")[0]
            t = datetime.datetime.strptime(point["GPSDateTime"], "%Y:%m:%d %H:%M:%S.%f")
            gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(latitude=a, longitude=b, time=t, elevation=alt))

        gpxData = gpx.to_xml() 
        gpxFileName = name +'.gpx'
        with open(gpxFileName, 'w') as f:
            f.write(gpxData)
            f.close()
            cmd = ["-geotag", gpxFileName, "'-geotime<${datetimeoriginal}'", '-overwrite_original', __config["imageFolderPath"]]
            output = self._exiftool(cmd)
            if output.returncode != 0:
                logging.error(output)
            else:
                logging.info(output)

    def __createGPXAllPoints(self, __config, __allGPSPoints, name):
        gpx = gpxpy.gpx.GPX()

        # Create first track in our GPX:
        gpx_track = gpxpy.gpx.GPXTrack()
        gpx.tracks.append(gpx_track)

        # Create first segment in our GPX track:
        gpx_segment = gpxpy.gpx.GPXTrackSegment()
        gpx_track.segments.append(gpx_segment)

        for point in __allGPSPoints:
            a = self.latLngToDecimal(point["GPSLatitude"])
            b = self.latLngToDecimal(point["GPSLongitude"])
            alt = point["GPSAltitude"].split(" ")[0]
            t = point["GPSDateTime"]
            gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(latitude=a, longitude=b, time=t, elevation=alt))

        gpxData = gpx.to_xml() 
        gpxFileName = name +'.gpx'
        with open(gpxFileName, 'w') as f:
            f.write(gpxData)
            f.close()

    def __cammCsv(self, data, imageFolder):
        with open(imageFolder+os.sep+'camm.csv', 'w', newline='') as csvfile:
            fieldnames = [
                'file_name', 
                'time_gps_epoch', 
                'gps_fix_type', 
                'latitude', 
                'longitude', 
                'altitude', 
                'horizontal_accuracy', 
                'vertical_accuracy', 
                'velocity_east',
                'velocity_north',
                'velocity_up',
                'speed_accuracy'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for row in data:
                writer.writerow({
                    'file_name': '',
                    'time_gps_epoch': '',
                    'gps_fix_type': '3D', 
                    'latitude': row["GPSLatitude"], 
                    'longitude': row["GPSLongitude"], 
                    'altitude': row["GPSAltitude"], 
                    'horizontal_accuracy': '1', 
                    'vertical_accuracy': '1', 
                    'velocity_east': '', 
                    'velocity_north': '', 
                    'velocity_up': '', 
                    'speed_accuracy': '0', 
                })


    """
       __validate function
       This function is used to validate command-line arguments.
    """

    def __validate(self, args):
        check = self._checkFileExists(args.input)
        if check == False:
            exit("{} does not exists. Please provide a valid video file.".format(args.input))
        if (args.frame_rate is not None):
            frameRate = int(args.frame_rate)
            fropts = [1,2,5]
            if frameRate not in fropts:
                exit("Frame rate {} is not available. Only 1, 2, 5 options are available.".format(frameRate))

        if (args.time_warp is not None):
            timeWarp = str(args.time_warp)
            twopts = ["2x", "5x", "10x", "15x", "30x"]
            if timeWarp not in twopts:
                exit("Timewarp mode {} not available. Only 2x, 5x, 10x, 15x, 30x options are available.".format(timeWarp))

        if (args.quality is not None):
            quality = int(args.quality)
            qopts = [1,2,3,4,5]
            if quality not in qopts:
                exit("Extracted quality {} is not available. Only 1, 2, 3, 4, 5 options are available.".format(quality))

        if (args.debug is not None):
            debug = True
        else:
            print("debug value is not provided, so by default debugging is off.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str, help="Input a valid video file.")
    parser.add_argument("-r", "--frame-rate", type=int, help="Sets the frame rate (frames per second) for extraction, default: 5.", default=5)
    parser.add_argument("-t", "--time-warp", type=str, help="Set time warp mode for gopro. available values are 2x, 5x, 10x, 15x, 30x")
    parser.add_argument("-q", "--quality", type=int, help="Sets the extracted quality between 2-6. 1 being the highest quality (but slower processing), default: 1. This is value used for ffmpeg -q:v flag. ", default=1)
    parser.add_argument("-d", "--debug", action='store_true', help="Enable debug mode, default: off.")
    args = parser.parse_args()
    dateTimeCurrent = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    logFolder = os.getcwd() + os.sep + "logs"
    if not os.path.exists(logFolder):
        os.makedirs(logFolder, exist_ok=True)
    if args.debug is True:
        logHandlers = [
            logging.FileHandler(logFolder+os.sep+'trekview-gopro-{}.log'.format(dateTimeCurrent)),
            logging.StreamHandler()
        ]
    else:
        logHandlers = [
            logging.FileHandler(logFolder+os.sep+'trekview-gopro-{}.log'.format(dateTimeCurrent))
        ]
    logging.basicConfig(
        level=logging.DEBUG,
        datefmt='%m/%d/%Y %I:%M:%S %p',
        format="%(asctime)s [%(levelname)s] [Line No.:%(lineno)d] %(message)s",
        handlers=logHandlers
    )
    
    goProMp4 = TrekViewGoProMp4(args, dateTimeCurrent)
    exit("Extraction complete, you can see your images now.")
