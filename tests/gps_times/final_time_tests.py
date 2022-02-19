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

import unittest

class TestGpsFinalTime(unittest.TestCase):

    def setUp(self):
        self.current_directory = os.path.abspath(os.path.dirname(__file__))
        video_xml = "{}{}{}{}{}".format(self.current_directory, os.sep, 'data', os.sep, 'video.xml')
        self.metadata = GoProFrameMakerHelper.parseMetadata(video_xml)
        self.metadata_gpx = GoProFrameMakerHelper.gpsTimestamps(self.metadata['gps_data'], self.metadata['video_field_data'])
    
    def test_check_gps_key_presence(self):
        metadata_keys = list(self.metadata.keys())
        video_field_data_keys = list(self.metadata['video_field_data'].keys())

        #self.metadata
        self.assertIsInstance(self.metadata, dict) #check if video metadata is of dict type.
        self.assertIn('gps_data', metadata_keys) #check if video metadata has `gps_data` value in it.
        self.assertIn('video_field_data', metadata_keys) #check if video metadata has `video_field_data` value in it.

        #self.metadata['gps_data']
        self.assertIsInstance(self.metadata['gps_data'], list) #check if video metadata gps_data is of list type.
        self.assertTrue(len(self.metadata['gps_data']) > 1) #check if video metadata gps_data has value in it.
        

        #self.metadata['video_field_data']
        self.assertIsInstance(self.metadata['video_field_data'], dict) #check if video metadata video_field_data is of dict type.
        self.assertIn('ProjectionType', video_field_data_keys) #check if video metadata has `ProjectionType` value in it.
        self.assertIn('StitchingSoftware', video_field_data_keys) #check if video metadata has `StitchingSoftware` value in it.
        self.assertIn('MetaFormat', video_field_data_keys) #check if video metadata has `MetaFormat` value in it.
        self.assertIn('CompressorName', video_field_data_keys) #check if video metadata has `CompressorName` value in it.
        self.assertIn('CompressorNameTrack', video_field_data_keys) #check if video metadata has `CompressorNameTrack` value in it.
        self.assertIn('FileSize', video_field_data_keys) #check if video metadata has `FileSize` value in it.
        self.assertIn('FileType', video_field_data_keys) #check if video metadata has `FileType` value in it.
        self.assertIn('FileTypeExtension', video_field_data_keys) #check if video metadata has `FileTypeExtension` value in it.
        self.assertIn('Duration', video_field_data_keys) #check if video metadata has `Duration` value in it.
        self.assertIn('DeviceName', video_field_data_keys) #check if video metadata has `DeviceName` value in it.
        self.assertIn('SourceImageWidth', video_field_data_keys) #check if video metadata has `SourceImageWidth` value in it.
        self.assertIn('SourceImageHeight', video_field_data_keys) #check if video metadata has `SourceImageHeight` value in it.
        self.assertIn('VideoFrameRate', video_field_data_keys) #check if video metadata has `VideoFrameRate` value in it.
        print('Duration', self.metadata['video_field_data']['Duration'])

    def test_check_gps_gpx_data(self):
        metadata_gpx_keys = list(self.metadata_gpx.keys())
        
        print(self.metadata_gpx['start_time'], self.metadata_gpx['end_time'], self.metadata_gpx['end_time'] - self.metadata_gpx['start_time'])
        
        #self.metadata_gpx
        self.assertIsInstance(self.metadata_gpx, dict) #check if video metadata_gpx is of dict type.
        self.assertIn('gpx_data', metadata_gpx_keys) #check if video metadata_gpx has `gpx_data` value in it.
        self.assertIn('start_time', metadata_gpx_keys) #check if video metadata_gpx has `start_time` value in it.
        gpx_file = "{}{}{}{}{}".format(self.current_directory, os.sep, 'data', os.sep, 'video.gpx')
        with open(gpx_file, "w") as f:
            f.write(self.metadata_gpx['gpx_data'])
            f.close()


if __name__ == '__main__':
    unittest.main()


"""

assertEqual(a, b)
assertNotEqual(a, b)
assertTrue(x)
assertFalse(x)
assertIs(a, b)
assertIsNot(a, b)
assertIsNone(x)
assertIsNotNone(x)
assertIn(a, b)
assertNotIn(a, b)
assertIsInstance(a, b)
assertNotIsInstance(a, b)

"""


# python -m unittest discover tests -p '*_tests.py'
