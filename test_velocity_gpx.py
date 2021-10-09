import subprocess, itertools, argparse, platform, logging, datetime, fnmatch, shutil, pandas as pd, shlex, html, copy, time, json, math, csv, os, re
from lxml import etree

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str, help="Input a valid gpx file.")

    args = parser.parse_args()
    tree = etree.parse(args.input)
    root = tree.getroot()
    nsmap = root[0].nsmap
    for el in root[0][0]:
        for ell in el[2]:
            tag = ell.tag.strip()
            value = ell.text.strip()
            time = 0.0
            east = 0.0
            north = 0.0
            speed = 0.0
            #print(tag, value)
            if tag == "gps_epoch_seconds":
                time = float(value)
            if tag == "gps_velocity_east_next_meters_second":
                east = float(value)
            if tag == "gps_velocity_north_next_meters_second":
                north = float(value)
            if tag == "gps_speed_next_meters_second":
                speed = float(value)
            print("time: {}, east_velocity: {}, north_velocity, speed: {}, east>speed: {}, north>speed: {}".format(time, east, north, speed, east > speed, north > speed))
