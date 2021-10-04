import subprocess, argparse, platform, logging, datetime, fnmatch, shutil, pandas as pd, shlex, html, copy, time, json, math, csv, os, re
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
        ret = None
        try:
            cmd = command
            if sh == 0:
                cmd = shlex.split(" ".join(cmd))
            output = subprocess.run(cmd, capture_output=True)
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
        command.insert(0, exiftool)
        ret = self.__subprocess(command, sh)
        if ret["error"] is not None:
            logging.critical(ret["error"])
            exit("Error occured while executing exiftool.")
        return ret

    def _ffmpeg(self, command, sh=0):
        if platform.system() == "Windows":
            ffmpeg = "ffmpeg.exe"
        else:
            ffmpeg = "ffmpeg"
        command.insert(0, ffmpeg)
        ret = self.__subprocess(command, sh)
        if ret["error"] is not None:
            logging.critical(ret["error"])
            exit("Error occured while executing ffmpeg, please see logs for more info.")
        return ret

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
            videoData = self.__extractVideoInformationPre(args.input, "Track3")
        else:
            videoData = self.__extractVideoInformationPre(args.input, "Track2")

        fileType = self.__validateVideo(videoData["video_field_data"])
        if fileType == "360":
            self.__config["fileType"] = '360'
            filename = self.__convert360tomp4()
            self.__config["360file"] = filename
            self.__breakIntoFrames(filename)
        else:
            self.__breakIntoFrames(self.__config["args"].input)
        
        videoData = self.__extractVideoInformation(videoData)
        
        self.__processVideoInformation(videoData)

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
    
    def __validateVideo(self, videoData):
        fileStat = os.stat(self.__config["args"].input)
        if fileStat.st_size > 1000000000:
            logging.critical("The following file {} is too large. The maximum size for a single video is 5GB".format(self.__config["args"].input))
            exit("The following file {} is too large. The maximum size for a single video is 5GB".format(self.__config["args"].input))
        
        #Validate Critical Errors
        
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
        
        StitchingSoftwares = ["Fusion Studio / GStreamer", "Spherical Metadata Tool"]
        if videoData['StitchingSoftware'].strip() not in StitchingSoftwares:
            logging.critical("Only mp4's stitched using GoPro software are supported. Please use GoPro software to stitch your GoPro 360 videos.")
            exit("Only mp4's stitched using GoPro software are supported. Please use GoPro software to stitch your GoPro 360 videos.")

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
        return videoData["FileType"].strip()
    
    def __convert360tomp4(self):
        filename = "{}{}{}.mp4".format(os.getcwd(), os.sep, self.__config["imageFolder"])
        print("Converting 360 video to mp4 video...")
        if self.__config["time_warp"] is None:
            trackmap = '0:3'
        else:
            trackmap = '0:2'
        cmd = [
            '-hwaccel', 
            'auto',
            '-hwaccel', 
            'auto', 
            '-init_hw_device', 
            'opencl:0.2', 
            '-filter_hw_device', 
            'opencl0', 
            '-v', 
            'verbose', 
            '-filter_complex', 
            '[0:0]format=yuv420p,hwupload[a] , [0:4]format=yuv420p,hwupload[b], [a][b]gopromax_opencl, hwdownload,format=yuv420p', 
            '-i', 
            self.__config["args"].input, 
            '-c:v', 
            'libx264', 
            '-map_metadata', 
            '-map', 
            trackmap,
            '0',
            '-y',
            filename
        ]
        output = self._ffmpeg(cmd)
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
        videoFieldData = {}
        allGps = []
        check = 0
        nsmap = root[0].nsmap
        for elem in root[0]:
            eltags = elem.tag.split("}")
            nm = eltags[0].replace("{", "")
            tag = eltags[-1]
            if (tag in gpsFields) and (nm == nsmap[Track]):
                allGps.append({tag: elem.text})
            else:
                if tag in videoInfoFields:
                    videoFieldData[tag] = elem.text
        return {
            "allGps": allGps,
            "video_field_data": videoFieldData
        }

    def __getImageSequenceTimestamps(self, start, images, gpsFields, timeData):
        periods = len(images)
        timesBetween = [tdata["GPSDateTime"] for tdata in timeData ]
        ms = int(((100.0/float(self.__config["frame_rate"]))/100.0)*1000.0)
        timestamps = pd.date_range(start=start, periods=periods, closed=None, freq="{}ms".format(ms))
        tData = []
        for t in timestamps:
            z = min(timesBetween, key=lambda x: abs(x - t))
            for tdata in timeData:
                if tdata["GPSDateTime"] == z:
                    tdata["GPSDateTime"] = t
                    tData.append(tdata.copy())
        return pd.DataFrame(tData)
    
    def __createAllGpsGpx(self, data):
        gpx = gpxpy.gpx.GPX()

        # Create first track in our GPX:
        gpx_track = gpxpy.gpx.GPXTrack()
        gpx.tracks.append(gpx_track)

        # Create first segment in our GPX track:
        gpx_segment = gpxpy.gpx.GPXTrackSegment()
        gpx_track.segments.append(gpx_segment)

        for point in data:
            a = self.latLngToDecimal(point["GPSLatitude"])
            b = self.latLngToDecimal(point["GPSLongitude"])
            alt = point["GPSAltitude"].split(" ")[0]
            t = point["GPSDateTime"]
            gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(latitude=a, longitude=b, time=t, elevation=alt))

        gpxData = gpx.to_xml() 

        return self.__saveXmlMetaFile(self.__config["imageFolder"] + "_video.xml", gpxData)

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
            'GPSAltitude'
        ]
        _xmlData = self.__getXMLData(root, videoInfoFields, gpsFields, Track)
        return _xmlData

    def __extractVideoInformation(self, videoFieldData):
        logging.info("Running exiftool to extract metadata...")
        print("Running exiftool to extract metadata...")
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
            'GPSAltitude'
        ]
        images = fnmatch.filter(os.listdir(self.__config["imageFolderPath"]), '*.jpg')
        allGps = videoFieldData["allGps"]
        videoFieldData = videoFieldData["video_field_data"]
        timesBetween = []
        timestamps = []
        gpsData = []
        pData = []
        dateTime = ''
        data = {}
        dataSub = {}
        check = 0
        checkSub = 0
        dlen = len(allGps)
        while check < dlen:
            dtlist = list(allGps[check].items())
            dtlist = dtlist[0]
            if dtlist[0] == "GPSDateTime":
                if len(data) > 0:
                    gpsData.append(data.copy())
                    data = {}
                dateTime = dtlist[1]
                timestamps.append(dateTime)
                data[dateTime] = []
                check = check + 1
            else:
                j = 0
                while j < 3:
                    dlist = list(allGps[check].items())
                    dlist = dlist[0]
                    if dlist[0] == "GPSDateTime":
                        break
                    dataSub[dlist[0]] = dlist[1]
                    check = check + 1
                    j = j + 1
                data[dateTime].append(dataSub.copy())
            if check == dlen:
                gpsData.append(data.copy())
                break
        dlen = len(gpsData)
        diff = int(((100.0/float(self.__config["frame_rate"]))/100.0)*100.0)
        for i in range(0, dlen):
            dlist = list(gpsData[i].items())
            dlist = dlist[0]
            if i < dlen-1:
                delist = list(gpsData[i+1].items())
                delist = delist[0]
                start = datetime.datetime.strptime(dlist[0], "%Y:%m:%d %H:%M:%S.%f")
                timesBetween.append(start)
                end = datetime.datetime.strptime(delist[0], "%Y:%m:%d %H:%M:%S.%f")
                diff = int(((end - start).total_seconds()/float(len(dlist[1])))*1000.0)
                #check this later
                if diff == 0:
                    """zend = end
                    for tbet in timesBetween:
                        if tbet >= end:
                            diff = int(((end - start).total_seconds()/float(len(dlist[1])))*1000.0)
                            break
                        start = tbet
                    print('##', start, end)"""
                    if start == end:
                        start = end
                        diff = int((0.05)*1000.0)
                        end = end+datetime.timedelta(0, 0.05) 
                #print(diff, end, start, len(dlist[1]))
                new = pd.date_range(start=start, end=end, closed='left', freq="{}ms".format(diff))
                ii = 0 
                for n in dlist[1]:
                    dlist[1][ii]['GPSDateTime'] = new[ii]
                    pData.append(dlist[1][ii].copy())
                    ii = ii+1
            else:
                diff = int((0.05)*1000.0)
                new = pd.date_range(start=start, periods=len(dlist[1]), closed='left', freq="{}ms".format(diff))
                ii = 0 
                for n in dlist[1]:
                    dlist[1][ii]['GPSDateTime'] = new[ii]
                    pData.append(dlist[1][ii].copy())
                    ii = ii+1
            i = i+1
        self.__createAllGpsGpx(pData)
        timeData = pd.DataFrame(pData)
        start = datetime.datetime.strptime(timestamps[0], "%Y:%m:%d %H:%M:%S.%f")
        timestamps = self.__getImageSequenceTimestamps(start, images, gpsFields, pData)
        #timestamps.to_csv('./01.csv', sep=',', encoding='utf-8', index=False)
        data = {
            "video_field_data": videoFieldData,
            "timestamps": timestamps,
            "images": images
        }
        return data

    """
       __cammCsv function
       This function will create a csv file containing all the data to create CAMM Telemetry
    """
    #https://github.com/trek-view/basecamp/blob/master/_posts/2021-10-07-calculating-velocity-between-two-sequence-photos.md
    #https://github.com/trek-view/basecamp/blob/master/_posts/2020-01-17-what-direction-are-you-facing.md
    def __cammCsv(self, data):
        print("Starting to create CAMM csv file.")
        gpsData = []
        cammData = []
        for img in data["images"]:
            cmd = ["-ee", "-j", "-G3", "-GPSDateTime", "-GPSLatitude", "-GPSLongitude", "-GPSAltitude", self.__config["imageFolderPath"] + os.sep + img]
            output = self._exiftool(cmd)
            if output["output"] is not None:
                row = json.loads(output["output"])
                if len(row) > 0:
                    row = row[0]
                    gpsData.append({
                        "GPSDateTime": row["Main:GPSDateTime"].replace("Z", ""),
                        "GPSLatitude": row["Main:GPSLatitude"],
                        "GPSLongitude": row["Main:GPSLongitude"],
                        "GPSAltitude": row["Main:GPSAltitude"],
                        "image": img
                    })
            i = 0
            for row in gpsData:
                start = gpsData[i]
                end = None
                dist = 0
                time_diff = 0
                azimuth1 = 0
                t_start = datetime.datetime.strptime(gpsData[i]["GPSDateTime"], "%Y:%m:%d %H:%M:%S.%f")
                d_start = (self.latLngToDecimal(gpsData[i]["GPSLatitude"]), self.latLngToDecimal(gpsData[i]["GPSLongitude"]))  
                if i < (len(gpsData)-1):
                    t_end = datetime.datetime.strptime(gpsData[i+1]["GPSDateTime"], "%Y:%m:%d %H:%M:%S.%f")
                    time_diff = (t_end - t_start).total_seconds()
                    d_end = (self.latLngToDecimal(gpsData[i+1]["GPSLatitude"]), self.latLngToDecimal(gpsData[i+1]["GPSLongitude"]))    
                    dist = haversine(d_start, d_end)
                    brng = Geodesic.WGS84.Inverse(d_start[0], d_start[1], d_end[0], d_end[1])
                    azimuth1 = math.radians(brng['azi1'])
                    azimuth2 = math.radians(brng['azi2'])
                    AC = (math.cos(math.radians(azimuth1))*dist)
                    BC = (math.sin(math.radians(azimuth2))*dist)
                    velocity_east = 0 if time_diff < 1 else AC/time_diff  
                    velocity_north = 0 if time_diff < 1 else BC/time_diff
                    velocity_up = 0 if AC == 0 else BC/AC
                    #print("time_diff: {}, dist: {}, azimuth1: {}, azimuth2: {}, velocity_east: {}, velocity_north: {}, velocity_up: {}".format(time_diff, dist, azimuth1, azimuth2, AC, BC, velocity_up))
                    end = gpsData[i+1]
                else:
                    velocity_east = 0
                    velocity_north = 0
                    velocity_up = 0
                    end = None
                t = datetime.datetime.strptime(row["GPSDateTime"], "%Y:%m:%d %H:%M:%S.%f")
                t1970 = datetime.datetime.strptime("1970:01:01 00:00:00.000000", "%Y:%m:%d %H:%M:%S.%f")
                time_gps_epoch = (t-t1970).total_seconds()
                cammData.append({
                    'file_name': row["image"],
                    'time_gps_epoch': time_gps_epoch,
                    'gps_fix_type': '3D', 
                    'latitude': d_start[0], 
                    'longitude': d_start[1], 
                    'altitude': row["GPSAltitude"], 
                    'horizontal_accuracy': '1', 
                    'vertical_accuracy': '1', 
                    'distance': dist, 
                    'time_difference': time_diff, 
                    'heading': azimuth1, 
                    'velocity_east': velocity_east, 
                    'velocity_north': velocity_north, 
                    'velocity_up': velocity_up, 
                    'speed_accuracy': '0', 
                })
                i = i+1
        pdcammData = pd.DataFrame(cammData)
        pdcammData.to_csv(self.__config["imageFolderPath"] + os.sep + 'camm.csv', sep=',', encoding='utf-8', index=False)
        print("CAMM csv file created.")

    def __processVideoInformation(self, data):
        print("Starting to inject metadata into the images...")
        gpx = gpxpy.gpx.GPX()

        # Create first track in our GPX:
        gpx_track = gpxpy.gpx.GPXTrack()
        gpx.tracks.append(gpx_track)

        # Create first segment in our GPX track:
        gpx_segment = gpxpy.gpx.GPXTrackSegment()
        gpx_track.segments.append(gpx_segment)
        i = 0
        #print('########', len(data["images"]), len(data["timestamps"]))
        for img in data["images"]:
            image = img
            img = data["timestamps"].iloc[i].copy()
            img["image"] = image
            logging.info("# image: {}, GPSDateTime: {}, GPSLatitude: {}, GPSLongitude: {}, GPSAltitude: {}".format(img["image"], img["GPSDateTime"], img["GPSLatitude"], img["GPSLongitude"], img["GPSAltitude"]))
            GPSDateTime = datetime.datetime.strftime(img["GPSDateTime"], "%Y:%m:%d %H:%M:%S.%f")
            tt = GPSDateTime.split(".")
            ttz = GPSDateTime.split(" ")
            alt = img["GPSAltitude"].split(" ")[0]
            latRef = self.latLngToDirection(img["GPSLatitude"])
            lngRef = self.latLngToDirection(img["GPSLongitude"])
            altRef = 0 if float(alt) > 0.0 else -1
            cmdMetaData = [
                '-DateTimeOriginal="{0}Z"'.format(self.removeEntities(GPSDateTime)),
                '-SubSecTimeOriginal="{0}"'.format(self.removeEntities(tt[1])),
                '-SubSecDateTimeOriginal="{0}Z"'.format(self.removeEntities(".".join(tt))),
                '-IFD0:Model="{}"'.format(self.removeEntities(data["video_field_data"]["DeviceName"])),
            ]
            if data["video_field_data"]["ProjectionType"] == "equirectangular0":
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
            cmdMetaData.append("{}{}{}".format(self.__config["imageFolderPath"], os.sep, img["image"]))
            output = self._exiftool(cmdMetaData)
            i = i + 1
            a = self.latLngToDecimal(img["GPSLatitude"])
            b = self.latLngToDecimal(img["GPSLongitude"])
            alt = img["GPSAltitude"].split(" ")[0]
            t = img["GPSDateTime"]
            gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(latitude=a, longitude=b, time=t, elevation=alt))
        gpxData = gpx.to_xml() 
        gpxFileName = self.__config["imageFolder"] + "_photos.gpx"
        gpxFileName = self.__saveXmlMetaFile(gpxFileName, gpxData)
        if gpxFileName is None:
            exit("Unable to save gpx file.")
        cmd = ["-geotag", gpxFileName, "'-geotime<${subsecdatetimeoriginal}'", '-overwrite_original', self.__config["imageFolderPath"]]
        output = self._exiftool(cmd)

        self.__cammCsv(data)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str, help="Input a valid video file.")
    parser.add_argument("-r", "--frame-rate", type=int, help="Sets the frame rate (frames per second) for extraction, default: 5.", default=5)
    parser.add_argument("-t", "--time-warp", type=str, help="Set time warp mode for gopro. available values are 2x, 5x, 10x, 15x, 30x")
    parser.add_argument("-q", "--quality", type=int, help="Sets the extracted quality between 2-6. 1 being the highest quality (but slower processing), default: 1. This is value used for ffmpeg -q:v flag. ", default=1)
    parser.add_argument("-d", "--debug", action='store_true', help="Enable debug mode, default: off.")
    args = parser.parse_args()
    dateTimeCurrent = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    goProMp4 = TrekViewGoProMp4(args, dateTimeCurrent)
    exit("Extraction complete, you can see your images now.")
