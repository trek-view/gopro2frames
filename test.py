import subprocess, json, argparse, platform, copy, os, re, shutil, shlex, time, logging, datetime
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

    def __init__(self, filename):
        cmd = ["-ee", "-j", "-G3", "-s", "-api", "Largefilesupport=1", filename]
        output = self._exiftool(cmd)
        gpx = filename.split(".")[0]
        jsn = json.loads(output.stdout.decode('utf-8'))[0]

        cmd = ["ffmpeg", "-i", filename, "-r", "1", "./Img/img%d.jpg"]
        output = subprocess.run(cmd, capture_output=True)
        if output.returncode != 0: 
            exit("Error in ffmpeg")
        else:
            gpsData = self.getJSON13(jsn)
            gpsData = self.createGpxFile(gpsData, 1)
            with open(gpx+'.gpx', 'w') as f:
                f.write(gpsData)
                f.close()
                cmd = ["-geotag", gpx+'.gpx', "'-geotime<${datetimeoriginal}-00:00'", "-v2", "./Img"]
                output = self._exiftool(cmd)
                print(output)




    def createGpxFile(self, gpsData, frameRate):
        gpx = gpxpy.gpx.GPX()

        # Create first track in our GPX:
        gpx_track = gpxpy.gpx.GPXTrack()
        gpx.tracks.append(gpx_track)

        # Create first segment in our GPX track:
        gpx_segment = gpxpy.gpx.GPXTrackSegment()
        gpx_track.segments.append(gpx_segment)

        frameRateSeconds = float(1/float(frameRate))
        deltaSeconds = 0.0
        i = 1
        # Create points:
        for gps in gpsData:
            t = datetime.datetime.strptime(gps["GPSDateTime"], "%Y:%m:%d %H:%M:%S.%f")
            deg, minutes, seconds, direction = re.split('[deg\'"]+', gps["GPSLatitude"])
            gps["GPSLatitude"] = (float(deg) + float(minutes)/60 + float(seconds)/(60*60)) * (-1 if direction in ['W', 'S'] else 1)
            deg, minutes, seconds, direction = re.split('[deg\'"]+', gps["GPSLongitude"])
            gps["GPSLongitude"] = (float(deg) + float(minutes)/60 + float(seconds)/(60*60)) * (-1 if direction in ['W', 'S'] else 1)
            gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(latitude=gps["GPSLatitude"], longitude=gps["GPSLongitude"], time=t))
            dateTimeValue = gps["GPSDateTime"].split('.')
            if len(dateTimeValue) > 1:
                DateTimeOriginal = dateTimeValue[0]+"Z"
                SubSecTimeOriginal = dateTimeValue[1]
                SubSecDateTimeOriginal = dateTimeValue[0]+"."+dateTimeValue[1]+"Z"
                cmd = ["-ee", '-DateTimeOriginal="'+DateTimeOriginal+'"', '-SubSecTimeOriginal="'+SubSecTimeOriginal+'"', '-SubSecDateTimeOriginal="'+SubSecDateTimeOriginal+'"', "Img/img"+str(i)+".jpg"]
                output = self._exiftool(cmd)
            #t = t+datetime.timedelta(0, frameRateSeconds)
            i = i+1

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
        ffmpegFrameRate = "5"
        if args.frame_rate != None:
            try:
                ffmpegFrameRate = int(args.frame_rate)
            except:
                exit("Please enter a valid integer for frame rate.")
            ffmpegFrameRate = str(ffmpegFrameRate)
        t = T(args.input)
