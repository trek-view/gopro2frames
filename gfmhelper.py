import configparser, subprocess, threading, itertools, argparse, platform, logging, datetime, fnmatch, shutil, shlex, pandas as pd, html, copy, time, json, math, csv, os, re
from colorama import init, deinit, reinit, Fore, Back, Style
from geographiclib.geodesic import Geodesic
from decimal import Decimal, getcontext
from haversine import haversine, Unit
from pathlib import Path
from lxml import etree as ET
from os import walk
import itertools
import gpxpy

class GoProFrameMakerHelper():
    def __init__(self):
        pass

    @staticmethod
    def getListOfTuples(mylist, n):
        args = [iter(mylist)] * n
        return itertools.zip_longest(fillvalue=None, *args)

    @staticmethod
    def removeEntities(text):
        text = re.sub('"', '', html.unescape(text))
        text = re.sub("'", '', html.unescape(text))
        return html.escape(text)

    @staticmethod
    def latLngDecimalToDecimal(latLng):
        ll = latLng.split(" ")
        return float(ll[0]) * (-1 if ll[1].strip() in ['W', 'S'] else 1)

    @staticmethod
    def latLngToDecimal(latLng):
        deg, minutes, seconds, direction = re.split('[deg\'"]+', latLng)
        return (float(deg.strip()) + float(minutes.strip())/60 + float(seconds.strip())/(60*60)) * (-1 if direction.strip() in ['W', 'S'] else 1)

    @staticmethod
    def latLngToDirection(latLng):
        deg, minutes, seconds, direction = re.split('[deg\'"]+', latLng)
        return direction.strip()

    @staticmethod
    def getAltitudeFloat(altitude):
        alt = float(altitude.split(" ")[0])
        return alt

    @staticmethod
    def decimalDivide(num1, num2):
        num1 = Decimal(round(num1, 6))
        num2 = Decimal(round(num2, 6))
        if num2 == 0.0:
            return 0.0
        if num1 == 0.0:
            return 0.0
        num = Decimal(num1 / num2)
        if num == 0.0:
            num = abs(num)
        return round(float(num), 3)

    @staticmethod
    def calculateBearing(lat1, long1, lat2, long2):
        Long = (long2-long1)
        y = math.sin(Long) * math.cos(lat2)
        x = math.cos(lat1)*math.sin(lat2) - math.sin(lat1)*math.cos(lat2)*math.cos(Long)
        brng = math.degrees((math.atan2(y, x)))
        brng = (((brng + 360) % 360))
        return brng

    @staticmethod
    def calculateExtensions(gps, times, positions, etype=1, utype=1):
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

            gps_elevation_change_next_meters = Decimal(end_altitude - start_altitude)
            gps_velocity_east_next_meters_second = GoProFrameMakerHelper.decimalDivide( AC, time_diff ) 
            gps_velocity_north_next_meters_second = GoProFrameMakerHelper.decimalDivide( BC, time_diff )
            gps_velocity_up_next_meters_second = GoProFrameMakerHelper.decimalDivide( gps_elevation_change_next_meters, time_diff )
            gps_speed_next_meters_second = GoProFrameMakerHelper.decimalDivide( distance, time_diff )
            gps_heading_next_degrees = GoProFrameMakerHelper.decimalDivide( compass_bearing, 1 )
            gps_pitch_next_degrees = GoProFrameMakerHelper.decimalDivide( gps_elevation_change_next_meters, distance ) % 360
            gps_distance_next_meters = distance
            gps_speed_next_kmeters_second = GoProFrameMakerHelper.decimalDivide( gps_distance_next_meters, 1000.0  ) #in kms
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

    @staticmethod
    def parseMetadata(xmlFileName):
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
        return {
            'gps_data': gpsData,
            'video_field_data': videoFieldData
        }

    @staticmethod
    def gpsTimestamps(gpsData, videoFieldData):
        
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
        first_start_time = datetime.datetime.strptime(gpsData[0]["GPSDateTime"].replace("Z", ""), "%Y:%m:%d %H:%M:%S.%f")
        final_end_time = datetime.datetime.strptime(gpsData[0]["GPSDateTime"].replace("Z", ""), "%Y:%m:%d %H:%M:%S.%f")
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
                final_end_time = end_time
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
            start_latitude = GoProFrameMakerHelper.latLngToDecimal(gps["GPSLatitude"])
            start_longitude = GoProFrameMakerHelper.latLngToDecimal(gps["GPSLongitude"])
            start_altitude = GoProFrameMakerHelper.getAltitudeFloat(gps["GPSAltitude"])
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
                end_latitude = GoProFrameMakerHelper.latLngToDecimal(Timestamps[icounter+1]["GPSLatitude"])
                end_longitude = GoProFrameMakerHelper.latLngToDecimal(Timestamps[icounter+1]["GPSLongitude"])
                end_altitude = GoProFrameMakerHelper.getAltitudeFloat(Timestamps[icounter+1]["GPSAltitude"])

                ext = GoProFrameMakerHelper.calculateExtensions(
                    gps, 
                    (start_time, end_time, gps_epoch_seconds),
                    (
                        (start_latitude, start_longitude, start_altitude),
                        (end_latitude, end_longitude, end_altitude)
                    ),
                    1, 1
                )
            else:
                ext = GoProFrameMakerHelper.calculateExtensions(
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

        return {
            "gpx_data": gpxData,
            "start_time": Timestamps[0]['GPSDateTime'],
            "end_time": final_end_time
        }


    @staticmethod
    def getConfig():
        #read config file
        values_required = [
            'magick_path',
            'ffmpeg_path',
            'frame_rate',
            'time_warp',
            'quality',
            'nadir_image',
            'nadir_percentage',
            'max_sphere',
            'fusion_sphere',
            'fusion_params',
            'debug'
        ]
        data = {}
        config_path = Path('./config.ini')
        status = False
        if config_path.is_file():
            config = configparser.ConfigParser()
            config.read(str(config_path.resolve()))
            status = True
            for val in values_required:
                if val not in config['DEFAULT']:
                    status = False
                    print("Required value '{}' is missing from config.ini please make sure its present before you use connfig.ini\n".format(val))
            if status == False:
                print('Please make sure all required values are present in config file. Falling back to command line arguments mode.\n')
                time.sleep(2)
            else:
                try:
                    if platform.system() == "Windows":
                        ffmpeg = "ffmpeg.exe"
                    else:
                        ffmpeg = "ffmpeg"

                    default = {
                        'debug': config.getboolean('DEFAULT', 'debug'),
                        'image_magick_path': config['DEFAULT'].get('magick_path'),
                        'ffmpeg_path': config['DEFAULT'].get('ffmpeg_path', ffmpeg),
                        'frame_rate': float(config['DEFAULT'].get('frame_rate', '0.5')),
                        'time_warp': config['DEFAULT'].get('time_warp', '5x'),
                        'quality': int(config['DEFAULT'].get('quality', '1')),
                        'nadir_image': config['DEFAULT'].get('nadir_image'),
                        'nadir_percentage': int(config['DEFAULT'].get('nadir_percentage')),
                        'max_sphere': config['DEFAULT'].get('max_sphere'),
                        'fusion_sphere': config['DEFAULT'].get('fusion_sphere'),
                        'fusion_sphere_params': config['DEFAULT'].get('fusion_params')
                    }
                    status = True
                except:
                    status = False
        return {
            'status': status,
            'config': default
        }

    @staticmethod
    def validateArgs(args):
        status = True
        arguments = {
            'current_directory': Path(),
            'predicted_camera': '',
            'input': '',
            'ffmpeg': '',
            'max_sphere': '',
            'fusion_sphere': '',
            'frame_rate': 0.5,
            'quality': 1,
            'time_warp': None,
            'nadir_image': '',
            'nadir_percentage': '',
            'debug': '',
            'image_magick_path': '',
            'fusion_sphere_params': ''
        }
        errors = []
        info = []
        args_input_len = len(args.input)

        #validating length of input video files
        if(args_input_len > 2):
            errors.append("Only (1) Input files is required in case of max video file and (2) in case of fusion video file.")
            status = False

        #validating input video files for max_sphere
        if(args_input_len == 1): 
            if (args.max_sphere is not None):
                arguments['max_sphere'] = Path(args.max_sphere)
                if(arguments['max_sphere'].is_file() == False):
                    errors.append("{} path does not exists at {}. Please make sure you used correct path!".format(args.max_sphere, str(arguments['max_sphere'].resolve())))
                    status = False
            else:
                info.append("No max2sphere binary is present starting processing without it.")
                status = False
            #camera should be max
            arguments['predicted_camera'] = 'max'

        #validating input video files for fusion_sphere
        #should be only (2) video file
        elif(args_input_len == 2):
            if(args.fusion_sphere is not None):
                arguments['fusion_sphere'] = Path(args.fusion_sphere)
                if(arguments['fusion_sphere'].is_file() == False):
                    errors.append("{} path does not exists at {}. Please make sure you used correct path!".format(args.fusion_sphere, str(arguments['fusion_sphere'].resolve())))
                    status = False
                else:
                    #camera should be fusion
                    arguments['predicted_camera'] = 'fusion'
                    #sort front/back fusion videos
                    front = os.path.basename(args.input[0])[0:4]
                    back = os.path.basename(args.input[1])[0:4]
                    if((front == 'GPFR') and (back == 'GPBK')):
                        args.input = [args.input[0], args.input[1]]
                    elif((front == 'GPBK') and (back == 'GPFR')):
                        args.input = [args.input[1], args.input[0]]
                    else:
                        errors.append("Unidentified video prefix names.")
                        status = False
            else:
                errors.append("Please provide fusion2sphere binary path along with two videos (front/back).")
                status = False
        else:
            errors.append("Please make sure to provide (1) video in case of max camera and (2) in case of fusion camera.")
            status = False


        #validate if the provided input file is actually exists or not.
        if(arguments['predicted_camera'] == 'max'):
            arguments['input'] = [Path(args.input[0])]
            if(arguments['input'][0].is_file()): #input is a list.
                pass
            else:
                errors.append("Input file {} does not exists.".format(args.input[0]))
                status = False

        #validate if the provided input file is actually exists or not.
        elif(arguments['predicted_camera'] == 'fusion'):
            arguments['input'] = [Path(args.input[0]), Path(args.input[1])]
            if((arguments['input'][0].is_file()) and (arguments['input'][1].is_file())): #input is a list.
                pass
            else:
                if((arguments['input'][0].is_file() == False) and (arguments['input'][0].is_file() == False)): #input is a list.
                    errors.append("Input files {}, {} does not exists.".format(args.input[0], args.input[1]))
                elif(arguments['input'][0].is_file()):
                    errors.append("Input file {} does not exists.".format(args.input[0]))
                elif(arguments['input'][1].is_file()):
                    errors.append("Input file {} does not exists.".format(args.input[1]))
                status = False


        #checking is a ffmpeg path is given, if not show the default one.
        if(args.ffmpeg_path is None):
            info.append("Default path for ffmpeg is used as ffmpeg-path is not provided.")
            arguments['ffmpeg'] = Path('.{}FFmpeg{}ffmpeg'.format(os.sep, os.sep))
            if(arguments['ffmpeg'].is_file() == False):
                errors.append("Ffmpeg binary {} does not exists.".format('.{}FFmpeg{}ffmpeg'.format(os.sep, os.sep)))
                status = False
        else:
            arguments['ffmpeg'] = Path(args.ffmpeg_path)
            if(arguments['ffmpeg'].is_file() == False):
                errors.append("Ffmpeg binary {} does not exists.".format(args.ffmpeg_path))
                status = False

        #validating frame rate parameter used for ffmpeg
        if (args.frame_rate is not None):
            frameRate = args.frame_rate
            fropts = [0.5, 1, 2, 5]
            if frameRate not in fropts:
                errors.append("Frame rate {} is not available. Only 0.5, 1, 2, 5 options are available.".format(frameRate))
            else:
                arguments["frame_rate"] = frameRate
        else:
            arguments["frame_rate"] = 0.5

        #validating quality parameter used for ffmpeg
        if (args.quality is not None):
            quality = int(args.quality)
            qopts = [1,2,3,4,5]
            if quality not in qopts:
                errors.append("Extracted quality {} is not available. Only 1, 2, 3, 4, 5 options are available.".format(quality))
                status = False
            else:
                arguments["quality"] = quality
        else:
            arguments["quality"] = 1

        #validating time warp parameter used for ffmpeg
        if (args.time_warp.strip() != ""):
            timeWarp = str(args.time_warp)
            twopts = ["2x", "5x", "10x", "15x", "30x"]
            if timeWarp not in twopts:
                errors.append("Timewarp mode {} not available. Only 2x, 5x, 10x, 15x, 30x options are available.".format(timeWarp))
            else:
                arguments["time_warp"] = timeWarp
        else:
            arguments["time_warp"] = None


        #validating and checking if nadir image exists if present in the arument.
        if (args.nadir_image is not None):
            if(Path(args.nadir_image).is_file() == False):
                errors.append("{} path does not exists at {}. Please make sure you used correct path!".format(args.nadir_image, str(Path(args.nadir_image).resolve())))
                status = False
            else:
                arguments["nadir_image"] = Path(args.nadir_image)
        else:
            arguments["nadir_image"] = ''
        
        #validating nadir percentage.
        if (args.nadir_percentage is not None):
            nadir_percentage = int(args.nadir_percentage)
            if((nadir_percentage >= 12) and (nadir_percentage <= 20)):
                nadir_percentage = nadir_percentage
            else:
                nadir_percentage = 15
            arguments["nadir_percentage"] = nadir_percentage
        else:
            arguments["nadir_percentage"] = 15

        if(args.image_magick_path is not None):
            if(Path(args.image_magick_path).is_file()):
                arguments["image_magick_path"] = Path(args.image_magick_path)
            else:
                errors.append("{} file does not exists.".format(Path(args.fusion_sphere_params)))
                status = False
        else:
            arguments["image_magick_path"] = 'magick'

        if(args.fusion_sphere_params is not None):
            if(Path(args.fusion_sphere_params).is_file()):
                arguments["fusion_sphere_params"] = Path(args.fusion_sphere_params)
            else:
                errors.append("{} file does not exists.".format(Path(args.fusion_sphere_params)))
                status = False
        else:
            if(Path('./params.txt').is_file()):
                arguments["fusion_sphere_params"] = Path('./params.txt')
            else:
                errors.append("{} file does not exists.".format(Path('./params.txt')))
                status = False

        

        return {
            'status': status,
            'args': arguments,
            'errors': errors,
            'info': info
        }
