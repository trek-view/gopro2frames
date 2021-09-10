import subprocess, json, argparse
from pathlib import Path

class TrekviewPreProcess():
    filename = "" # Variable to store `Video file` with complete path
    device = "" # Variable to store `Device Name` (in this case GoPro)
    exifPreProcessData = [] # Variable to store `Exiftool Data`

    """
        init function
        It checks if the video file is valid or not.
        If the video file is valid then it will execute exiftool to get the metadata
    """
    def __init__(self, filename):
        filecheck = self.checkFileExists(filename)
        if filecheck == True:
            self.filename = filename
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
            cmd = "exiftool -ee -j -DeviceName -ProjectionType -MetaFormat  -StitchingSoftware -VideoFrameRate '%s'" % self.filename
            output = subprocess.check_output(cmd, shell=True)
            self.exifPreProcessData = json.loads(output.decode('utf-8'))
            if len(self.exifPreProcessData) > 0:
                self.exifPreProcessData = self.exifPreProcessData[0]
            else:
                exit("Data not available")
        except:
            exit("Error occurred. Please try again or check if `ExifTool`is installed or not.")

    """
        getPreProcessData function
        It will return the data that is required for pre-process-1
        return (Object)
    """  
    def getPreProcessData(self):
        return self.exifPreProcessData

    """
        checkProjectionType function
        It will check if the ProjectionType is `equirectangular`
        return (True|False)
    """  
    def checkProjectionType(self):
        if 'ProjectionType' in self.exifPreProcessData:
            if self.exifPreProcessData['ProjectionType'] == 'equirectangular':
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
        if 'DeviceName' in self.exifPreProcessData:
            if self.exifPreProcessData['DeviceName'] in devices:
                self.device = self.exifPreProcessData['DeviceName']
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
        if 'MetaFormat' in self.exifPreProcessData:
            if self.exifPreProcessData['MetaFormat'] == "gpmd":
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
        if 'StitchingSoftware' in self.exifPreProcessData:
            if self.exifPreProcessData['StitchingSoftware'] in softwares:
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
        if 'VideoFrameRate' in self.exifPreProcessData:
            if self.exifPreProcessData['VideoFrameRate'] > 5:
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
            
        if metaformat is True and (self.device == "GoPro Max"):
            errors['non_critical']['metaFormatMax']['errorStatus'] = True
        else:
            errors['non_critical']['metaFormatMax']['errorStatus'] = False
            errors['nonCriticalErrors'] = True

        if (errors['criticalErrors'] == True) or (errors['nonCriticalErrors'] == True):
            errors['hasErrors'] = True
            
        return errors

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", type=str, help="Please input a valid video file.")
    args = parser.parse_args()
    if (args.input is not None):
        preProcess = TrekviewPreProcess(args.input)
        preProcessValidated = preProcess.validatePreProcessData()
        print(preProcessValidated)
