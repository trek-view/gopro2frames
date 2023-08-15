import configparser, subprocess, threading, itertools, argparse, platform, logging, datetime, fnmatch, shutil, pandas as pd, shlex, html, copy, time, json, math, csv, os, re
from colorama import init, deinit, reinit, Fore, Back, Style
from gfmhelper import GoProFrameMakerHelper
from geographiclib.geodesic import Geodesic
from decimal import Decimal, getcontext
from haversine import haversine, Unit
from pathlib import Path
from lxml import etree as ET
from os import walk
import itertools
import gpxpy


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def ExiftoolGetMetadata(path, image, imageData):
    #Get metadata from exiftool
    cmd = ["exiftool", "-ee", "-G3", "-j", "{}{}{}".format(path, os.sep, image)]
    output = subprocess.run(cmd, capture_output=True)
    output = output.stdout.decode('utf-8',"ignore")
    photo = json.loads(output)[0]
    imageData[image] = photo
    #print(photo)

def ExiftoolGetImagesMetadata(path, images, imageData):
    images = list(chunks(images, 5))

    for image in images:
        threads = []
        for i in range(0, len(image)):
            threads.append(threading.Thread(target=ExiftoolGetMetadata, args=(path, image[i],imageData,)))

        for t in threads:
            t.start()

        for t in threads:
            t.join()
    return imageData

def ExiftoolInjectMetadata(metadata):
    metadata.insert(0, "exiftool")
    output = subprocess.run(metadata, capture_output=True)
    if output.returncode == 0:
        print("Injecting additional metadata to {} is done.".format(metadata[-1]))
    else:
        print("Error Injecting additional metadata to {}.".format(metadata[-1]))

def ExiftoolInjectImagesMetadata(cmdMetaDataAll):
    metadatas = list(chunks(cmdMetaDataAll, 5))

    for metadata in metadatas:
        threads = []
        for i in range(0, len(metadata)):
            threads.append(threading.Thread(target=ExiftoolInjectMetadata, args=(metadata[i],)))

        for t in threads:
            t.start()

        for t in threads:
            t.join()
    return

def createNadir(nadir, magick):
    print(nadir, magick)
    #magick trek-view-square-nadir.png -rotate 180 -strip trek-view-square-nadir-1.png
    #magick trek-view-square-nadir-1.png -distort DePolar 0  trek-view-square-nadir-2.png
    #magick trek-view-square-nadir-2.png -flip  trek-view-square-nadir-3.png
    #magick trek-view-square-nadir-3.png -flop  trek-view-square-nadir-4.png
    cmd = [
        magick, nadir, "-rotate", "180", "-strip", nadir
    ]
    out = subprocess.run(cmd)
    print(out)
    cmd = [
        magick, nadir, "-distort", "DePolar", "0", "-strip", nadir
    ]
    out = subprocess.run(cmd)
    print(out)
    cmd = [
        magick, nadir, "-flip", "-strip", nadir
    ]
    out = subprocess.run(cmd)
    print(out)
    cmd = [
        magick, nadir, "-flop", "-strip", nadir
    ]
    out = subprocess.run(cmd)
    print(out)
    return nadir

def AddNadir(image, nadir, magick, imageData, equirectangular, height_percentage=15):
    image_path = Path(image)
    nadir_path = Path(nadir)

    new_nadir_path = Path(str(image_path.parent)+os.sep+str(nadir_path.name))
    new_nadir_path.write_bytes(nadir_path.read_bytes())

    image = str(image_path.resolve())
    nadir = str(new_nadir_path.resolve())
    print('equirectangular', equirectangular)
    imageWidth = imageData["Main:ImageWidth"]
    imageHeight = imageData["Main:ImageHeight"]
    if equirectangular == False:
        imageWidth = "-1"
    else:
        nadir = createNadir(nadir, magick)
        imageWidth = str(imageWidth)
    imageHeight = int(imageHeight)*(height_percentage/100)
    imageHeight = str(round(imageHeight))
    print(imageWidth, imageHeight)
    print("path for nadir: {}".format(nadir))
    print("path for image: {}".format(image))
    cmd = [
        "ffmpeg", 
        "-y", 
        "-i", 
        str("{}".format(image)), 
        "-i", str("{}".format(nadir)), 
        "-filter_complex", str("[1:v]scale="+imageWidth+":"+imageHeight+" [ovrl],[0:v][ovrl] overlay=(W-w):(H-h)"), 
        str("{}".format(image))
    ]
    print(" ".join(cmd))
    logging.info(" ".join(cmd))
    fout = subprocess.run(cmd)
    logging.info("Adding Nadir to {} is done.".format(image))
    print("Adding Nadir to {} is done.".format(image))


class GoProFrameMakerParent():
    def __init__(self, args):
        getcontext().prec = 6
        media_folder_full_path = str(args["media_folder_full_path"].resolve())
        try:
            if os.path.exists(media_folder_full_path):
                shutil.rmtree(media_folder_full_path)
            os.makedirs(media_folder_full_path, exist_ok=True) 
        except:
            exit('Unable to create main media directory {}'.format(media_folder_full_path))
        
        args['log_folder'] = Path('{}{}{}'.format(str(args['current_directory'].resolve()), os.sep, 'logs'))
        args['date_time_current'] = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        self.__args = copy.deepcopy(args)
        self.__setLogging()

    def get_arguments(self):
        return copy.deepcopy(self.__args)

    def __setLogging(self):
        logFolder = str(self.__args['log_folder'].resolve())
        dateTimeCurrent = self.__args["date_time_current"]
        if not os.path.exists(logFolder):
            os.makedirs(logFolder, exist_ok=True)
        if self.__args['debug'] is True:
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
        return alt

    def decimalDivide(self, num1, num2):
        a = round(num1, 6)
        b = round(num2, 6)
        num1 = Decimal(a)
        num2 = Decimal(b)
        if num2 == 0.0:
            return 0.0
        if num1 == 0.0:
            return 0.0
        num = Decimal(num1 / num2)
        if num == 0.0:
            num = abs(num)
        return round(float(num), 3)

    def calculateBearing(self, lat1, long1, lat2, long2):
        Long = (long2-long1)
        y = math.sin(Long) * math.cos(lat2)
        x = math.cos(lat1)*math.sin(lat2) - math.sin(lat1)*math.cos(lat2)*math.cos(Long)
        brng = math.degrees((math.atan2(y, x)))
        brng = (((brng + 360) % 360))
        return brng

    def calculateExtensions(self, gps, times, positions, etype=1, utype=1):
        if utype == 1:
            gps_speed_accuracy_meters = float('0.1')
            gps_fix_type = gps["GPSMeasureMode"]
            gps_vertical_accuracy_meters = float(gps["GPSHPositioningError"].strip())
            gps_horizontal_accuracy_meters = float(gps["GPSHPositioningError"].strip())
        else:
            gps_speed_accuracy_meters = float('0.1')
            gps_fix_type = '3-Dimensional Measurement'
            gps_vertical_accuracy_meters = float('0.1')
            gps_horizontal_accuracy_meters = float('0.1')
        
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
            AC = math.sin(math.radians(azimuth1))*distance
            BC = math.cos(math.radians(azimuth2))*distance

            #print((start_latitude, start_longitude), (end_latitude, end_longitude))
            #print("AC: {}, BC: {}, azimuth1: {}, azimuth2: {}, \ntime: {}, distance: {} seconds: {}\n\n\n".format(AC, BC, azimuth1, azimuth2, Decimal(time_diff), distance, gps_epoch_seconds))
            gps_elevation_change_next_meters = float(end_altitude - start_altitude)
            gps_velocity_east_next_meters_second = self.decimalDivide( AC, time_diff ) 
            gps_velocity_north_next_meters_second = self.decimalDivide( BC, time_diff )
            gps_velocity_up_next_meters_second = self.decimalDivide( gps_elevation_change_next_meters, time_diff )
            gps_speed_next_meters_second = self.decimalDivide( distance, time_diff )
            gps_heading_next_degrees = self.decimalDivide( compass_bearing, 1 )
            gps_pitch_next_degrees = self.decimalDivide( gps_elevation_change_next_meters, distance ) % 360
            gps_distance_next_meters = distance
            gps_speed_next_kmeters_second = self.decimalDivide( gps_distance_next_meters, 1000.0  ) #in kms
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
            "gps_vertical_accuracy_meters": "{0:.3f}".format(gps_vertical_accuracy_meters),
            "gps_horizontal_accuracy_meters": "{0:.3f}".format(gps_horizontal_accuracy_meters),
            "gps_velocity_east_next_meters_second": "{0:.3f}".format(gps_velocity_east_next_meters_second),
            "gps_velocity_north_next_meters_second": "{0:.3f}".format(gps_velocity_north_next_meters_second),
            "gps_velocity_up_next_meters_second": "{0:.3f}".format(gps_velocity_up_next_meters_second),
            "gps_speed_accuracy_meters": "{0:.3f}".format(gps_speed_accuracy_meters),
            "gps_speed_next_meters_second": "{0:.3f}".format(gps_speed_next_meters_second),
            "gps_heading_next_degrees": "{0:.3f}".format(gps_heading_next_degrees),
            "gps_elevation_change_next_meters": "{0:.3f}".format(gps_elevation_change_next_meters),
            "gps_pitch_next_degrees": "{0:.3f}".format(gps_pitch_next_degrees),
            "gps_distance_next_meters": "{0:.3f}".format(gps_distance_next_meters),
            "gps_time_next_seconds": "{0:.3f}".format(gps_time_next_seconds),
            "gps_speed_next_kmeters_second": "{0:.3f}".format(gps_speed_next_kmeters_second)
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
                out = ''
                if output.stdout  is not None:
                    out = output.stdout.decode('utf-8',"ignore")
                    logging.info(str(out))
                ret = {
                    "output": out,
                    "error": None
                }
            else:
                print(output)
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

    def __exiftool(self, command, sh=0):
        if platform.system() == "Windows":
            exiftool = "exiftool.exe"
        else:
            exiftool = "exiftool"
        command.insert(0, "-config")
        command.insert(1, ".ExifTool_config")
        command.insert(0, exiftool)
        ret = self.__subprocess(command, sh)
        if ret["error"] is not None:
            print(command)
            logging.critical(ret["error"])
            print(ret["error"])
            exit("Error occured while executing exiftool.")
        return ret

    def _ffmpeg(self, command, sh=0):
        ffmpeg = str(self.__args['ffmpeg'].resolve())
        command.insert(0, ffmpeg)
        ret = self.__subprocess(command, sh, False)
        print(ret)
        
        """if ret["error"] is not None:
            logging.critical(ret["error"])
            exit("Error occured while executing ffmpeg, please see logs for more info.")"""
        return True

    def exiftool(self, cmd):
        output = self.__exiftool(cmd, 1)
        #print(" ".join(output))
        if output["output"] is None:
            logging.critical(output["error"])
            logging.critical("Unable to get metadata information")
            exit("Unable to get metadata information")
        else:
            return output["output"]

    def get_video_exif_data(self):
        video_file = '{}'.format(str(self.__args['input'][0].resolve()))
        output = self.__exiftool(["-ee", "-G3", "-api", "LargeFileSupport=1", "-X", video_file], 1)
        if output["output"] is None:
            logging.critical(output["error"])
            logging.critical("Unable to get metadata information")
            exit("Unable to get metadata information")
        else:
            return output["output"]

class GoProFrameMaker(GoProFrameMakerParent):
    def __init__(self, args):
        args["media_folder"] = os.path.basename(str(args['input'][0].resolve())).split(".")[0]
        args["file_type"] = os.path.basename(str(args['input'][0].resolve())).split(".")[-1]
        args["media_folder_full_path"] = Path('{}{}{}'.format(str(args['current_directory'].resolve()), os.sep, args["media_folder"]))
        super().__init__(args)

    def getArguments(self):
        return copy.deepcopy(self.get_arguments())

    def initiateProcessing(self):
        self.__startProcessing()

    def __startProcessing(self):
        camera = ''
        equirectangular = False
        args = self.getArguments()
        media_folder_full_path = str(args["media_folder_full_path"].resolve())
        #validation max video file size
        if(len(args["input"]) == 1):
            video_file = str(args["input"][0].resolve())
            fileStat = os.stat(video_file)
            if fileStat.st_size > 8000000000:
                logging.critical("The following file {} is too large. The maximum size for a single video is 8GB".format(video_file))
                exit("The following file {} is too large. The maximum size for a single video is 8GB".format(video_file))
        #validation fusion video file size
        elif(len(args["input"]) == 2):
            video_file_front = str(args["input"][0].resolve())
            video_file_back = str(args["input"][1].resolve())
            file_stat_front = os.stat(video_file_front)
            file_stat_back = os.stat(video_file_back)
            if file_stat_front.st_size > 4000000000:
                logging.critical("The following file {} is too large. The maximum size for a single video is 4GB".format(video_file_front))
                exit("The following file {} is too large. The maximum size for a single video is 4GB".format(video_file_front))
            if file_stat_back.st_size > 4000000000:
                logging.critical("The following file {} is too large. The maximum size for a single video is 4GB".format(file_stat_back))
                exit("The following file {} is too large. The maximum size for a single video is 4GB".format(file_stat_back))
        
        #getting video metadata
        metadata = self.__getVideoMetadata()

        #validation video
        self.__validateVideo(metadata["video_field_data"])

        fileType = args["file_type"].strip().lower()

        #checking if projection type is equirectangular
        if(metadata["video_field_data"]["ProjectionType"] == "equirectangular"):
            equirectangular = True
        if(metadata['video_field_data']['DeviceName'] == 'GoPro Max'):
            camera = 'max'
            if((equirectangular == False) and (args['predicted_camera'] == 'max') and (fileType == '360')):
                equirectangular = True
        if(metadata['video_field_data']['DeviceName'].lower() in ['gopro fusion', 'fusion']):
            camera = 'fusion'
            if((equirectangular == False) and (args['predicted_camera'] == 'fusion') and (fileType == 'mp4')):
                equirectangular = True
        
        #getting frames
        if fileType == "360":
            if camera == 'max':
                self.__breakIntoFrames360(metadata, video_file, media_folder_full_path)
            else:
                exit('Unknown camera type.')
        elif fileType in ["mp4", "mov"]:
            if camera == 'max':
                self.__breakIntoFrames(video_file, media_folder_full_path)
            elif camera == 'fusion':
                fusion_front = "{}{}{}".format(media_folder_full_path, os.sep, 'front')
                if os.path.exists(fusion_front):
                    shutil.rmtree(fusion_front)
                os.makedirs(fusion_front, exist_ok=True) 
                fusion_back = "{}{}{}".format(media_folder_full_path, os.sep, 'back')
                if os.path.exists(fusion_back):
                    shutil.rmtree(fusion_back)
                os.makedirs(fusion_back, exist_ok=True) 
                self.__breakIntoFrames(video_file_front, fusion_front, '')
                self.__breakIntoFrames(video_file_back, fusion_back, '')
                total_images = fnmatch.filter(os.listdir(fusion_front), '*.jpg')
                cmd = [
                    str(args['fusion_sphere'].resolve()), 
                    '-w', str(4096), '-b', '5',
                    '-g', '1', '-h', str(len(total_images)), 
                    '-o', "{}{}%06d.jpg".format(media_folder_full_path, os.sep),
                    '-x', "{}{}%06d.jpg".format(fusion_front, os.sep), "{}{}%06d.jpg".format(fusion_back, os.sep),
                    str(args['fusion_sphere_params'].resolve())
                ]
                output = subprocess.run(cmd, capture_output=True)
                if os.path.exists(fusion_front):
                    shutil.rmtree(fusion_front)
                if os.path.exists(fusion_back):
                    shutil.rmtree(fusion_back)
            else:
                exit('Unknown camera type.')
        else:
            exit('Unknown file type.')

        #ms calculation
        if args["time_warp"] is None:
            ms = float(((100.0/float(args["frame_rate"]))/100.0))
        else:
            tw = args["time_warp"]
            fr = args["frame_rate"]
            tw = int(tw.replace('x', ''))
            if fr < 1:
                fr = 5
            tw = float(tw)/float(fr)
            ms = float(tw)

        metadata['images'] = fnmatch.filter(os.listdir(media_folder_full_path), '*.jpg')
        metadata['images'].sort()
        startTime = metadata['startTime']
        icounter = 0
        if len(metadata['images']) > 0:
            print('\nStarting to geotag all the images...\n')
            for img in metadata['images']:
                GPSDateTime = datetime.datetime.strftime(startTime, "%Y:%m:%d %H:%M:%S.%f")
                tt = GPSDateTime.split(".")
                tt[1] = tt[1][:3]
                tz = "T".join(tt[0].split(" "))
                tt[0] = tz
                cmdMetaData = [
                    '-DateTimeOriginal={0}Z'.format(tt[0]),
                    '-SubSecTimeOriginal={0}'.format(tt[1]),
                    '-SubSecDateTimeOriginal={0}Z'.format(".".join(tt))
                ]
                cmdMetaData.append('-overwrite_original')
                cmdMetaData.append("{}{}{}".format(media_folder_full_path, os.sep, metadata['images'][icounter]))
                output = self.exiftool(cmdMetaData)
                startTime = startTime+datetime.timedelta(0, ms) 
                icounter = icounter + 1
            cmd = [
                '-geotag', 
                '{}{}{}{}'.format(media_folder_full_path, os.sep, args["media_folder"], "_video.gpx"), 
                '-geotime<${subsecdatetimeoriginal}', 
                '-overwrite_original', 
                media_folder_full_path
            ]
            
            output = self.exiftool(cmd)
            
            self.__updateImagesMetadata(metadata, equirectangular)
        else:
            exit('Not enough images available for geotagging.')

    def __validateVideo(self, videoData):
        args = self.getArguments()
        #Validate Critical Errors
        #print(videoData)
        if videoData['MetaFormat'].strip()  != 'gpmd':
            metaFormat = False
            logging.critical("Your video has no telemetry. You need to enable GPS on your GoPro to ensure GPS location is captured.")
            exit("Your video has no telemetry. You need to enable GPS on your GoPro to ensure GPS location is captured.")
        else:
            metaFormat = True
        
        if videoData["ProjectionType"].strip()  != 'equirectangular':
            if metaFormat is False:
                logging.critical("This does not appear to be a GoPro 360 video. Only mp4 videos with a 360 equirectangular projection are accepted. Please make sure you are uploading 360 mp4 videos from your camera.")
                exit("This does not appear to be a GoPro 360 video. Only mp4 videos with a 360 equirectangular projection are accepted. Please make sure you are uploading 360 mp4 videos from your camera.")
        
        devices = ["Fusion", "GoPro Max"]
        if videoData['DeviceName'].strip() not in devices:
            logging.critical("This file does not look like it was captured using a GoPro camera. Only content taken using a GoPro 360 Camera are currently supported.")
            exit("This file does not look like it was captured using a GoPro camera. Only content taken using a GoPro 360 Camera are currently supported.")
        
        if args["frame_rate"] > 5:
            logging.warning("It appears the frame rate of this video is very low. You can continue, but the images in the Sequence might not render as expected.")
            print("It appears the frame rate of this video is very low. You can continue, but the images in the Sequence might not render as expected.")

        if args["time_warp"] is not None:
            logging.warning("It appears this video was captured in timewarp mode. You can continue, but the images in the Sequence might not render as expected.")
            print("It appears this video was captured in timewarp mode. You can continue, but the images in the Sequence might not render as expected.")

        FileType = ["MP4", "360", "MOV"]
        if videoData["FileType"].strip().upper() not in FileType:
            logging.critical("The following filetype {} is not supported. Please upload only .mp4 or .360 videos.".format(videoData["FileType"]))
            exit("The following filetype {} is not supported. Please upload only .mp4 or .360 videos.".format(videoData["FileType"]))
        else:
            if videoData["FileType"].strip() == "360":
                if videoData["CompressorName"] == "H.265":
                    logging.critical("This does not appear to be a GoPro .360 file. Please use the .360 video created from your GoPro camera only.")
                    exit("This does not appear to be a GoPro .360 file. Please use the .360 video created from your GoPro camera only.")

    def __breakIntoFrames(self, filename, fileoutput, prefix=''):
        args = self.getArguments()
        logging.info("Running ffmpeg to extract images...")
        print("Please wait while image extraction is complete.\nRunning ffmpeg to extract images...")
        test_str = ""
        if args['debug'] is True:
            if "time_warp" in args:
                tw = "-t_{}x".format(args["time_warp"])
            else:
                tw = ""
            test_str = "-q_{}-r_{}fps{}".format(
                args["quality"], 
                args["frame_rate"], tw
            )
        cmd = [
            "-i", filename, 
            "-r", str(args["frame_rate"]), 
            "-q:v", str(args["quality"]), 
            "{}{}{}%06d.jpg".format(fileoutput, os.sep, prefix)
        ]

        output = self._ffmpeg(cmd, 1)
        
    def __breakIntoFrames360(self, videoData, filename, fileoutput):
        args = self.getArguments()
        media_folder_full_path = str(args["media_folder_full_path"].resolve())
        logging.info("Running ffmpeg to extract images...")
        print("Please wait while image extraction is complete.\nRunning ffmpeg to extract images...")

        tracks = videoData['video_field_data']['CompressorNameTrack']
        if (type(tracks) == list) and (len(tracks) == 2):
            tracks[0] = 0 if (tracks[0]-1) < 0 else (tracks[0]-1)
            tracks[1] = 0 if (tracks[1]-1) < 0 else (tracks[1]-1)
            trackmapFirst = "0:{}".format(tracks[0])
            trackmapSecond = "0:{}".format(tracks[1])
        else:
            trackmapFirst = "0:{}".format(0)
            trackmapSecond = "0:{}".format(5)

        track0 = "{}{}{}".format(fileoutput, os.sep, 'track0')
        if os.path.exists(track0):
            shutil.rmtree(track0)
        os.makedirs(track0, exist_ok=True) 
        track5 = "{}{}{}".format(fileoutput, os.sep, 'track5')
        if os.path.exists(track5):
            shutil.rmtree(track5)
        os.makedirs(track5, exist_ok=True) 
        cmd = [
            "-i", filename,
            "-map", trackmapFirst,
            "-r", str(args["frame_rate"]), 
            "-q:v", str(args["quality"]),
            track0 + os.sep + "%06d.jpg",
            "-map", trackmapSecond,
            "-r", str(args["frame_rate"]),
            "-q:v", str(args["quality"]), 
            track5 + os.sep + "%06d.jpg"
        ]
        
        output = self._ffmpeg(cmd, 1)

        total_images = fnmatch.filter(os.listdir("{}{}{}".format(media_folder_full_path, os.sep, 'track0')), '*.jpg')

        imgWidth = videoData['video_field_data']['SourceImageWidth']
        if imgWidth == 4096:
            _w = 5376
        elif imgWidth == 2272:
            _w = 3072
        else:
            _w = imgWidth
        
        try:
            if args['max_sphere'] == None:
                if platform.system() == "Windows":
                    max_sphere = ".{}max2sphere-batch{}MAX2spherebatch.exe".format(os.sep, os.sep)
                else:
                    max_sphere = ".{}max2sphere-batch{}MAX2spherebatch".format(os.sep, os.sep)
            else:
                max_sphere = str(args['max_sphere'].resolve()).strip()

            cmd = [
                max_sphere, '-w', str(imgWidth), '-n', '1', '-m', str(len(total_images)), 
                '-o', '{}{}{}'.format(media_folder_full_path, os.sep, '%06d.jpg'),
                '{}{}{}'.format(media_folder_full_path, os.sep, 'track%d/%06d.jpg')
            ]
            print(max_sphere)
            output = subprocess.run(cmd, capture_output=True)
            #Max2Sphere(max_sphere, _w, media_folder_full_path, track0, track5)
        except Exception as e:
            logging.info(str(e))
            print(str(e))
            exit("Unable to convert 360 deg video.")

        if os.path.exists(track0):
            shutil.rmtree(track0)
        if os.path.exists(track5):
            shutil.rmtree(track5)
        return filename

    def __getVideoMetadata(self):
        args = self.getArguments()
        exif_xml_data = self.get_video_exif_data()
        xmlFileName = "{}{}{}.xml".format(args["media_folder_full_path"], os.sep, args["media_folder"])
        self.__saveAFile(xmlFileName, exif_xml_data)
        if(Path(xmlFileName).is_file() == False):
            exit('Unable to save xml file: {}'.format(xmlFileName))
        return self.__parseMetadata(xmlFileName)

    def __parseMetadata(self, xmlFileName):
        root = ET.parse(xmlFileName).getroot()
        nsmap = root[0].nsmap

        videoInfoFields = [
            'Duration',
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
        gpsData = []
        videoFieldData = {}
        videoFieldData['ProjectionType'] = ''
        videoFieldData['StitchingSoftware'] = ''
        videoFieldData['MetaFormat'] = ''
        videoFieldData['CompressorName'] = ''
        videoFieldData['CompressorNameTrack'] = []
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
                                """if len(data['GPSData']) > 0:
                                    prev = data['GPSData'][-1]
                                    if (((ldata['GPSLatitude'] == prev['GPSLatitude']) and (ldata['GPSLongitude'] == prev['GPSLongitude']) and (ldata['GPSAltitude'] == prev['GPSAltitude'])) is not True):
                                        data['GPSData'].append(ldata)
                                    else:
                                        print("Found duplicate GPS POint...")
                                        print(ldata, prev)
                                else:
                                    data['GPSData'].append(ldata)"""
                                data['GPSData'].append(ldata)
                                ldata = {}
        for k, v in adata.items():
            data[k] = v
        gpsData.append(data)

        if 'Duration' in videoFieldData:
            _tsm = videoFieldData['Duration'].strip().split(' ')
            if len(_tsm) > 0:
                _t = float(_tsm[0])
                _sm = _tsm[-1]
                if _sm == 's':
                    videoFieldData['Duration'] = "00:00:{:06.3F}".format(_t)
            else:
                if '.' not in videoFieldData['Duration']:
                    videoFieldData['Duration'] = "{}.000".format(videoFieldData['Duration'].strip())

        output = GoProFrameMakerHelper.gpsTimestamps(gpsData, videoFieldData)
        args = self.getArguments()
        output["filename"] = "{}{}{}_video.gpx".format(args["media_folder_full_path"], os.sep, args["media_folder"])
        self.__saveAFile(output["filename"], output['gpx_data'])
        if(Path(output["filename"]).is_file() == False):
            exit('Unable to save file: {}'.format(output["filename"]))

        return {
            "filename": output["filename"],
            "startTime": output["start_time"],
            "video_field_data": videoFieldData
        }

    def __gpsTimestamps(self, gpsData, videoFieldData):
        gpx = gpxpy.gpx.GPX()

        # Create first track in our GPX:
        gpx_track = gpxpy.gpx.GPXTrack()
        gpx.tracks.append(gpx_track)

        # Create first segment in our GPX track:
        gpx_segment = gpxpy.gpx.GPXTrackSegment()
        gpx_track.segments.append(gpx_segment)
        Timestamps = []
        counter = 0
        gLen = len(gpsData)
        for gps in gpsData:
            if counter < gLen-1:
                start_gps = gpsData[counter]
                end_gps = gpsData[counter + 1]

                #Get Times from metadata
                start_time = datetime.datetime.strptime(start_gps["GPSDateTime"].replace("Z", ""), "%Y:%m:%d %H:%M:%S.%f")
                end_time = datetime.datetime.strptime(end_gps["GPSDateTime"].replace("Z", ""), "%Y:%m:%d %H:%M:%S.%f")
                time_diff = (end_time - start_time).total_seconds()
                diff = int((time_diff/float(len(start_gps["GPSData"])))*1000.0)
                #check this later
                if diff == 0:
                    if start_time == end_time:
                        start_time = end_time
                        diff = int((0.05)*1000.0)
                        end_time = end_time+datetime.timedelta(0, 0.05) 
                new = pd.date_range(start=start_time, end=end_time, closed='left', freq="{}ms".format(diff))
                icounter = 0
                dlLen = 1 if len(start_gps["GPSData"]) < 1 else len(start_gps["GPSData"])
                nlLen = 1 if len(new) < 1 else len(new)
                _ms = math.floor(dlLen/nlLen)
                _ms = 1 if _ms < 1 else _ms
                for gps in start_gps["GPSData"]:
                    tBlock = gps.copy()
                    tBlock["GPSDateTime"] = new[icounter]
                    tBlock["GPSMeasureMode"] = start_gps["GPSMeasureMode"]
                    tBlock["GPSHPositioningError"] = start_gps["GPSHPositioningError"]
                    Timestamps.append(tBlock)
                    icounter = icounter + _ms
            else:
                #datetime.datetime.strptime("0:0:0 0:0:0.0", "%Y:%m:%d %H:%M:%S.%f")
                start_gps = gpsData[counter]
                #Get Times from metadata

                #_e_date = start_gps["GPSDateTime"].split(" ")[0]
                zero_start = datetime.datetime.strptime("2022:1:1 00:00:00.000", "%Y:%m:%d %H:%M:%S.%f")
                zero_duration = datetime.datetime.strptime("2022:1:1 {}".format(videoFieldData['Duration']), "%Y:%m:%d %H:%M:%S.%f")
                

                start_time = datetime.datetime.strptime(start_gps["GPSDateTime"].replace("Z", ""), "%Y:%m:%d %H:%M:%S.%f")
                first_start_time = datetime.datetime.strptime(gpsData[0]["GPSDateTime"].replace("Z", ""), "%Y:%m:%d %H:%M:%S.%f")
                l_1 = (start_time - first_start_time).total_seconds()
                l_2 = (zero_duration - zero_start).total_seconds()
                end_time = start_time+datetime.timedelta(0, l_2-l_1) 
                time_diff = (end_time - start_time).total_seconds()
                diff = int((time_diff/float(len(start_gps["GPSData"])))*1000.0)
                #check this later
                if diff == 0:
                    if start_time == end_time:
                        print('####')
                        start_time = end_time
                        diff = int((0.05)*1000.0)
                        end_time = end_time+datetime.timedelta(0, 0.05) 
                new = pd.date_range(start=start_time, end=end_time, closed='left', freq="{}ms".format(diff))
                icounter = 0
                dlLen = 1 if len(start_gps["GPSData"]) < 1 else len(start_gps["GPSData"])
                nlLen = 1 if len(new) < 1 else len(new)
                _ms = math.floor(dlLen/nlLen)
                _ms = 1 if _ms < 1 else _ms
                for gps in start_gps["GPSData"]:
                    tBlock = gps.copy()
                    tBlock["GPSDateTime"] = new[icounter]
                    tBlock["GPSMeasureMode"] = start_gps["GPSMeasureMode"]
                    tBlock["GPSHPositioningError"] = start_gps["GPSHPositioningError"]
                    Timestamps.append(tBlock)
                    icounter = icounter + _ms
            counter = counter + 1
        icounter = 0
        tlen = len(Timestamps)
        t1970 = datetime.datetime.strptime("1970:01:01 00:00:00.000000", "%Y:%m:%d %H:%M:%S.%f")
        prev = None
        for gps in Timestamps:
            #removing duplicate lat&lng
            if icounter > 0:
                prev = Timestamps[icounter-1]
                if ((gps['GPSLatitude'] == prev['GPSLatitude']) and (gps['GPSLongitude'] == prev['GPSLongitude']) and (gps['GPSAltitude'] == prev['GPSAltitude'])):
                    icounter = icounter + 1
                    continue
            #Get Start Time from metadata
            start_time = gps["GPSDateTime"]
            gps_epoch_seconds = (start_time-t1970).total_seconds()
            #Get Latitude, Longitude and Altitude
            start_latitude = self.latLngToDecimal(gps["GPSLatitude"])
            start_longitude = self.latLngToDecimal(gps["GPSLongitude"])
            start_altitude = self.getAltitudeFloat(gps["GPSAltitude"])
            gpx_point = gpxpy.gpx.GPXTrackPoint(
                latitude=start_latitude, 
                longitude=start_longitude, 
                time=start_time, 
                elevation=start_altitude
            )
            gpx_segment.points.append(gpx_point)
            if icounter < tlen-1:
                #Get End Time from metadata
                end_time = Timestamps[icounter+1]["GPSDateTime"]
                time_diff = (end_time - start_time).total_seconds()

                #Get Latitude, Longitude and Altitude
                end_latitude = self.latLngToDecimal(Timestamps[icounter+1]["GPSLatitude"])
                end_longitude = self.latLngToDecimal(Timestamps[icounter+1]["GPSLongitude"])
                end_altitude = self.getAltitudeFloat(Timestamps[icounter+1]["GPSAltitude"])

                ext = self.calculateExtensions(
                    gps, 
                    (start_time, end_time, gps_epoch_seconds),
                    (
                        (start_latitude, start_longitude, start_altitude),
                        (end_latitude, end_longitude, end_altitude)
                    ),
                    1, 1
                )
            else:
                ext = self.calculateExtensions(
                    gps, 
                    (start_time, None, gps_epoch_seconds),
                    (
                        (start_latitude, start_longitude, start_altitude),
                        (None, None, None)
                    ),
                    0, 1
                )
            del ext["gps_speed_next_kmeters_second"]
            for k, v in ext.items():
                gpx_extension = ET.fromstring(f"""
                    <{str(k)}>{str(v)}</{str(k)}>
                """)
                gpx_point.extensions.append(gpx_extension)
            icounter = icounter + 1
        gpxData = gpx.to_xml() 
        args = self.getArguments()

        filename = "{}{}{}_video.gpx".format(args["media_folder_full_path"], os.sep, args["media_folder"])
        self.__saveAFile(filename, gpxData)
        if(Path(filename).is_file() == False):
            exit('Unable to save file: {}'.format(filename))

        return {
            "filename": filename,
            "startTime": Timestamps[0]['GPSDateTime']
        }

    def __saveAFile(self, filename, data):
        logging.info("Trying to save file: {}".format(filename))
        with open(filename, "w") as f:
            f.write(data)
            f.close()
        logging.info("Unable to save file: {}".format(filename))

    def __updateImagesMetadata(self, data, equirectangular):
        args = self.getArguments()
        media_folder_full_path = str(args["media_folder_full_path"].resolve())
        print("Starting to inject additional metadata into the images...")

        gpx = gpxpy.gpx.GPX()

        # Create first track in our GPX:
        gpx_track = gpxpy.gpx.GPXTrack()
        gpx.tracks.append(gpx_track)

        # Create first segment in our GPX track:
        gpx_segment = gpxpy.gpx.GPXTrackSegment()
        gpx_track.segments.append(gpx_segment)

        counter = 0
        photosLen = len(data['images'])
        t1970 = datetime.datetime.strptime("1970:01:01 00:00:00.000000", "%Y:%m:%d %H:%M:%S.%f")

        imageData = {}
        imageData = ExiftoolGetImagesMetadata(media_folder_full_path, data['images'], imageData)

        cmdMetaDataAll = []
        
        if args["nadir_image"] != "":
            for image in data['images']:
                nadir_image = "{}{}{}".format(media_folder_full_path, os.sep, image)
                AddNadir(nadir_image, args["nadir_image"], args["image_magick_path"], imageData[image], equirectangular, int(args["nadir_percentage"]))

        counter = 0
        for img in data['images']:
            if counter < photosLen - 1:
                photo = [data['images'][counter], data['images'][counter + 1]]

                start_photo = imageData[data['images'][counter]]
                end_photo   = imageData[data['images'][counter + 1]]

                #Get Times from metadata
                start_time = datetime.datetime.strptime(start_photo["Main:GPSDateTime"].replace("Z", ""), "%Y:%m:%d %H:%M:%S.%f")
                end_time = datetime.datetime.strptime(end_photo["Main:GPSDateTime"].replace("Z", ""), "%Y:%m:%d %H:%M:%S.%f")
                time_diff = (end_time - start_time).total_seconds()
                gps_epoch_seconds = (start_time-t1970).total_seconds()

                #Get Latitude, Longitude and Altitude
                start_latitude = self.latLngToDecimal(start_photo["Main:GPSLatitude"])
                start_longitude = self.latLngToDecimal(start_photo["Main:GPSLongitude"])
                start_altitude = self.getAltitudeFloat(start_photo["Main:GPSAltitude"])
                end_latitude = self.latLngToDecimal(end_photo["Main:GPSLatitude"])
                end_longitude = self.latLngToDecimal(end_photo["Main:GPSLongitude"])
                end_altitude = self.getAltitudeFloat(end_photo["Main:GPSAltitude"])

                ext = self.calculateExtensions(
                    start_photo, 
                    (start_time, end_time, gps_epoch_seconds),
                    (
                        (start_latitude, start_longitude, start_altitude),
                        (end_latitude, end_longitude, end_altitude)
                    ),
                    1, 0
                )
            else:
                photo = [data['images'][counter], None]

                start_photo = imageData[data['images'][counter]]

                #Get Times from metadata
                start_time = datetime.datetime.strptime(start_photo["Main:GPSDateTime"].replace("Z", ""), "%Y:%m:%d %H:%M:%S.%f")
                gps_epoch_seconds = (start_time-t1970).total_seconds()

                ext = self.calculateExtensions(
                    start_photo, 
                    (start_time, None, gps_epoch_seconds),
                    (
                        (start_latitude, start_longitude, start_altitude),
                        (None, None, None)
                    ),
                    0, 0
                )
            gpx_point = gpxpy.gpx.GPXTrackPoint(
                latitude=start_latitude, 
                longitude=start_longitude, 
                time=start_time, 
                elevation=start_altitude
            )
            gpx_segment.points.append(gpx_point)
            kms = ext["gps_speed_next_kmeters_second"]
            del ext["gps_speed_next_kmeters_second"]
            for k, v in ext.items():
                gpx_extension = ET.fromstring(f"""
                    <{str(k)}>{str(v)}</{str(k)}>
                """)
                gpx_point.extensions.append(gpx_extension)

            cmdMetaData = [
                '-DateTimeOriginal={0}'.format(start_photo["Main:DateTimeOriginal"]),
                '-SubSecTimeOriginal={0}'.format(start_photo["Main:SubSecTimeOriginal"]),
                '-SubSecDateTimeOriginal={0}'.format(start_photo["Main:SubSecDateTimeOriginal"]),

                '-GPSDateTime={0}"'.format(start_photo["Main:GPSDateTime"]),
                '-GPSLatitude="{0}"'.format(start_photo["Main:GPSLatitude"]),
                '-GPSLongitude="{0}"'.format(start_photo["Main:GPSLongitude"]),
                '-GPSAltitude="{0}"'.format(start_photo["Main:GPSAltitude"]),

                '-GPSSpeed={}'.format(kms),
                '-GPSSpeedRef=k',
                '-GPSImgDirection={}'.format(ext['gps_heading_next_degrees']),
                '-GPSImgDirectionRef=m',
                '-GPSPitch={}'.format(ext['gps_pitch_next_degrees']),
                '-IFD0:Model="{}"'.format(self.removeEntities(data["video_field_data"]["DeviceName"]))
            ]
            if (data["video_field_data"]["ProjectionType"] == "equirectangular") or ("360ProjectionType" in data["video_field_data"]):
                cmdMetaData.append('-XMP-GPano:StitchingSoftware="Spherical Metadata Tool"')
                cmdMetaData.append('-XMP-GPano:ProjectionType="equirectangular"')
                cmdMetaData.append('-XMP-GPano:SourcePhotosCount="{}"'.format(2))
                cmdMetaData.append('-XMP-GPano:UsePanoramaViewer="{}"'.format("TRUE"))
                cmdMetaData.append('-XMP-GPano:CroppedAreaImageHeightPixels="{}"'.format(data["video_field_data"]["SourceImageHeight"]))
                cmdMetaData.append('-XMP-GPano:CroppedAreaImageWidthPixels="{}"'.format(data["video_field_data"]["SourceImageWidth"]))
                cmdMetaData.append('-XMP-GPano:FullPanoHeightPixels="{}"'.format(data["video_field_data"]["SourceImageHeight"]))
                cmdMetaData.append('-XMP-GPano:FullPanoWidthPixels="{}"'.format(data["video_field_data"]["SourceImageWidth"]))
                cmdMetaData.append('-XMP-GPano:CroppedAreaLeftPixels="{}"'.format(0))
                cmdMetaData.append('-XMP-GPano:CroppedAreaTopPixels="{}"'.format(0))
            cmdMetaData.append('-overwrite_original')
            cmdMetaData.append("{}{}{}".format(media_folder_full_path, os.sep, photo[0]))
            cmdMetaDataAll.append(cmdMetaData)
            counter = counter + 1
        ExiftoolInjectImagesMetadata(cmdMetaDataAll)
        gpxData = gpx.to_xml()
        filename = "{}{}{}_photos.gpx".format(args["media_folder_full_path"], os.sep, args["media_folder"])
        self.__saveAFile(filename, gpxData)
        if(Path(filename).is_file() == False):
            exit('Unable to save file: {}'.format(filename))
