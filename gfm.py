import subprocess, argparse, platform, logging, datetime, fnmatch, shutil, shlex, html, copy, time, json, os, re
from pathlib import Path
from lxml import etree
from os import walk
import itertools
import gpxpy

def loading():
    return itertools.cycle(['-', '/', '|', '\\'])

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
        return (float(deg) + float(minutes)/60 + float(seconds)/(60*60)) * (-1 if direction in ['W', 'S'] else 1)

    def Log(self, msg, level="info"):
        if self.__config["debug"] == True:
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
                raise Exception(output.stderr.decode('utf-8',"ignore"))
        except Exception as e:
            if type(e) is TypeError:
                logging.error(str(e))
            else:
                logging.error(e.stderr.decode('utf-8',"ignore"))
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
        command.insert(len(command)-1, "-q:v")
        command.insert(len(command)-1, str(self.__config["quality"]))
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
                        self.__TimeWrap = True
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

    def __getGPSw(self, el, nsmap):
        __config = self.getConfig()
        Track = __config["jsonData"]["Track"]
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
        Track = __config["jsonData"]["Track"]
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

    def _breakIntoFrames(self, filename, frameRate, folderPath, imageFolder):
        if os.path.exists(folderPath):
            shutil.rmtree(folderPath)
        os.makedirs(folderPath, exist_ok=True) 
        __config = self.getConfig()
        cmd = ["-i", filename, "-r", str(frameRate), folderPath+os.sep+"{}_%06d.jpg".format(imageFolder)]
        output = self._ffmpeg(cmd, 1)
        if output.returncode != 0:
            return False 
        else:
            return True

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
    def __init__(self, args, dateTimeCurrent):

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
            self.Log("Unable to get metadata from video.", "critical")
            exit("Unable to get metadata from video.")

        FileType = ["MP4", "360"]
        if preProcessDataJSON["FileType"].strip() not in FileType:
            self.Log("The following filetype {} is not supported. Please upload only .mp4 or .360 videos.".format(preProcessDataJSON["FileType"]), "critical")
            exit("The following filetype {} is not supported. Please upload only .mp4 or .360 videos.".format(preProcessDataJSON["FileType"]))
        if preProcessDataJSON["FileType"].strip() == "360":
            if preProcessDataJSON["CompressorName"] == "H.265":
                self.Log("This does not appear to be a GoPro .360 file. Please use the .360 video created from your GoPro camera only.", "critical")
                exit("This does not appear to be a GoPro .360 file. Please use the .360 video created from your GoPro camera only.")
        
        fileStat = os.stat(filename)
        if fileStat.st_size > 1000000000:
            self.Log("The following file {} is too large. The maximum size for a single video is 5GB".format(filename), "critical")
            exit("The following file {} is too large. The maximum size for a single video is 5GB".format(filename))

        __configData["jsonData"] = preProcessDataJSON
        __configData["imageFolder"] = imageFolder
        __configData["imageFolderPath"] = imageFolderPath
        self.setConfig(__configData)

        framesBroken = self._breakIntoFrames(filename, frameRate, imageFolderPath, imageFolder)
        if framesBroken == False:
            self.Log("Unable to extract frames from video.", "critical")
            exit("Unable to extract frames from video.")
        images = fnmatch.filter(os.listdir(imageFolderPath), '*.jpg')
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
        iCounter = 0
        for data in preProcessDataXMLGPS:
            print("****")
            bt1 = preProcessDataXMLGPS[i]["GPSDateTime"]
            if i < len(preProcessDataXMLGPS)-1:
                bt2 = preProcessDataXMLGPS[i+1]["GPSDateTime"]
            else:
                bt = datetime.datetime.strptime(data["GPSDateTime"], "%Y:%m:%d %H:%M:%S.%f")
                bt2 = datetime.datetime.strftime(bt + datetime.timedelta(0,1), "%Y:%m:%d %H:%M:%S.%f")
            betweenTimes = self._getTimesBetween(
                bt1, 
                bt2, 
                frameRate,
                len(data["GPSData"])
            )
            betweenTimes.insert(0, datetime.datetime.strptime(preProcessDataXMLGPS[i]["GPSDateTime"], "%Y:%m:%d %H:%M:%S.%f"))        

            gpsIncFr = round(len(data["GPSData"])/frameRate)
            gpsInc = 0
            print("****")
            for bt in betweenTimes:
                if gpsInc < len(data["GPSData"]):
                    lat = data["GPSData"][gpsInc]["GPSLatitude"]
                    lng = data["GPSData"][gpsInc]["GPSLongitude"]
                else:
                    lat = "N/A"
                    lng = "N/A"
                print(gpsInc, len(data["GPSData"]), datetime.datetime.strftime(bt, "%Y:%m:%d %H:%M:%S.%f"), gpsInc < len(data["GPSData"]), "\""+lat+"\",", "\""+lng+"\"")
                if gpsInc < len(data["GPSData"]):
                    gpsData.append({
                        "GPSDateTime": datetime.datetime.strftime(bt, "%Y:%m:%d %H:%M:%S.%f"),
                        "GPSLatitude": data["GPSData"][gpsInc]["GPSLatitude"],
                        "GPSLongitude": data["GPSData"][gpsInc]["GPSLongitude"],
                        "GPSAltitude": data["GPSData"][gpsInc]["GPSAltitude"],
                    })
                    iCounter = iCounter+1
                else:
                    self.Log("File deleted as no gps data available. "+imageFolderPath+os.sep+"{}".format(images[iCounter]), "error")
                    os.unlink(imageFolderPath+os.sep+"{}".format(images[iCounter]))
                gpsInc = gpsInc + gpsIncFr
            print("increment: {}, totalImagesCount: {}, timesInBetween: {}, totalGPSPoints: {}".format(gpsIncFr, imagesCount, len(betweenTimes), len(data["GPSData"])))

            i = i+1
        
        images = fnmatch.filter(os.listdir(imageFolderPath), '*.jpg')
        imagesCount = len(images)
        metaData = {
            "gps": gpsData,
            "json": preProcessDataJSON
        }
        self.__injectMetadat(metaData, images, imageFolderPath)
        
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

        __config = self.getConfig()
        i = 0
        for img in images:
            if i >= len(gpsMetaData):
                self.Log("File deleted as no gps data available. "+imageFolder+os.sep+"{}".format(images[i]), "error")
                os.unlink(imageFolder+os.sep+"{}".format(images[i]))
                continue
            tt = gpsMetaData[i]["GPSDateTime"].split(".")
            t = datetime.datetime.strptime(gpsMetaData[i]["GPSDateTime"], "%Y:%m:%d %H:%M:%S.%f")
            a = self.latLngToDecimal(gpsMetaData[i]["GPSLatitude"])
            b = self.latLngToDecimal(gpsMetaData[i]["GPSLongitude"])
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
            
            cmdMetaData.append(imageFolder+os.sep+"{}".format(str(img)))

            output = self._exiftool(cmdMetaData)
            if output.returncode != 0:
                self.Log(output, "error")
            else:
                self.Log(output, "info")
            i = i+1
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
            os.unlink(gpxFileName)


    def __validate(self, args):
        check = self._checkFileExists(args.input)
        if check == False:
            exit("{} does not exists. Please provide a valid video file.".format(args.input))
        if (args.frame_rate is not None):
            frameRate = int(args.frame_rate)
            fropts = [1,2,5]
            if frameRate not in fropts:
                exit("Frame rate {} is not available. Only 1, 2, 5 options are available.".format(frameRate))

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
    parser.add_argument("-f", "--frame-rate", type=int, help="Sets the frame rate (frames per second) for extraction, default: 5.", default=5)
    parser.add_argument("-q", "--quality", type=int, help="Sets the extracted quality between 2-6. 1 being the highest quality (but slower processing), default: 1. This is value used for ffmpeg -q:v flag. ", default=1)
    parser.add_argument("-d", "--debug", action='store_true', help="Enable debug mode, default: off.")
    args = parser.parse_args()
    dateTimeCurrent = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    logFolder = os.getcwd() + os.sep + "logs"
    if not os.path.exists(logFolder):
        os.makedirs(logFolder, exist_ok=True)
    logging.basicConfig(filename=logFolder+os.sep+'trekview-gopro-{}.self.log'.format(dateTimeCurrent), format='%(asctime)s %(levelname)s: LineNo:%(lineno)d %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.DEBUG)
    goProMp4 = TrekViewGoProMp4(args, dateTimeCurrent)
    exit("Extraction complete, you can see your images now.")
