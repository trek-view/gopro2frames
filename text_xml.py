from lxml import etree
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
            print(e)
            #print(e.stderr.decode('utf-8',"ignore"))
            #print(e)
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


def getGPSw(el):
    data = {"GPSDateTime": "", "GPSData":[]}
    if el == None:
        return None
    else:
        data["GPSDateTime"] = el.text
    for i in range(0, 500):
        el = el.getnext()
        if el == None:
            break
        if el.tag == "{http://ns.exiftool.org/QuickTime/Track3/1.0/}GPSDateTime":
            break
        if el.tag == "{http://ns.exiftool.org/QuickTime/Track3/1.0/}GPSLatitude":
            data["GPSData"].append({"GPSLatitude": el.text})
        if el.tag == "{http://ns.exiftool.org/QuickTime/Track3/1.0/}GPSLongitude":
            data["GPSData"].append({"GPSLongitude": el.text})
        if el.tag == "{http://ns.exiftool.org/QuickTime/Track3/1.0/}GPSAltitude":
            data["GPSData"].append({"GPSAltitude": el.text})
    return data



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", type=str, help="Please input a valid video file.")
    args = parser.parse_args()
    if (args.input is not None):
        tkvc = TrekviewCommand()
        output = tkvc._exiftool(["-ee", "-G3", "-api", "LargeFileSupport=1", "-X", args.input])
        if output.returncode == 0:
            vfx = "VIDEO_META0.xml"
            with open(vfx, "w") as f:
                f.write(output.stdout.decode('utf-8',"ignore"))
                f.close()
                data = []
                tree = etree.parse(vfx)
                root = tree.getroot()
                time.sleep(3)
                time.sleep(3)
                for el in root[0]:
                    if el.tag == "{http://ns.exiftool.org/QuickTime/Track3/1.0/}GPSDateTime":
                        data = getGPSw(el)
                        if data is not None:
                            for d in data["GPSData"]:
                                k, v = list(d.items())[0]
                                print("DateTime: {}, {}:{}", data["GPSDateTime"], k, v)
