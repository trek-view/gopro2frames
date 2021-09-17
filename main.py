import subprocess, argparse, platform, logging, datetime, fnmatch, shutil, shlex, copy, time, json, os, re
from pathlib import Path
from lxml import etree
from os import walk
import gpxpy

def log(msg, level="info", cnf={}):
    if cnf["debug"] == True :
        print(msg)
    if level == "info":
        logging.info(msg)
    if level == "warning":
        logging.warning(msg)
    if level == "error":
        logging.error(msg)

class TrekviewCommand():

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
                raise Exception(output)
        except Exception as e:
            if type(e) is TypeError:
                logging.error(str(e))
            else:
                logging.error(e.stderr.decode('utf-8',"ignore"))
            ret = None
        except:
            exit("Error:Please try again.")
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
            exit("Error occured while executing exiftool.")
        return ret

    def _ffmpeg(self, command, sh=0):
        logging.info("Starting Ffmpeg")
        if platform.system() == "Windows":
            ffmpeg = "ffmpeg.exe"
        else:
            ffmpeg = "ffmpeg"
        command.insert(0, ffmpeg)
        ret = self.__subprocess(command, sh)
        if ret == None:
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
    def __init__(self):
        """"""
    def _preProcessExifToolExecute(self, filename):
        logging.info("Getting Pre Process Info")
        cmd = ["-ee", "-j", "-DeviceName", "-ProjectionType", "-MetaFormat", "-StitchingSoftware", "-VideoFrameRate", "-SourceImageHeight", "-SourceImageWidth", filename]
        output = self._exiftool(cmd)
        exifPreProcessData = json.loads(output.stdout.decode('utf-8',"ignore"))
        if len(exifPreProcessData) > 0:
            preProcessValidated = self.__validatePreProcessData(exifPreProcessData[0])
            exifPreProcessData[0]["Timewrap"] = self.__TimeWrap
            self.__printErrors(preProcessValidated)
            return exifPreProcessData[0]
        else:
            return None
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

class TrekviewProcessMp4(TrekviewCommand):
    def __init__(self):
        """"""

    def __getGPSw(self, el, nsmap):
        data = {"GPSDateTime": "", "GPSData":[]}
        if el == None:
            return None
        else:
            data["GPSDateTime"] = el.text
        print("#", el.text)
        for i in range(0, 500):
            el = el.getnext()
            if el == None:
                break
            if el.tag == "{"+nsmap["Track3"]+"}GPSDateTime":
                break
            if el.tag == "{"+nsmap["Track3"]+"}GPSLatitude":
                data["GPSData"].append({"GPSLatitude": el.text})
            if el.tag == "{"+nsmap["Track3"]+"}GPSLongitude":
                data["GPSData"].append({"GPSLongitude": el.text})
            if el.tag == "{"+nsmap["Track3"]+"}GPSAltitude":
                data["GPSData"].append({"GPSAltitude": el.text})
        return data

    def _processXMLGPS(self, filename):
        output = self._exiftool(["-ee", "-G3", "-api", "LargeFileSupport=1", "-X", filename])
        if output is None:
            exit("Unable to get metadata information")
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
                if el.tag == "{"+nsmap["Track3"]+"}GPSDateTime":
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

        self.__validate(args)

        imageFolder = os.getcwd() + os.sep + 'Img'
        filename = args.input
        frameRate = self._config["frameRate"]

        preProcessDataJSON = self._preProcessExifToolExecute(args.input)
        if preProcessDataJSON is None:
            exit("Unable to get metadata from video.")

        framesBroken = self._breakIntoFrames(filename, frameRate, imageFolder)
        if framesBroken == False:
            exit("Unable to extract frames from video.")
        images = fnmatch.filter(os.listdir(imageFolder), '*.jpg')
        imagesCount = len(images)
        preProcessDataXMLGPS = self._processXMLGPS(args.input)
        if len(preProcessDataXMLGPS) <= 0:
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
                gpsIncFr = int((frameRate-1)/2)
                gpsInc = 2-1
                for bt in betweenTimes:
                    log("{} {} {} {} {}".format("#", i, gpsInc, data["GPSDateTime"], len(data["GPSData"])), "error", self._config)
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
                gpsIncFr = int((frameRate-1)/2)
                gpsInc = 2-1
                j = 0
                for ei in range(len(gpsData), imagesCount):
                    if gpsInc < len(data["GPSData"]):
                        gpsData.append({
                            "GPSDateTime": datetime.datetime.strftime(betweenTimes[j], "%Y:%m:%d %H:%M:%S.%f"),
                            "GPSLatitude": data["GPSData"][gpsInc]["GPSLatitude"],
                            "GPSLongitude": data["GPSData"][gpsInc]["GPSLongitude"],
                            "GPSAltitude": data["GPSData"][gpsInc]["GPSAltitude"],
                        })
                        j = j+1
                    else:
                        log("No gps data available for this image.", "error", self._config)
                    gpsInc = gpsInc + gpsIncFr
            i = i+1
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

            log("{} {} {} {} {}".format(gpsMetaData[i]["GPSDateTime"], gpsMetaData[i]["GPSLatitude"], a, gpsMetaData[i]["GPSLongitude"], b), "info", self._config)

            if i < len(gpsMetaData)-1:
                t1 = datetime.datetime.strptime(gpsMetaData[i+1]["GPSDateTime"], "%Y:%m:%d %H:%M:%S.%f")
                log("{} {} {}".format(t, t1, t1-t), "info", self._config)

            cmdMetaData = [
                '-DateTimeOriginal="{0}Z"'.format(tt[0]),
                '-SubSecTimeOriginal="{0}"'.format(tt[1]),
                '-SubSecDateTimeOriginal="{0}Z"'.format(".".join(tt)),
                '-IFD0:Model="{}"'.format(jsonMetaData["DeviceName"]),
                '-XMP-GPano:StitchingSoftware="{}"'.format(jsonMetaData["StitchingSoftware"]),
                '-XMP-GPano:SourcePhotosCount="{}"'.format(2),
                '-XMP-GPano:UsePanoramaViewer="{}"'.format("true"),
                '-XMP-GPano:ProjectionType="{}"'.format(jsonMetaData["ProjectionType"]),
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
                log(output, "error", self._config)
            else:
                log(output, "info", self._config)

        time.sleep(2)

        gpxData = gpx.to_xml() 
        gpxFileName = os.getcwd() + os.sep + 'VIDEO_META.gpx'
        with open(gpxFileName, 'w') as f:
            f.write(gpxData)
            f.close()
            cmd = ["-geotag", gpxFileName, "'-geotime<${datetimeoriginal}-00:00'", "-v2", '-overwrite_original', imageFolder]
            output = self._exiftool(cmd)
            if output.returncode != 0:
                log(output, "error", self._config)
            else:
                log(output, "info", self._config)


    def __validate(self, args):
        frameRate = 5
        debug = False
        quiet = True
        check = self._checkFileExists(args.input)
        if check == False:
            exit("{} does not exists.".format(args.input))

        if (args.frame_rate is not None):
            frameRate = int(args.frame_rate)
            if frameRate > 10:
                exit("Please use framerate value less than 10.")
        else:
            print("frameRate is not provided, so using default framerate of 5 frames per second")

        if (args.debug is not None):
            debug = True
        else:
            print("debug value is not provided, so by default debugging is off.")

        if (args.quiet is not None):
            quiet = False
        else:
            print("verbosity is not enabled, so by default is quiet.")

        self._config = {
            "frameRate": frameRate,
            "debug": debug,
            "quiet": quiet,
        }

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", type=str, help="Please input a valid video file.")
    parser.add_argument("-f", "--frame-rate", type=str, help="Frame rate for ffmpeg command.")
    parser.add_argument("-d", "--debug", type=str, help="Print out debuggin info.")
    parser.add_argument("-q", "--quiet", type=str, help="Use this option to enable verbosity or not. -q 0 is quiet and -q 1 is verbose. Default is 0.")
    args = parser.parse_args()
    if (args.input is not None):
        logging.basicConfig(filename='trekview-gopro.log', format='%(asctime)s %(levelname)s: LineNo:%(lineno)d %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.DEBUG)
        goProMp4 = TrekViewGoProMp4(args)
    else:
        exit("Please use a valid video file.")
