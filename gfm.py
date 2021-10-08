import subprocess, itertools, argparse, platform, logging, datetime, fnmatch, shutil, pandas as pd, shlex, html, copy, time, json, math, csv, os, re
from geographiclib.geodesic import Geodesic
from haversine import haversine, Unit
from pathlib import Path
from lxml import etree as ET
from os import walk
import itertools
import gpxpy

class TrekviewHelpers():
    def __init__(self, config):
        """"""
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
            AC = (math.cos(math.radians(azimuth1))*distance)
            BC = (math.sin(math.radians(azimuth2))*distance)
            gps_elevation_change_next_meters = end_altitude - start_altitude
            gps_velocity_east_next_meters_second = 0 if time_diff == 0.0 else AC/time_diff  
            gps_velocity_north_next_meters_second = 0 if time_diff == 0.0 else BC/time_diff
            gps_velocity_up_next_meters_second = 0 if time_diff == 0.0 else gps_elevation_change_next_meters/time_diff
            gps_speed_next_meters_second = 0 if time_diff == 0.0 else distance/time_diff 
            gps_heading_next_degrees = compass_bearing
            gps_pitch_next_degrees = 0 if distance == 0.0 else (gps_elevation_change_next_meters / distance)%360
            gps_distance_next_meters = distance
            gps_speed_next_kmeters_second = gps_distance_next_meters/1000.0 #in kms
            gps_time_next_seconds = time_diff
        else:
            gps_epoch_seconds = times[2]
            gps_velocity_east_next_meters_second = 0
            gps_velocity_north_next_meters_second = 0
            gps_velocity_up_next_meters_second = 0
            gps_speed_next_meters_second = 0
            gps_speed_next_kmeters_second = 0
            gps_heading_next_degrees = 0
            gps_elevation_change_next_meters = 0
            gps_pitch_next_degrees = 0
            gps_distance_next_meters = 0
            gps_time_next_seconds = 0
        return {
            "gps_epoch_seconds": gps_epoch_seconds,
            "gps_fix_type": gps_fix_type,
            "gps_vertical_accuracy_meters": gps_vertical_accuracy_meters,
            "gps_horizontal_accuracy_meters": gps_horizontal_accuracy_meters,
            "gps_velocity_east_next_meters_second": gps_velocity_east_next_meters_second,
            "gps_velocity_north_next_meters_second": gps_velocity_north_next_meters_second,
            "gps_velocity_up_next_meters_second": gps_velocity_up_next_meters_second,
            "gps_speed_accuracy_meters": gps_speed_accuracy_meters,
            "gps_speed_next_meters_second": gps_speed_next_meters_second,
            "gps_heading_next_degrees": gps_heading_next_degrees,
            "gps_elevation_change_next_meters": gps_elevation_change_next_meters,
            "gps_pitch_next_degrees": gps_pitch_next_degrees,
            "gps_distance_next_meters": gps_distance_next_meters,
            "gps_time_next_seconds": gps_time_next_seconds,
            "gps_speed_next_kmeters_second": gps_speed_next_kmeters_second
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
        fileType = self.__validateVideo(videoData["video_field_data"])
        if fileType == "360":
            self.__config["fileType"] = '360'
            filename = self.__convert360tomp4(videoData)
            #self.__breakIntoFrames(filename)
        else:
            self.__breakIntoFrames(self.__config["args"].input)
        videoData['images'] = fnmatch.filter(os.listdir(self.__config["imageFolderPath"]), '*.jpg')
        startTime = videoData['startTime']
        icounter = 0
        if len(videoData['images']) > 0:
            print('\nStarting to geotag all the images...\n')
            for img in videoData['images']:
                GPSDateTime = datetime.datetime.strftime(startTime, "%Y:%m:%d %H:%M:%S.%f")
                tt = GPSDateTime.split(".")
                cmdMetaData = [
                    '-DateTimeOriginal="{0}Z"'.format(GPSDateTime),
                    '-SubSecTimeOriginal="{0}"'.format(tt[1]),
                    '-SubSecDateTimeOriginal="{0}Z"'.format(".".join(tt))
                ]
                cmdMetaData.append('-overwrite_original')
                cmdMetaData.append("{}{}{}".format(self.__config["imageFolderPath"], os.sep, videoData['images'][icounter]))
                output = self._exiftool(cmdMetaData)
                startTime = startTime+datetime.timedelta(0, ms) 
                icounter = icounter + 1
            cmd = ["-geotag", self.__config["imageFolderPath"]+os.sep+self.__config["imageFolder"] + "_video.gpx", "'-geotime<${subsecdatetimeoriginal}'", '-overwrite_original', self.__config["imageFolderPath"]]
            output = self._exiftool(cmd)
            self.__updateImagesMetadata(videoData)
        else:
            exit('Not enough images available for geotagging.')
            

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
    
    def __validateVideo(self, videoData):
        fileStat = os.stat(self.__config["args"].input)
        if fileStat.st_size > 1000000000:
            logging.critical("The following file {} is too large. The maximum size for a single video is 5GB".format(self.__config["args"].input))
            exit("The following file {} is too large. The maximum size for a single video is 5GB".format(self.__config["args"].input))
        
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
        
        if self.__config["frame_rate"] > 5:
            logging.warning("It appears the frame rate of this video is very low. You can continue, but the images in the Sequence might not render as expected.")
            print("It appears the frame rate of this video is very low. You can continue, but the images in the Sequence might not render as expected.")

        if self.__config["time_warp"] is not None:
            logging.warning("It appears this video was captured in timewarp mode. You can continue, but the images in the Sequence might not render as expected.")
            print("It appears this video was captured in timewarp mode. You can continue, but the images in the Sequence might not render as expected.")

        FileType = ["MP4", "360"]
        if videoData["FileType"].strip() not in FileType:
            logging.critical("The following filetype {} is not supported. Please upload only .mp4 or .360 videos.".format(videoData["FileType"]))
            exit("The following filetype {} is not supported. Please upload only .mp4 or .360 videos.".format(videoData["FileType"]))
        else:
            if videoData["FileType"].strip() == "360":
                if videoData["CompressorName"] == "H.265":
                    logging.critical("This does not appear to be a GoPro .360 file. Please use the .360 video created from your GoPro camera only.")
                    exit("This does not appear to be a GoPro .360 file. Please use the .360 video created from your GoPro camera only.")
        vFileType = os.path.basename(self.__config["args"].input.strip()).split(".")[-1]
        """if vFileType == '360':
            StitchingSoftwares = ["Fusion Studio / GStreamer", "Spherical Metadata Tool"]
            if videoData['StitchingSoftware'].strip() not in StitchingSoftwares:
                logging.critical("Only mp4's stitched using GoPro software are supported. Please use GoPro software to stitch your GoPro 360 videos.")
                exit("Only mp4's stitched using GoPro software are supported. Please use GoPro software to stitch your GoPro 360 videos.")"""
        return vFileType
    
    def __convert360tomp4(self, videoData):
        filename = "{}{}{}.mp4".format(self.__config["imageFolderPath"], os.sep, self.__config["imageFolder"])
        print("Converting 360 video to mp4 video...")

        tracks = videoData['video_field_data']['CompressorNameTrack']
        if (type(tracks) == list) and (len(tracks) == 2):
            tracks[0] = 0 if (tracks[0]-1) < 0 else (tracks[0]-1)
            tracks[1] = 0 if (tracks[1]-1) < 0 else (tracks[1]-1)
            trackmapFirst = "0:{}".format(tracks[0])
            trackmapSecond = "0:{}".format(tracks[1])
        else:
            trackmapFirst = "0:{}".format(0)
            trackmapSecond = "0:{}".format(5)
        
        track0 = os.getcwd() + os.sep + 'track0'
        if os.path.exists(track0):
            shutil.rmtree(track0)
        os.makedirs(track0, exist_ok=True) 
        track5 = os.getcwd() + os.sep + 'track5'
        if os.path.exists(track5):
            shutil.rmtree(track5)
        os.makedirs(track5, exist_ok=True) 

        cmd = [
            "-i",
            self.__config["args"].input,
            "-map", 
            trackmapFirst,
            "-r",
            str(self.__config["frame_rate"]), 
            "-q:v",
            str(self.__config["quality"]),
            track0 + os.sep + "img%d.jpg",
            "-map", 
            trackmapSecond,
            "-r", 
            str(self.__config["frame_rate"]),
            "-q:v", 
            str(self.__config["quality"]), 
            track5 + os.sep + "img%d.jpg"
        ]
        
        output = self._ffmpeg(cmd)

        imgWidth = videoData['video_field_data']['SourceImageWidth']
        if imgWidth == 4096:
            _w = 5376
        elif imgWidth == 2272:
            _w = 3072
        else:
            _w = imgWidth
        
        try:
            if self.__config["args"].max_sphere == None:
                if platform.system() == "Windows":
                    max_sphere = ".{}MAX2sphere{}MAX2sphere.exe".format(os.sep, os.sep)
                else:
                    max_sphere = ".{}MAX2sphere{}MAX2sphere".format(os.sep, os.sep)
            else:
                max_sphere = self.__config["args"].max_sphere.strip()

            t0Images = fnmatch.filter(os.listdir(track0), '*.jpg')
            t5Images = fnmatch.filter(os.listdir(track5), '*.jpg')
            imgCounter = 0
            for img in t0Images:
                if imgCounter < len(t5Images):
                    print("Converting 360 image '{}' to euirectangular".format(img))
                    cmd = [max_sphere, '-w', _w, "track0/{}".format(img), "track5/{}".format(img)]
                    cmd = shlex.split(" ".join(cmd))
                    output = subprocess.run(cmd, capture_output=True)
                    logging.info(output)
                    if output.returncode == 0:
                        #iMG = int(img.replace("_sphere", "").replace("img", "").replace(".jpg", ""))
                        iMG = imgCounter+1
                        Path(track0+os.sep+img).rename(self.__config["imageFolderPath"]+os.sep+"{0}_{1:06d}.jpg".format(self.__config["imageFolder"], iMG))
                    else:
                        raise Exception(output.stderr.decode('utf-8',"ignore"))
                imgCounter = imgCounter + 1
        except Exception as e:
            logging.info(str(e))
            print(str(e))
            exit("Unable to convert 360 deg video.")

        if os.path.exists(track0):
            shutil.rmtree(track0)
        if os.path.exists(track5):
            shutil.rmtree(track5)
        return filename

    def __createDirectories(self):
        if os.path.exists(self.__config["imageFolderPath"]):
            shutil.rmtree(self.__config["imageFolderPath"])
        os.makedirs(self.__config["imageFolderPath"], exist_ok=True) 

    def __breakIntoFrames(self, filename):
        logging.info("Running ffmpeg to extract images...")
        print("Please wait while image extraction is complete.\nRunning ffmpeg to extract images...")
        test_str = ""
        if self.__config["args"].debug is True:
            if "time_warp" in self.__config:
                tw = "-t_{}x".format(self.__config["time_warp"])
            else:
                tw = ""
            test_str = "-q_{}-r_{}fps{}".format(
                self.__config["quality"], 
                self.__config["frame_rate"], tw
            )
        cmd = [
            "-i", filename, 
            "-r", str(self.__config["frame_rate"]), 
            "-q:v", str(self.__config["quality"]), 
            "{}{}{}{}_%06d.jpg".format(
                self.__config["imageFolderPath"], 
                os.sep, 
                self.__config["imageFolder"], 
                test_str
            )
        ]
        output = self._ffmpeg(cmd, 1)

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
                                data['GPSData'].append(ldata)
                                ldata = {}
        for k, v in adata.items():
            data[k] = v
        gpsData.append(data)
        """for gps in gpsData:
            print(gps['GPSDateTime'], len(gps['GPSData']))
        exit()"""
        output = self.__gpsTimestamps(gpsData)
        return {
            "filename": output["filename"],
            "startTime": output["startTime"],
            "video_field_data": videoFieldData
        }

    def __gpsTimestamps(self, gpsData):
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
                start_gps = gpsData[counter]
                #Get Times from metadata
                start_time = datetime.datetime.strptime(start_gps["GPSDateTime"].replace("Z", ""), "%Y:%m:%d %H:%M:%S.%f")
                end_time = start_time+datetime.timedelta(0, 1.0) 
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
        for gps in Timestamps:
            #Get Start Time from metadata
            start_time = gps["GPSDateTime"]
            gps_epoch_seconds = (start_time-t1970).total_seconds()

            if icounter < tlen-1:
                #Get End Time from metadata
                end_time = Timestamps[icounter+1]["GPSDateTime"]
                time_diff = (end_time - start_time).total_seconds()

                #Get Latitude, Longitude and Altitude
                start_latitude = self.latLngToDecimal(gps["GPSLatitude"])
                start_longitude = self.latLngToDecimal(gps["GPSLongitude"])
                start_altitude = self.getAltitudeFloat(gps["GPSAltitude"])

                end_latitude = self.latLngToDecimal(Timestamps[icounter+1]["GPSLatitude"])
                end_longitude = self.latLngToDecimal(Timestamps[icounter+1]["GPSLongitude"])
                end_altitude = self.getAltitudeFloat(Timestamps[icounter+1]["GPSAltitude"])

                gpx_point = gpxpy.gpx.GPXTrackPoint(
                    latitude=start_latitude, 
                    longitude=start_longitude, 
                    time=start_time, 
                    elevation=start_altitude
                )
                gpx_segment.points.append(gpx_point)
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
        filename = self.__saveXmlMetaFile(self.__config["imageFolder"] + "_video.gpx", gpxData)
        return {
            "filename": filename,
            "startTime": Timestamps[0]['GPSDateTime']
        }

    def __extractVideoInformationPre(self, videoFile, Track):
        logging.info("Running exiftool to extract metadata...")
        print("Running exiftool to extract metadata...")

        images = fnmatch.filter(os.listdir(self.__config["imageFolderPath"]), '*.jpg')
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

    def __updateImagesMetadata(self, data):
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
        for img in data['images']:
            if counter < photosLen - 1:
                photo = [data['images'][counter], data['images'][counter + 1]]
                #Get metadata from exiftool
                cmd = ["-ee", "-G3", "-j", "-api", "LargeFileSupport=1", self.__config["imageFolderPath"]+os.sep+photo[0]]
                output = self._exiftool(cmd)
                start_photo = json.loads(output["output"])[0]
                cmd = ["-ee", "-G3", "-j", "-api", "LargeFileSupport=1", self.__config["imageFolderPath"]+os.sep+photo[1]]
                output = self._exiftool(cmd)
                end_photo = json.loads(output["output"])[0]

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
                #Get metadata from exiftool
                cmd = ["-ee", "-G3", "-j", "-api", "LargeFileSupport=1", self.__config["imageFolderPath"]+os.sep+photo[0]]
                output = self._exiftool(cmd)
                start_photo = json.loads(output["output"])[0]

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
                '-GPSSpeed={}'.format(kms),
                '-GPSSpeedRef=k',
                '-GPSImgDirection={}'.format(ext['gps_heading_next_degrees']),
                '-GPSImgDirectionRef=m',
                '-GPSPitch={}'.format(ext['gps_pitch_next_degrees']),
                '-IFD0:Model="{}"'.format(self.removeEntities(data["video_field_data"]["DeviceName"]))
            ]
            if data["video_field_data"]["ProjectionType"] == "equirectangular":
                cmdMetaData.append('-XMP-GPano:StitchingSoftware="{}"'.format(self.removeEntities(data["video_field_data"]["StitchingSoftware"])))
                cmdMetaData.append('-XMP-GPano:SourcePhotosCount="{}"'.format(2))
                cmdMetaData.append('-XMP-GPano:UsePanoramaViewer="{}"'.format("true"))
                cmdMetaData.append('-XMP-GPano:ProjectionType="{}"'.format(self.removeEntities(data["video_field_data"]["ProjectionType"])))
                cmdMetaData.append('-XMP-GPano:CroppedAreaImageHeightPixels="{}"'.format(data["video_field_data"]["SourceImageHeight"]))
                cmdMetaData.append('-XMP-GPano:CroppedAreaImageWidthPixels="{}"'.format(data["video_field_data"]["SourceImageWidth"]))
                cmdMetaData.append('-XMP-GPano:FullPanoHeightPixels="{}"'.format(data["video_field_data"]["SourceImageHeight"]))
                cmdMetaData.append('-XMP-GPano:FullPanoWidthPixels="{}"'.format(data["video_field_data"]["SourceImageWidth"]))
                cmdMetaData.append('-XMP-GPano:CroppedAreaLeftPixels="{}"'.format(0))
                cmdMetaData.append('-XMP-GPano:CroppedAreaTopPixels="{}"'.format(0))
            cmdMetaData.append('-overwrite_original')
            cmdMetaData.append("{}{}{}".format(self.__config["imageFolderPath"], os.sep, photo[0]))
            output = self._exiftool(cmdMetaData)
            counter = counter + 1
            print("Injecting additional metadata to {} is done.".format(photo[0]))
        gpxData = gpx.to_xml()
        gpxFileName = self.__config["imageFolder"] + "_photos.gpx"
        gpxFileName = self.__saveXmlMetaFile(gpxFileName, gpxData)

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
