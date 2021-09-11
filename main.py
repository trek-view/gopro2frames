import subprocess, json, argparse, platform, copy, os, re, shutil, shlex, time
from datetime import datetime, timedelta
from pathlib import Path
from lxml import etree
from os import walk

class TrekviewPreProcess():
    """
        init function
        It checks if the video file is valid or not.
        If the video file is valid then it will execute exiftool to get the metadata
    """
    def __init__(self, filename):
        if platform.system() == "Windows":
            self.__exiftool = "exiftool.exe"
        else:
            self.__exiftool = "exiftool"
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
        try:
            cmd = [self.__exiftool, "-ee", "-j", "-DeviceName", "-ProjectionType", "-MetaFormat", "-StitchingSoftware", "-VideoFrameRate", self.__filename]
            output = subprocess.run(cmd, capture_output=True)
            if output.returncode == 0:
                self.__exifPreProcessData = json.loads(output.stdout.decode('utf-8',"ignore"))
                if len(self.__exifPreProcessData) > 0:
                    self.__exifPreProcessData = self.__exifPreProcessData[0]
                else:
                    exit("Data not available")
            else:
                raise Exception(output)
        except Exception as e:
            exit("Error: {}".format( e.stderr.decode('utf-8',"ignore")))
        except:
            exit("Error:Please try again or check if `ExifTool`is installed or not.")

    """
        getPreProcessData function
        It will return the data that is required for pre-process-1
        return (Object)
    """  
    def getPreProcessData(self):
        return copy.deepcopy(self.__exifPreProcessData)

    """
        checkProjectionType function
        It will check if the ProjectionType is `equirectangular`
        return (True|False)
    """  
    def checkProjectionType(self):
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
        else:
            errors['non_critical']['metaFormatMax']['errorStatus'] = False
            errors['nonCriticalErrors'] = True

        if (errors['criticalErrors'] == True) or (errors['nonCriticalErrors'] == True):
            errors['hasErrors'] = True
            
        return errors

class TrekviewProcessMp4():
    def __init__(self, filename):
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
        try:
            video_file = Path(filename)
            if video_file.is_file():
                return True
            else:
                return False
        except:
            return False

    def extractMetaData(self):
        xmlFile = os.getcwd() + os.sep + 'VIDEO_META.xml'
        try:
            cmd = [self.__exiftool, "-ee", "-G3", "-api", "LargeFileSupport=1", "-X", self.__filename]
            output = subprocess.run(cmd, capture_output=True)
            if output.returncode == 0:
                with open(xmlFile, "w") as f:
                    self.__xmlOutput = output.stdout
                    f.write(self.__xmlOutput.decode('utf-8'))  
            else:
                raise Exception(output)
        except Exception as e:
            exit("Error: {}".format( e.stderr.decode('utf-8',"ignore")))
        except:
            exit("Error occurred. Please try again or check if `ExifTool`is installed or not.")

    def breakIntoFrames(self):
        self.__folderName = os.getcwd() + os.sep + "Img"
        root = etree.fromstring(self.__xmlOutput)
        DTO = root.xpath('.//Track3:GPSDateTime', namespaces = {'Track3':'http://ns.exiftool.org/QuickTime/Track3/1.0/'})
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
                    self.injectDateTimeMetadata(self.__folderName+os.sep+img, root)

                try:
                    cmd = shlex.split(self.__exiftool+" '-DateTimeOriginal+<0:0:${filesequence;$_*=0.2}' "+self.__folderName)
                    output = subprocess.run(cmd, capture_output=True)
                    if output.returncode == 0:
                        print(output.stdout.decode('utf-8'))
                        for img in images:
                            try:
                                cmd = [self.__exiftool, "-ee", "-j", "-DateTimeOriginal", self.__folderName+os.sep+img]
                                output = subprocess.run(cmd, capture_output=True)
                                if output.returncode == 0:
                                    img_dateTimeOriginal= json.loads(output.stdout.decode('utf-8',"ignore"))
                                    if len(img_dateTimeOriginal) > 0:
                                        img_dateTimeOriginal = img_dateTimeOriginal[0]["DateTimeOriginal"]
                                        for _val in DTO:
                                            _match = False
                                            atd = time.strptime(_val.text, "%Y:%m:%d %H:%M:%S.%f")
                                            btd = time.strptime(img_dateTimeOriginal, "%Y:%m:%d %H:%M:%S")
                                            if (btd <= atd) == True:
                                                _match = True
                                                print(_val.text, img_dateTimeOriginal, btd <= atd)
                                                self.getGPSValues(_val, self.__folderName+os.sep+img)
                                                break
                                        if _match == False:
                                            self.getGPSValues(DTO[-1], self.__folderName+os.sep+img)
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

    def getSphericalMetaData(self, root):
        data = {}
        nsGSpherical = {"XMP-GSpherical":'http://ns.exiftool.org/XMP/XMP-GSpherical/1.0/'}
        nsTrack1 = {"Track1":'http://ns.exiftool.org/QuickTime/Track1/1.0/'}
        GSpherical = [
            {
                "video":"XMP-GSpherical:StitchingSoftware",
                "image":"XMP-GPano:StitchingSoftware",
                "value":""
            },
            {
                "video":"",
                "image":"XMP-GPano:SourcePhotosCount",
                "value":"2"
            },
            {
                "video":"",
                "image":"XMP-GPano:UsePanoramaViewer",
                "value":"true"
            },
            {
                "video":"XMP-GSpherical:ProjectionType",
                "image":"XMP-GPano:ProjectionType",
                "value":""
            },
        ]
        Track = [
            {
                "video":"Track1:SourceImageHeight",
                "image":"XMP-GPano:CroppedAreaImageHeightPixels",
                "value":""
            },
            {
                "video":"Track1:SourceImageWidth",
                "image":"XMP-GPano:CroppedAreaImageWidthPixels",
                "value":""
            },
            {
                "video":"Track1:SourceImageHeight",
                "image":"XMP-GPano:FullPanoHeightPixels",
                "value":""
            },
            {
                "video":"Track1:SourceImageWidth",
                "image":"XMP-GPano:FullPanoWidthPixels",
                "value":""
            },
            {
                "video":"",
                "image":"XMP-GPano:CroppedAreaLeftPixels",
                "value":"0"
            },
            {
                "video":"",
                "image":"XMP-GPano:CroppedAreaTopPixels",
                "value":"0"
            },
        ]

        for i in GSpherical:
            if i["video"] != "":
                try:
                    el = root.find('.//'+str(i["video"]), namespaces = nsGSpherical)
                    name = el.xpath('local-name()')
                    value = el.text
                    data[i["image"]] = value
                except:
                    """"""
            else:
                data[i["image"]] = i["value"]

        for i in Track:
            if i["video"] != "":
                try:
                    el = root.find('.//'+str(i["video"]), namespaces = nsTrack1)
                    name = el.xpath('local-name()')
                    value = el.text
                    data[i["image"]] = value
                except:
                    """"""
            else:
                data[i["image"]] = i["value"]
        return data

    def getAdditionalMetaData(self, root):
        data = {}
        ns = {"Track3":'http://ns.exiftool.org/QuickTime/Track3/1.0/'}
        metadata = [
            {
                "video":"Track3:DeviceName",
                "image":"IFD0:Model",
                "value":""
            },
        ]
        for i in metadata:
            if i["video"] != "":
                try:
                    el = root.find('.//'+str(i["video"]), namespaces = ns)
                    name = el.xpath('local-name()')
                    value = el.text
                    data[i["image"]] = value
                except:
                    """"""
        return data

    def getGPSValues(self, root, image):
        data = {}
        nsTrack2 = {"Track2":'http://ns.exiftool.org/QuickTime/Track2/1.0/'}
        nsTrack3 = {"Track3":'http://ns.exiftool.org/QuickTime/Track3/1.0/'}
        Track = "Track3"
        if Track == "Track3":
            ns = nsTrack3
        else:
            ns = nsTrack2
        metadata = [
            {
                "video":Track+":GPSDateTime",
                "image":["GPS:GPSDateStamp", "GPS:GPSTimeStamp"],
                "value":""
            },
            {
                "video":Track+":GPSLatitude",
                "image":["GPS:GPSLatitude", "GPS:GPSLatitudeRef"],
                "value":""
            },
            {
                "video":Track+":GPSLongitude",
                "image":["GPS:GPSLongitude", "GPS:GPSLongitudeRef"],
                "value":""
            },
            {
                "video":Track+":GPSAltitude",
                "image":["GPS:GPSAltitude", "GPS:GPSAltitudeRef"],
                "value":""
            },
        ]
        _check = 0
        _limit = 0
        while True:
            if root == None:
                break
            root = root.getnext()
            if root == None:
                break
            name = root.xpath('local-name()')
            if name == "GPSDateTime":
                break
            for i in metadata:
                if i["video"] != "":
                    try:
                        if i["video"] == "Track3:"+name:
                            value = root.text
                            value = value.split(" ")
                            ref = value.pop()
                            data[i["image"][0]] = " ".join(value)
                            if( i["image"][1] =="GPS:GPSAltitudeRef"):
                                data[i["image"][1]] = "Above Sea Level"
                            else:
                                data[i["image"][1]] = "\""+ref+"\""
                            _check = _check+1
                    except:
                        """"""
            _limit = _limit+1
            if _check > 8:
                break
            if _limit > 1000:
                break
        if len(data) > 1:
            cmd = [self.__exiftool] 
            for flag in [data]:
                for key, value in flag.items():
                    cmd.append("-"+key+"="+value)
            try:
                cmd.append(image)
                output = subprocess.run(cmd, capture_output=True)
                if output.returncode == 0:
                    print("Image: {} {}".format(image, output.stdout.decode('utf-8',"ignore")))
                    print("{}".format( output.stderr.decode('utf-8',"ignore")))
                else:
                    raise Exception(output)
            except Exception as e:
                exit("Error: {}".format( e.stderr.decode('utf-8',"ignore")))
            except:
                exit("Error occurred. Please try again or check if `ExifTool`is installed or not.")

        return True

    def getDateTimeFirstImageMetaData(self, root):
        data = {}
        ns = {"Track3":'http://ns.exiftool.org/QuickTime/Track3/1.0/'}
        el = root.find('.//Track3:GPSDateTime', namespaces = ns)
        dateTimeLocalName = el.xpath('local-name()')
        dateTimeValue = el.text.split('.')
        if len(dateTimeValue) > 1:
            DateTimeOriginal = dateTimeValue[0]+"Z"
            SubSecTimeOriginal = dateTimeValue[1]
            SubSecDateTimeOriginal = dateTimeValue[0]+"."+dateTimeValue[1]+"Z"
            data = {"DateTimeOriginal":DateTimeOriginal, "SubSecTimeOriginal":SubSecTimeOriginal, "SubSecDateTimeOriginal":SubSecDateTimeOriginal}
        return data
    
    def injectDateTimeMetadata(self, img, root):
        image1     = self.getDateTimeFirstImageMetaData(root)
        cmd = [self.__exiftool] 
        for flag in [image1]:
            for key, value in flag.items():
                cmd.append("-"+key+"="+value)
        try:
            cmd.append(img)
            output = subprocess.run(cmd, capture_output=True)
            if output.returncode == 0:
                print("Image: {} {}".format(img, output.stdout.decode('utf-8',"ignore")))
                print("{}".format( output.stderr.decode('utf-8',"ignore")))
            else:
                raise Exception(output)
        except Exception as e:
            exit("Error: {}".format( e.stderr.decode('utf-8',"ignore")))
        except:
            exit("Error occurred. Please try again or check if `ExifTool`is installed or not.")
    def injectMetadata(self, root):
        spherical  = self.getSphericalMetaData(root)
        additional = self.getAdditionalMetaData(root)
        data = [
            spherical,
            additional
        ]
        cmd = [self.__exiftool] 
        for flag in data:
            for key, value in flag.items():
                cmd.append("-"+key+"="+value)
        try:
            cmd.append(self.__folderName)
            output = subprocess.run(cmd, capture_output=True)
            if output.returncode == 0:
                print("Image: {}".format(output.stdout.decode('utf-8',"ignore")))
                print("{}".format( output.stderr.decode('utf-8',"ignore")))
            else:
                raise Exception(output)
        except Exception as e:
            exit("Error: {}".format( e.stderr.decode('utf-8',"ignore")))
        except:
            exit("Error occurred. Please try again or check if `ExifTool`is installed or not.")

def printErrors(errors):
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
        preProcess = TrekviewPreProcess(args.input)
        preProcessValidated = preProcess.validatePreProcessData()
        printErrors(preProcessValidated)
        mp4Video = TrekviewProcessMp4(args.input)
        print(preProcess.getPreProcessData())
        printErrors(preProcessValidated)
        print("Done! You can now see your images in Img filder.")
        
