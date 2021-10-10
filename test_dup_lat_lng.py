import subprocess, itertools, argparse, platform, logging, datetime, fnmatch, shutil, pandas as pd, shlex, html, copy, time, json, math, csv, os, re
from geographiclib.geodesic import Geodesic
from decimal import Decimal, getcontext
from haversine import haversine, Unit
from pathlib import Path
from lxml import etree as ET
from os import walk
import itertools
import gpxpy

class TrekviewHelpers():
    def __init__(self, config):
        getcontext().prec = 6
    def getListOfTuples(self, mylist, n):
        args = [iter(mylist)] * n
        return itertools.zip_longest(fillvalue=None, *args)

    def removeEntities(self, text):
        text = re.sub('"', '', html.unescape(text))
        text = re.sub("'", '', html.unescape(text))
        return html.escape(text)

    def latLngDecimalToDecimal(self, latLng):
        ll = latLng.split(" ")
        return float(ll[0]) * (-1 if ll[1].strip() in ['W', 'S'] else 1)

    def latLngToDecimal(self, latLng):
        deg, minutes, seconds, direction = re.split('[deg\'"]+', latLng)
        return (float(deg.strip()) + float(minutes.strip())/60 + float(seconds.strip())/(60*60)) * (-1 if direction.strip() in ['W', 'S'] else 1)

    def latLngToDirection(self, latLng):
        deg, minutes, seconds, direction = re.split('[deg\'"]+', latLng)
        return direction.strip()

    def getAltitudeFloat(self, altitude):
        alt = float(altitude.split(" ")[0])
        #print("\nalt: {} {} \n".format(alt, altitude.split(" ")[0]))
        return alt

    def calculateBearing(self, lat1, long1, lat2, long2):
        Long = (long2-long1)
        y = math.sin(Long) * math.cos(lat2)
        x = math.cos(lat1)*math.sin(lat2) - math.sin(lat1)*math.cos(lat2)*math.cos(Long)
        brng = math.degrees((math.atan2(y, x)))
        brng = (((brng + 360) % 360))
        return brng

    def calculateExtensions(self, gps, times, positions, etype=1, utype=1):
        if utype == 1:
            gps_speed_accuracy_meters = '0.1'
            gps_fix_type = gps["GPSMeasureMode"]
            gps_vertical_accuracy_meters = gps["GPSHPositioningError"]
            gps_horizontal_accuracy_meters = gps["GPSHPositioningError"]
        else:
            gps_speed_accuracy_meters = '0.1'
            gps_fix_type = '3-Dimensional Measurement'
            gps_vertical_accuracy_meters = '0.1'
            gps_horizontal_accuracy_meters = '0.1'
        
        if etype == 1:
            #Get Times from metadata
            start_time = times[0]
            end_time = times[1]
            gps_epoch_seconds = times[2]
            time_diff = (end_time - start_time).total_seconds()

            #Get Latitude, Longitude and Altitude
            start_latitude = positions[0][0]
            start_longitude = positions[0][1]
            start_altitude = positions[0][2]

            end_latitude = positions[1][0]
            end_longitude = positions[1][1]
            end_altitude = positions[1][2]

            #Find Haversine Distance
            distance = haversine((start_latitude, start_longitude), (end_latitude, end_longitude), Unit.METERS)

            #Find Bearing
            brng = Geodesic.WGS84.Inverse(start_latitude, start_longitude, end_latitude, end_longitude)
            azimuth1 = (brng['azi1'] + 360) % 360
            azimuth2 = (brng['azi2'] + 360) % 360

            compass_bearing = azimuth2

            #Create Metada Fields
            AC = Decimal(math.sin(math.radians(azimuth1))*distance)
            BC = Decimal(math.cos(math.radians(azimuth2))*distance)

            #print((start_latitude, start_longitude), (end_latitude, end_longitude))
            #print("AC: {}, BC: {}, azimuth1: {}, azimuth2: {}, \ntime: {}, distance: {} seconds: {}\n\n\n".format(AC, BC, azimuth1, azimuth2, Decimal(time_diff), distance, gps_epoch_seconds))

            gps_elevation_change_next_meters = end_altitude - start_altitude
            gps_velocity_east_next_meters_second = 0.0 if time_diff == 0.0 else AC/Decimal(time_diff)  
            gps_velocity_east_next_meters_second = 0.0 if gps_velocity_east_next_meters_second == 0.0 else gps_velocity_east_next_meters_second
            gps_velocity_north_next_meters_second = 0.0 if time_diff == 0.0 else BC/Decimal(time_diff)
            gps_velocity_north_next_meters_second = 0.0 if gps_velocity_north_next_meters_second == 0.0 else round(gps_velocity_north_next_meters_second)
            gps_velocity_up_next_meters_second = 0.0 if time_diff == 0.0 else gps_elevation_change_next_meters/time_diff
            gps_velocity_up_next_meters_second = 0.0 if gps_velocity_up_next_meters_second == 0.0 else round(gps_velocity_up_next_meters_second)
            gps_speed_next_meters_second = 0.0 if time_diff == 0.0 else distance/time_diff 
            gps_speed_next_meters_second = 0.0 if gps_speed_next_meters_second == 0.0 else round(gps_speed_next_meters_second)
            gps_heading_next_degrees = 0 if distance == 0.0 else compass_bearing
            gps_pitch_next_degrees = 0.0 if distance == 0.0 else (gps_elevation_change_next_meters / distance)%360
            gps_distance_next_meters = distance
            gps_speed_next_kmeters_second = gps_distance_next_meters/1000.0 #in kms
            gps_time_next_seconds = time_diff
        else:
            gps_epoch_seconds = times[2]
            gps_velocity_east_next_meters_second = 0.0
            gps_velocity_north_next_meters_second = 0.0
            gps_velocity_up_next_meters_second = 0.0
            gps_speed_next_meters_second = 0.0
            gps_speed_next_kmeters_second = 0.0
            gps_heading_next_degrees = 0.0
            gps_elevation_change_next_meters = 0.0
            gps_pitch_next_degrees = 0.0
            gps_distance_next_meters = 0.0
            gps_time_next_seconds = 0.0
        return {
            "gps_epoch_seconds": gps_epoch_seconds,
            "gps_fix_type": gps_fix_type,
            "gps_vertical_accuracy_meters": "{0:.3f}".format(Decimal(gps_vertical_accuracy_meters)),
            "gps_horizontal_accuracy_meters": "{0:.3f}".format(Decimal(gps_horizontal_accuracy_meters)),
            "gps_velocity_east_next_meters_second": "{0:.3f}".format(Decimal(gps_velocity_east_next_meters_second)),
            "gps_velocity_north_next_meters_second": "{0:.3f}".format(Decimal(gps_velocity_north_next_meters_second)),
            "gps_velocity_up_next_meters_second": "{0:.3f}".format(Decimal(gps_velocity_up_next_meters_second)),
            "gps_speed_accuracy_meters": "{0:.3f}".format(Decimal(gps_speed_accuracy_meters)),
            "gps_speed_next_meters_second": "{0:.3f}".format(Decimal(gps_speed_next_meters_second)),
            "gps_heading_next_degrees": "{0:.3f}".format(Decimal(gps_heading_next_degrees)),
            "gps_elevation_change_next_meters": "{0:.3f}".format(Decimal(gps_elevation_change_next_meters)),
            "gps_pitch_next_degrees": "{0:.3f}".format(Decimal(gps_pitch_next_degrees)),
            "gps_distance_next_meters": "{0:.3f}".format(Decimal(gps_distance_next_meters)),
            "gps_time_next_seconds": "{0:.3f}".format(Decimal(gps_time_next_seconds)),
            "gps_speed_next_kmeters_second": "{0:.3f}".format(Decimal(gps_speed_next_kmeters_second))
        }

    def __subprocess(self, command, sh=0, capture_output=True):
        ret = None
        try:
            cmd = command
            if sh == 0:
                cmd = shlex.split(" ".join(cmd))
            output = subprocess.run(cmd, capture_output=capture_output)
            logging.info(output)
            if output.returncode == 0:
                out = output.stdout.decode('utf-8',"ignore")
                logging.info(str(out))
                ret = {
                    "output": out,
                    "error": None
                }
            else:
                raise Exception(output.stderr.decode('utf-8',"ignore"))
        except Exception as e:
            logging.info(str(e))
            ret = {
                "output": None,
                "error": str(e)
            }
        except:
            exit("Error running subprocess. Please try again.")
        return ret

    def _exiftool(self, command, sh=0):
        if platform.system() == "Windows":
            exiftool = "exiftool.exe"
        else:
            exiftool = "exiftool"
        command.insert(0, "-config")
        command.insert(1, ".ExifTool_config")
        command.insert(0, exiftool)
        ret = self.__subprocess(command, sh)
        if ret["error"] is not None:
            logging.critical(ret["error"])
            exit("Error occured while executing exiftool.")
        return ret

    def setFFmpegPath(self, path):
        if path == "":
            if platform.system() == "Windows":
                ffmpeg = ".{}FFmpeg{}ffmpeg.exe".format(os.sep, os.sep)
            else:
                ffmpeg = ".{}FFmpeg{}ffmpeg".format(os.sep, os.sep)
        else:
            ffmpeg = path
        self.ffmpeg = ffmpeg.strip()
        print("ffmpeg path: {} is being used".format(self.ffmpeg))
    
    def _ffmpeg(self, command, sh=0):
        ffmpeg = self.ffmpeg
        command.insert(0, ffmpeg)
        ret = self.__subprocess(command, sh, False)
        
        """if ret["error"] is not None:
            logging.critical(ret["error"])
            exit("Error occured while executing ffmpeg, please see logs for more info.")"""
        return True

    def _checkFileExists(self, filename):
        try:
            return True if Path(filename).is_file() else False
        except:
            return False

class TrekViewGoProMp4(TrekviewHelpers):

    def __init__(self, args, dateTimeCurrent):

        self.__config = {
            "log_path": os.getcwd() + os.sep + "logs",
            "args": args,
            "date_time_current": dateTimeCurrent
        }

        self.__setLogging()
        self.__validateArguments()
        self.__config["imageFolder"] = os.path.basename(args.input).split(".")[0]
        self.__config["imageFolderPath"] = os.getcwd() + os.sep + self.__config["imageFolder"] + "_" + dateTimeCurrent
        self.__createDirectories()

        if self.__config["time_warp"] is None:
            ms = float(((100.0/float(self.__config["frame_rate"]))/100.0))
            videoData = self.__extractVideoInformationPre(args.input, "Track3")
        else:
            tw = self.__config["time_warp"]
            fr = self.__config["frame_rate"]
            tw = int(tw.replace('x', ''))
            if fr < 1:
                fr = 5
            tw = float(tw)/float(fr)
            ms = float(tw)
            videoData = self.__extractVideoInformationPre(args.input, "Track2")
            

    def __setLogging(self):
        args = self.__config["args"]
        logFolder = self.__config["log_path"]
        dateTimeCurrent = self.__config["date_time_current"]
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

    def __validateArguments(self):
        args = self.__config["args"]
        check = self._checkFileExists(args.input)
        if check == False:
            exit("{} does not exists. Please provide a valid video file.".format(args.input))
        if (args.frame_rate is not None):
            frameRate = int(args.frame_rate)
            fropts = [1,2,5]
            if frameRate not in fropts:
                exit("Frame rate {} is not available. Only 1, 2, 5 options are available.".format(frameRate))
            else:
                self.__config["frame_rate"] = frameRate
        else:
            self.__config["frame_rate"] = 5

        if (args.time_warp is not None):
            timeWarp = str(args.time_warp)
            twopts = ["2x", "5x", "10x", "15x", "30x"]
            if timeWarp not in twopts:
                exit("Timewarp mode {} not available. Only 2x, 5x, 10x, 15x, 30x options are available.".format(timeWarp))
            else:
                self.__config["time_warp"] = timeWarp
        else:
            self.__config["time_warp"] = None

        if (args.quality is not None):
            quality = int(args.quality)
            qopts = [1,2,3,4,5]
            if quality not in qopts:
                exit("Extracted quality {} is not available. Only 1, 2, 3, 4, 5 options are available.".format(quality))
            else:
                self.__config["quality"] = quality
        else:
            self.__config["quality"] = 1

        if (args.ffmpeg_path is not None):
            check = self._checkFileExists(args.ffmpeg_path)
            if check == False:
                exit("{} does not exists.".format(args.input))
            self.setFFmpegPath(args.ffmpeg_path)
        else:
            self.setFFmpegPath("")
    
    def __createDirectories(self):
        if os.path.exists(self.__config["imageFolderPath"]):
            shutil.rmtree(self.__config["imageFolderPath"])
        os.makedirs(self.__config["imageFolderPath"], exist_ok=True) 


    def __saveXmlMetaFile(self, name, output):
        xmlData = output
        xmlFileName = self.__config["imageFolderPath"] + os.sep + name
        logging.info("Trying to save xml file: {}".format(xmlFileName))
        with open(xmlFileName, "w") as f:
            f.write(xmlData)
            f.close()
            return xmlFileName
        logging.info("Unable to save xml file: {}".format(xmlFileName))
        return None

    def __getXMLInfoFromVideo(self, output):
        xmlFileName = self.__config["imageFolderPath"] + os.sep + self.__config["imageFolder"] + '.xml'
        return self.__saveXmlMetaFile(self.__config["imageFolder"]+".xml", output)
    
    def __getXMLData(self, root, videoInfoFields, gpsFields, Track):
        gpsData = []
        videoFieldData = {}
        videoFieldData['ProjectionType'] = ''
        videoFieldData['StitchingSoftware'] = ''
        videoFieldData['MetaFormat'] = ''
        videoFieldData['CompressorName'] = ''
        videoFieldData['CompressorNameTrack'] = []
        nsmap = root[0].nsmap
        anchor = ''
        data = {}
        ldata = {}
        adata = {}
        for elem in root[0]:
            eltags = elem.tag.split("}")
            nm = eltags[0].replace("{", "")
            tag = eltags[-1].strip()
            if tag in videoInfoFields:
                if tag == 'MetaFormat':
                    if elem.text.strip() == 'gpmd':
                        for k, v in nsmap.items():
                            if v == nm:
                                Track = k
                                break
                        videoFieldData[tag.strip()] = elem.text.strip()
                elif tag == 'ProjectionType':
                    if elem.text.strip() == 'equirectangular':
                        videoFieldData[tag] = elem.text.strip()
                elif tag == 'CompressorName':
                    if elem.text.strip() == 'GoPro H.265 encoder':
                        for k, v in nsmap.items():
                            if v == nm:
                                videoFieldData['CompressorNameTrack'].append(int(k.replace("Track", "")))
                                break
                else:
                    videoFieldData[tag.strip()] = elem.text.strip()
        for elem in root[0]:
            eltags = elem.tag.split("}")
            nm = eltags[0].replace("{", "")
            tag = eltags[-1].strip()
            if (tag in gpsFields) and (nm == nsmap[Track]):
                if tag.strip() in ['GPSHPositioningError', 'GPSMeasureMode']:
                    adata[tag] = elem.text.strip()
                if tag == 'GPSDateTime':
                    if anchor != '': 
                        for k, v in adata.items():
                            data[k] = v
                        gpsData.append(data)
                        anchor = str(elem.text.strip())
                        data = {
                            'GPSData': [],
                            'GPSHPositioningError': '',
                            'GPSMeasureMode': '',
                            'GPSDateTime': anchor
                        }
                    else:
                        anchor = str(elem.text.strip())
                        data = {
                            'GPSData': [],
                            'GPSHPositioningError': '',
                            'GPSMeasureMode': '',
                            'GPSDateTime': anchor
                        }
                        for k, v in adata.items():
                            data[k] = v
                else:
                    if tag.strip() in ['GPSLatitude', 'GPSLongitude', 'GPSAltitude']:
                        if (len(ldata) <= 3):
                            ldata[tag] = elem.text.strip()
                            if len(ldata) == 3:
                                if len(data['GPSData']) > 0:
                                    prev = data['GPSData'][-1]
                                    if ((ldata['GPSLatitude'] == prev['GPSLatitude']) and (ldata['GPSLongitude'] == prev['GPSLongitude']) and (ldata['GPSAltitude'] == prev['GPSAltitude'])):
                                        print("Found duplicate GPS POint...")
                                        print(anchor, ldata, prev)
                                        print("\n")
                                    else:
                                        data['GPSData'].append(ldata)
                                else:
                                    data['GPSData'].append(ldata)
                                ldata = {}
        for k, v in adata.items():
            data[k] = v
        gpsData.append(data)
        for gps in gpsData:
            print(gps['GPSDateTime'], len(gps['GPSData']))
            for p in gps['GPSData']:
                print(p)
        exit()
        output = self.__gpsTimestamps(gpsData)
        return {
            "filename": output["filename"],
            "startTime": output["startTime"],
            "video_field_data": videoFieldData
        }


    def __extractVideoInformationPre(self, videoFile, Track):
        logging.info("Running exiftool to extract metadata...")
        print("Running exiftool to extract metadata...")

        images = fnmatch.filter(os.listdir(self.__config["imageFolderPath"]), '*.jpg')
        images.sort()
        output = self._exiftool(["-ee", "-G3", "-api", "LargeFileSupport=1", "-X", self.__config["args"].input])
        if output["output"] is None:
            logging.critical(output["error"])
            logging.critical("Unable to get metadata information")
            exit("Unable to get metadata information")

        xmlFileName = self.__getXMLInfoFromVideo(output["output"])
        if xmlFileName is None:
            exit("Unable to save metadata xml file.")
        root = ET.parse(xmlFileName).getroot()

        videoInfoFields = [
            'DeviceName', 
            'ProjectionType', 
            'MetaFormat',
            'StitchingSoftware',
            'VideoFrameRate',
            'SourceImageHeight',
            'SourceImageWidth',
            'FileSize',
            'FileType',
            'FileTypeExtension',
            'CompressorName'
        ] 
        gpsFields = [
            'GPSDateTime', 
            'GPSLatitude', 
            'GPSLongitude', 
            'GPSAltitude',
            'GPSHPositioningError',
            'GPSMeasureMode'
        ]
        _xmlData = self.__getXMLData(root, videoInfoFields, gpsFields, Track)
        return _xmlData

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str, help="Input a valid video file.")
    parser.add_argument("-r", "--frame-rate", type=int, help="Sets the frame rate (frames per second) for extraction, default: 5.", default=5)
    parser.add_argument("-t", "--time-warp", type=str, help="Set time warp mode for gopro. available values are 2x, 5x, 10x, 15x, 30x")
    parser.add_argument("-f", "--ffmpeg-path", type=str, help="Set the path for ffmpeg.")
    parser.add_argument("-m", "--max-sphere", type=str, help="Set the path for MAX2sphere binary.")
    parser.add_argument("-q", "--quality", type=int, help="Sets the extracted quality between 2-6. 1 being the highest quality (but slower processing), default: 1. This is value used for ffmpeg -q:v flag. ", default=1)
    parser.add_argument("-d", "--debug", action='store_true', help="Enable debug mode, default: off.")
    args = parser.parse_args()
    dateTimeCurrent = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    goProMp4 = TrekViewGoProMp4(args, dateTimeCurrent)
    exit("Extraction complete, you can see your images now.")
