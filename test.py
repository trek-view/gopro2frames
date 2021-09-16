import subprocess, json, argparse, platform, copy, os, re, shutil, shlex, time, logging, datetime, fnmatch
from pathlib import Path
from os import walk
import gpxpy


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


class T(TrekviewCommand):

    def __init__(self, filename, framerate):
        self.__folderName = os.getcwd() + os.sep + "Img_Test"
        cmd = ["-ee", "-j", "-G3", "-s", "-api", "Largefilesupport=1", filename]
        output = self._exiftool(cmd)
        gpx = filename.split(".")[0]
        jsn = json.loads(output.stdout.decode('utf-8'))[0]
        gpsDataJSN = self.getJSON13(jsn)

        frs = [1, 5]

        for i in frs:
            fldr = self.__folderName+os.sep+"Img_"+str(i)

            if os.path.exists(fldr):
                shutil.rmtree(fldr)
            os.makedirs(fldr, exist_ok=True) 

            folder_1 = fldr+os.sep+"01" 
            os.makedirs(folder_1, exist_ok=True) 

            cmd = ["ffmpeg", "-i", filename, "-r", str(i), folder_1+os.sep+"img%d.jpg"]
            output = subprocess.run(cmd, capture_output=True)

            folder_2 = fldr+os.sep+"02" 
            os.makedirs(folder_2, exist_ok=True) 

            cmd = ["ffmpeg", "-i", filename, "-r", str(i), folder_2+os.sep+"img%d.jpg"]
            output = subprocess.run(cmd, capture_output=True)

            folder_3 = fldr+os.sep+"03" 
            os.makedirs(folder_3, exist_ok=True) 

            cmd = ["ffmpeg", "-i", filename, "-r", str(i), folder_3+os.sep+"img%d.jpg"]
            output = subprocess.run(cmd, capture_output=True)


            gpx_1 = fldr+os.sep+"01.gpx"

            gpsData = self.createGpxFile1(copy.deepcopy(gpsDataJSN), i, folder_1)
            with open(gpx_1, 'w') as f:
                f.write(gpsData)
                f.close()
                print(gpx_1)
                print(folder_1)
                cmd = ["-geotag", gpx_1, "'-geotime<${datetimeoriginal}-00:00'", "-v2", '-overwrite_original', folder_1]
                output = self._exiftool(cmd)
                print(output)

            gpx_2 = fldr+os.sep+"02.gpx" 

            gpsData = self.createGpxFile2(copy.deepcopy(gpsDataJSN), i, folder_2)
            with open(gpx_2, 'w') as f:
                f.write(gpsData)
                f.close()
                print(gpx_2)
                print(folder_2)
                cmd = ["-geotag", gpx_2, "'-geotime<${datetimeoriginal}-00:00'", "-v2", '-overwrite_original', folder_2]
                output = self._exiftool(cmd)
                print(output)

            gpx_3 = fldr+os.sep+"03.gpx"

            gpsData = self.createGpxFile3(copy.deepcopy(gpsDataJSN), i, folder_3)
            with open(gpx_3, 'w') as f:
                f.write(gpsData)
                f.close()
                print(gpx_3)
                print(folder_3)
                cmd = ["-geotag", gpx_3, "'-geotime<${datetimeoriginal}-00:00'", "-v2", '-overwrite_original', folder_3]
                output = self._exiftool(cmd)
                print(output)

            print(fldr, folder_1, folder_2, folder_3, gpx_1, gpx_2, gpx_3)
        exit()

    def createGpxFile1(self, gpsData, frameRate, folder):
        gpx = gpxpy.gpx.GPX()

        # Create first track in our GPX:
        gpx_track = gpxpy.gpx.GPXTrack()
        gpx.tracks.append(gpx_track)

        # Create first segment in our GPX track:
        gpx_segment = gpxpy.gpx.GPXTrackSegment()
        gpx_track.segments.append(gpx_segment)

        frameRateSeconds = float(1/float(frameRate))
        deltaSeconds = 0.0
        flen = len(fnmatch.filter(os.listdir(folder), '*.jpg'))
        j = 0
        k = 0
        t = datetime.datetime.strptime(gpsData[0]["GPSDateTime"], "%Y:%m:%d %H:%M:%S.%f")
        # Create points:
        for i in range(0, flen-1):
            if j == 0:
                deg, minutes, seconds, direction = re.split('[deg\'"]+', gpsData[k]["GPSLatitude"])
                gpsData[k]["GPSLatitude"] = (float(deg) + float(minutes)/60 + float(seconds)/(60*60)) * (-1 if direction in ['W', 'S'] else 1)
                deg, minutes, seconds, direction = re.split('[deg\'"]+', gpsData[k]["GPSLongitude"])
                gpsData[k]["GPSLongitude"] = (float(deg) + float(minutes)/60 + float(seconds)/(60*60)) * (-1 if direction in ['W', 'S'] else 1)
                gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(latitude=gpsData[k]["GPSLatitude"], longitude=gpsData[k]["GPSLongitude"], time=t))
                print(j, gpsData[k]["GPSLatitude"], gpsData[k]["GPSLongitude"], t, frameRate)
                k = k+1
            dateTimeValue = datetime.datetime.strftime(t, "%Y:%m:%d %H:%M:%S.%f").split('.')
            print(dateTimeValue, i, j)
            if len(dateTimeValue) > 1:
                DateTimeOriginal = dateTimeValue[0]+"Z"
                SubSecTimeOriginal = dateTimeValue[1]
                SubSecDateTimeOriginal = dateTimeValue[0]+"."+dateTimeValue[1]+"Z"
                cmd = ["-ee", '-DateTimeOriginal="'+DateTimeOriginal+'"', '-SubSecTimeOriginal="'+SubSecTimeOriginal+'"', '-SubSecDateTimeOriginal="'+SubSecDateTimeOriginal+'"', '-overwrite_original', folder+os.sep+"img"+str(i+1)+".jpg"]
                output = self._exiftool(cmd)
            t = t+datetime.timedelta(0, frameRateSeconds)
            i = i+1
            j = j+1
            if j == frameRate:
                j = 0

        return gpx.to_xml()

    def createGpxFile2(self, gpsData, frameRate, folder):
        gpx = gpxpy.gpx.GPX()

        # Create first track in our GPX:
        gpx_track = gpxpy.gpx.GPXTrack()
        gpx.tracks.append(gpx_track)

        # Create first segment in our GPX track:
        gpx_segment = gpxpy.gpx.GPXTrackSegment()
        gpx_track.segments.append(gpx_segment)

        frameRateSeconds = float(1/float(frameRate))
        deltaSeconds = 0.0
        flen = len(fnmatch.filter(os.listdir(folder), '*.jpg'))
        j = 0
        k = 0
        i = 1
        t = datetime.datetime.strptime(gpsData[0]["GPSDateTime"], "%Y:%m:%d %H:%M:%S.%f")
        # Create points:
        for gps in gpsData:
            deg, minutes, seconds, direction = re.split('[deg\'"]+', gps["GPSLatitude"])
            gps["GPSLatitude"] = (float(deg) + float(minutes)/60 + float(seconds)/(60*60)) * (-1 if direction in ['W', 'S'] else 1)
            deg, minutes, seconds, direction = re.split('[deg\'"]+', gps["GPSLongitude"])
            gps["GPSLongitude"] = (float(deg) + float(minutes)/60 + float(seconds)/(60*60)) * (-1 if direction in ['W', 'S'] else 1)
            gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(latitude=gps["GPSLatitude"], longitude=gps["GPSLongitude"], time=t))
            t = t+datetime.timedelta(0, frameRateSeconds)

        t = datetime.datetime.strptime(gpsData[0]["GPSDateTime"], "%Y:%m:%d %H:%M:%S.%f")
        # Inject date time:
        for i in range(0, flen-1):
            if j == 0:
                dateTimeValue = gpsData[k]["GPSDateTime"].split('.')
            else:
                dateTimeValue = datetime.datetime.strftime(t, "%Y:%m:%d %H:%M:%S.%f").split('.')
            if len(dateTimeValue) > 1:
                DateTimeOriginal = dateTimeValue[0]+"Z"
                SubSecTimeOriginal = dateTimeValue[1]
                SubSecDateTimeOriginal = dateTimeValue[0]+"."+dateTimeValue[1]+"Z"
                cmd = ["-ee", '-DateTimeOriginal="'+DateTimeOriginal+'"', '-SubSecTimeOriginal="'+SubSecTimeOriginal+'"', '-SubSecDateTimeOriginal="'+SubSecDateTimeOriginal+'"', '-overwrite_original', folder+os.sep+"img"+str(i+1)+".jpg"]
                output = self._exiftool(cmd)
            i = i+1
            t = t+datetime.timedelta(0, frameRateSeconds)
            j = j+1
            if j == frameRate:
                j = 0
                k = k+1
        return gpx.to_xml()

    def createGpxFile3(self, gpsData, frameRate, folder):
        gpx = gpxpy.gpx.GPX()

        # Create first track in our GPX:
        gpx_track = gpxpy.gpx.GPXTrack()
        gpx.tracks.append(gpx_track)

        # Create first segment in our GPX track:
        gpx_segment = gpxpy.gpx.GPXTrackSegment()
        gpx_track.segments.append(gpx_segment)

        frameRateSeconds = float(1/float(frameRate))
        deltaSeconds = 0.0
        flen = len(fnmatch.filter(os.listdir(folder), '*.jpg'))
        j = 0
        k = 0
        t = datetime.datetime.strptime(gpsData[0]["GPSDateTime"], "%Y:%m:%d %H:%M:%S.%f")
        # Create points:
        for i in range(0, flen-1):
            if j == 0:
                deg, minutes, seconds, direction = re.split('[deg\'"]+', gpsData[k]["GPSLatitude"])
                gpsData[k]["GPSLatitude"] = (float(deg) + float(minutes)/60 + float(seconds)/(60*60)) * (-1 if direction in ['W', 'S'] else 1)
                deg, minutes, seconds, direction = re.split('[deg\'"]+', gpsData[k]["GPSLongitude"])
                gpsData[k]["GPSLongitude"] = (float(deg) + float(minutes)/60 + float(seconds)/(60*60)) * (-1 if direction in ['W', 'S'] else 1)
                gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(latitude=gpsData[k]["GPSLatitude"], longitude=gpsData[k]["GPSLongitude"], time=t))
                print(j, gpsData[k]["GPSLatitude"], gpsData[k]["GPSLongitude"], t, frameRate)
                k = k+1
            dateTimeValue = datetime.datetime.strftime(t, "%Y:%m:%d %H:%M:%S.%f").split('.')
            print(dateTimeValue, i, j)
            if len(dateTimeValue) > 1:
                DateTimeOriginal = dateTimeValue[0]+"Z"
                SubSecTimeOriginal = dateTimeValue[1]
                SubSecDateTimeOriginal = dateTimeValue[0]+"."+dateTimeValue[1]+"Z"
                cmd = ["-ee", '-DateTimeOriginal="'+DateTimeOriginal+'"', '-SubSecTimeOriginal="'+SubSecTimeOriginal+'"', '-SubSecDateTimeOriginal="'+SubSecDateTimeOriginal+'"', '-overwrite_original', folder+os.sep+"img"+str(i+1)+".jpg"]
                output = self._exiftool(cmd)
            t = t+datetime.timedelta(0, frameRateSeconds)
            i = i+1
            j = j+1
            if j == frameRate:
                j = 0

        return gpx.to_xml()

    def getJSON13(self, jsonData):
        data = jsonData
        _jDTO = {}
        ret = []
        for k, v in data.items():
            key = k.split(":")
            if len(key) <= 1:
                continue
            else:
                if key[1] in ["GPSDateTime", "GPSLatitude", "GPSLongitude", "GPSAltitude"]:
                    if key[0] not in _jDTO:
                        _jDTO[key[0]] = {}
                    if v:
                        _jDTO[key[0]][key[1]] = v
        for k, v in _jDTO.items():
            ret.append(v)
        return ret


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", type=str, help="Please input a valid video file.")
    parser.add_argument("-f", "--frame-rate", type=str, help="Frame rate for ffmpeg command.")
    args = parser.parse_args()
    if (args.input is not None):
        ffmpegFrameRate = 5
        if args.frame_rate != None:
            try:
                ffmpegFrameRate = int(args.frame_rate)
            except:
                exit("Please enter a valid integer for frame rate.")
            ffmpegFrameRate = str(ffmpegFrameRate)
        t = T(args.input, ffmpegFrameRate)
