# GoPro 360 mp4 video to frames

Converts GoPro mp4s with equirectangular projections into single frames with correct metadata.

## Installation

```
pip install -r requirements.txt
```

## Usage

### Camera support

This video only accepts mp4 videos shot on a GoPro cameras.

It supports both 360 and non-360 videos. In the case of 360 videos, these must be processed by GoPro Software to final mp4 versions.

This script has currently been tested with the following GoPro cameras:

* GoPro HERO
	* HERO 8
	* HERO 9
	* HERO 10
* GoPro MAX
* GoPro Fusion

### Video requirements

* Must be shot on GoPro camera
* Must have telemetry (GPS enabled when shooting)

### Validation

To ensure the video can be processed, the following checks are applied.

**Determine projection type**

For .mp4 videos we can determine video is spherical (equirectangular) if it contains the following metatag `<XMP-GSpherical:ProjectionType>equirectangular</XMP-GSpherical:ProjectionType>`.

**If contains GoPro telemetry**

Once projection type (360/non-360) has been determined, we next check it contains telemetry from GoPro by identifying the following metatag `<TrackN:MetaFormat>gpmd</TrackN:MetaFormat>`. _Note: TrackN where N = track number, which varies between GoPro cameras._ 

If the script fails any of these checks, you will see an error returned.

### Logic

[To read how this script works, read this](https://guides.trekview.org/explorer/developer-docs/sequence-functions/process/gopro-video-telemetry).

### Options

```
$ gopro-frame-maker.py [options] VIDEO_NAME.mp4
```

Options:

* -r n sets the frame rate (frames per second) for extraction, default: `5`. Options available:
	* `1`
	* `2` 
	* `5`
* -q n sets the extracted quality between 2-6. 1 being the highest quality (but slower processing), default: 1. This is value used for ffmpeg `-q:v` flag. Options available:
	* `1`
	* `2` 
	* `3`
	* `4`
	* `5`
* - t enables timewarp mode. You NEED to use this if video was shot in timewarp mode, else telemetry will be inaccurate. You must also pass the timewarp mode used. No default
	* `2x`
	* `5x`
	* `10x`
	* `15x`
	* `30x`
* -d enable debug mode, default: false. If flag is passed, will be set to true.

#### Examples (MacOS)

##### Extract at a frame rate of 1 FPS

```
$ gopro-frame-maker.py -r 1 GS018422.mp4
```

##### Run with debug mode

```
$ gopro-frame-maker.py -d GS018422.mp4
```

##### Extract frames at lowest quality

```
$ gopro-frame-maker.py -q 5 GS018422.mp4
```

##### Extract from a timewarp video shot at 5x speed

```
$ gopro-frame-maker.py -t 5x GS018422.mp4
```

## How it works

The following describes how the script works.

### Overview of GPMF

GoPro reports telemetry in it's own metadata format called gpmf (GoPro metadata format).

GMPF is reported in one of the video tracks.  Different GoPro cameras/modes report telemetry in different tracks. You can identify which track the telemetry is held in by identifying track with MetaFormat=gpmd. e.g.

* Fusion: `<Track3:MetaFormat>gpmd</Track3:MetaFormat>`
* Max:
	* Spherical Video `<Track3:MetaFormat>gpmd</Track3:MetaFormat>`
	* Spherical Timewarp `<Track2:MetaFormat>gpmd</Track2:MetaFormat>`

### Step 1: Extract frames

Using ffmpeg:

```
ffmpeg -i VIDEO.mp4 -r 5 -q:v 1 img%d.jpg
```

Where -r is framerate (FPS) and -q:v is quality (1 being the highest).

### Step 2: Setting the frame (photo) times

#### First frame (all modes)

To assign first photo time, we use the first GPSDateTime value reported in telemetry and assign it to photo time fields as follows:

<table class="tableizer-table">
<thead><tr class="tableizer-firstrow"><th>Video metadata field extracted</th><th>Example extracted</th><th>Image metadata field injected</th><th>Example injected</th></tr></thead><tbody>
 <tr><td>TrackN:GPSDateTime</td><td>2020:04:13 15:37:22.444</td><td>DateTimeOriginal</td><td>2020:04:13 15:37:22Z</td></tr>
 <tr><td>TrackN:GPSDateTime</td><td>2020:04:13 15:37:22.444</td><td>SubSecTimeOriginal</td><td>444</td></tr>
 <tr><td>TrackN:GPSDateTime</td><td>2020:04:13 15:37:22.444</td><td>SubSecDateTimeOriginal</td><td>2020:04:13 15:37:22.444Z</td></tr>
</tbody></table>

Example exiftool command to write these values:

```
exiftool DateTimeOriginal:"2020:04:13 15:37:22Z" SubSecTimeOriginal:"444" SubSecDateTimeOriginal: "2020:04:13 15:37:22.444Z"
```

#### Other frames (normal mode)

Now we need to assign time to other photos. To do this we simply order the photos in ascending numerical order (as we number them sequentially when extracting frames).

We always extract videos at a fixed frame rate based on transport type. Therefore, we really only need to know the video start time, to determine time of first photo. From there we can incrementally add time based on extraction rate (e.g. photo 2 is 0.2 seconds later than photo one where framerate is set at extraction as 5 FPS).

<table class="tableizer-table">
<thead><tr class="tableizer-firstrow"><th>Extraction Frame rate</th><th>Photo spacing (sec)</th></tr></thead><tbody>
 <tr><td>1</td><td>1</td></tr>
 <tr><td>2</td><td>0.5</td></tr>
 <tr><td>5</td><td>0.2</td></tr>
</tbody></table>

#### Other frames (timewarp mode)

Timewarp is a GoPro mode that speeds up the video (e.g. when set a 5x every second of video is 5 seconds of footage).

We therefore explicitly ask use if video was shot in timewarp mode and the settings used (there is no easy way to determine this automatically).

<table class="tableizer-table">
<thead><tr class="tableizer-firstrow"><th>Timewarp mode</th><th>Each photo true time (sec) @1 FPS</th><th>Each photo true time (sec) @2 FPS</th><th>Each photo true time (sec) @5 FPS</th></tr></thead><tbody>
 <tr><td>2x</td><td>2</td><td>1</td><td>0.4</td></tr>
 <tr><td>5x</td><td>5</td><td>2.5</td><td>1</td></tr>
 <tr><td>10x</td><td>10</td><td>5</td><td>2</td></tr>
 <tr><td>15x</td><td>15</td><td>7.5</td><td>3</td></tr>
 <tr><td>30x</td><td>30</td><td>15</td><td>6</td></tr>
</tbody></table>

To give an example, lets say first photo gets assigned first GPS time = 00:00:01.000 and we extract photos at 5FPS for timewarp mode 30x. in this case second photo has time 00:00:01.000 +6 secs.

### Step 3: Calculating GPS

GoPro reports telemetry at different time intervals, and not every GPS position recorded has a time.

* ~ 18 Hz (up to 18 measurements per second) GPS position (lat/lon/alt/spd)
* 1 Hz (1 measurements per second, but not exactly 1 second apart) GPS timestamps
* 1 Hz (always at same interval as GPS timestamps) GPS accuracy (cm) and fix (2d/3d)

[You can see examples of these values in real GoPro telemetry here](https://github.com/trek-view/gopro-metadata).

Therefore up to 18 points have no time between GPS timestamps being reported. The number of points reported between times also varies based on mode/GPS signal (when GPS signal low, this number might be a lot lower).

Therefore, we first create times for all points noted in the telemetry.

To do this we calculate how many points there are between each time interval. Based on the number of points, we then calculate time.

For example, if GPSDateTime 1 = 1:00:00.000 and GPSDateTime 2 = 1:00:01.000 and there are 9 points reported between these two time, we know each point is about .100 second apart so times for points will be 1:00:00.000, 1:00:00.100. 1:00:00.200, ... 1:00:00.900.

**A note on final points reported in GPMF**

At the end of the GoPro telemetry there is not a final time. That is, some GPS points continue beyond final reported time (usually 3 or 4). In this case, we calculate the final GPS timestamp by adding +1 second onto last GoPro reported timestamp, and then calculate points inbetween in exactly the same way as before.

There files are written into a GPX file.

```
<trkseg>
	<trkpt lat="51.27254444444444" lon="-0.8459694444444444">
		<ele>82.008</ele>
		<time>2021-09-04T07:24:07.744000Z</time>
	</trkpt>
	<trkpt...
      ...
</trkseg>

```

### Step 4: Calculating additional telemetry

The following entries are also created in the gpx file:

<table class="tableizer-table">
<thead><tr class="tableizer-firstrow"><th>Name</th><th>Field in telemtry</th><th>Value</th><th>Image metadata (or fixed value)</th></tr></thead><tbody>
 <tr><td>GPS Epoch</td><td>gps_epoch</td><td>seconds</td><td>time converted to epoch</td></tr>
 <tr><td>GPS Fix Type</td><td>gps_fix_type</td><td> </td><td>Either 2 or 3 (reported in GoPro GPSMeasureMode field as NDimensional Measurement)</td></tr>
 <tr><td>Vertical Accuracy</td><td>gps_vertical_accuracy</td><td>meters</td><td>reported in GoPro GPSHPositioningError</td></tr>
 <tr><td>Horizontal Accuracy</td><td>gps_horizontal_accuracy</td><td>meters</td><td>reported in GoPro GPSHPositioningError</td></tr>
 <tr><td>Velocity East</td><td>gps_velocity_east_next</td><td>meters/second</td><td>Calculated using GPS lat,lon position/time between this an next photo. For last position, is always 0.</td></tr>
 <tr><td>Velocity North</td><td>gps_velocity_north_next</td><td>meters/second</td><td>Calculated using GPS lat,lon position/time between this an next photo. For last position, is always 0.</td></tr>
 <tr><td>Velocity Up</td><td>gps_velocity_up_next</td><td>meters/second</td><td>Calculated using GPS alt position/time between this and next photo. For last position, is always 0.</td></tr>
 <tr><td>Speed Accuracy</td><td>gps_speed_accuracy</td><td>meters/second</td><td>Always '0.1' (fixed)</td></tr>
 <tr><td>Speed</td><td>gps_speed_next</td><td>meters/second</td><td>Calculated using GPS lat,lon position/time between this an next photo. For last position, is always 0.</td></tr>
 <tr><td>Azimuth (heading)</td><td>gps_azimuth_next</td><td>degrees</td><td>Calculated using GPS lat,lon position between this an next photo. For last position, is always 0.</td></tr>
  <tr><td>Pitch</td><td>gps_pitch_next</td><td>degrees</td><td>Calculated using GPS alt position between this an next photo. For last position, is always 0.</td></tr>
 <tr><td>Distance Meters</td><td>gps_distance_next</td><td>meters</td><td>Calculated using GPS lat,lon position between this an next photo. For last position, is always 0.</td></tr>
 <tr><td>Distance Time</td><td>gps_time_next</td><td>seconds</td><td>Calculated using GPS lat,lon position between this an next photo. For last position, is always 0.</td></tr>
</tbody></table>

They are reported in the gpx like so:

```
<trkseg>
	<trkpt lat="51.27254444444444" lon="-0.8459694444444444">
		<ele>82.008</ele>
		<time>2021-09-04T07:24:07.744000Z</time>
		<extensions>
			<gps_epoch>X</gps_epoch>
			<gps_fix_type>X</gps_fix_type>
			<gps_vertical_accuracy>X</gps_vertical_accuracy>
			<gps_horizontal_accuracy>X</gps_horizontal_accuracy>
			<gps_velocity_east_next>X</gps_velocity_east_next>
			<gps_velocity_north_next>X</gps_velocity_north_next>
			<gps_velocity_up_next>X</gps_velocity_up_next>
			<gps_speed_accuracy>1</gps_speed_accuracy>
			<gps_speed_next/>X</gps_speed_next/>
			<gps_azimuth_next>X</gps_azimuth_next>
			<gps_pitch_next>X</gps_pitch_next>
			<gps_distance_next>X</gps_distance_next>
			<gps_time_next>X</gps_time_next>
		</extensions>
		</xsd:sequence>
	</trkpt>
	<trkpt...
      ...
</trkseg>

```

### Step 5: Setting the photo GPS

Now we can use the photo time and GPS positions / times to geotag the photos:

#### All frames (all modes)

[We can use Exiftool's geotag function to add GPS data (latitude, longitude, altitude)](https://exiftool.org/geotag.html).

```
exiftool -Geotag a.log "-Geotime<SubSecDateTimeOriginal" dir

```

This will write the following fields into the photos

<table class="tableizer-table">
<thead><tr class="tableizer-firstrow"><th>Image metadata field injected</th><th>Example injected</th></tr></thead><tbody>
 <tr><td>GPS:GPSDateStamp</td><td>2020:04:13</td></tr>
 <tr><td>GPS:GPSTimeStamp</td><td>15:37:22.444</td></tr>
 <tr><td>GPS:GPSLatitude</td><td>51 deg 14' 54.51"</td></tr>
 <tr><td>GPS:GPSLatitudeRef</td><td>North</td></tr>
 <tr><td>GPS:GPSLongitude</td><td>16 deg 33' 55.60"</td></tr>
 <tr><td>GPS:GPSLongitudeRef</td><td>West</td></tr>
 <tr><td>GPS:GPSAltitudeRef</td><td>Above Sea Level</td></tr>
 <tr><td>GPS:GPSAltitude</td><td>157.641 m</td></tr>
</tbody></table>

### Step 6: Create photo GPX

This is identical to step 4, however, the new GPS values from exiftool are used for calculations. This means the number of gps points in the gpx matches the number of photos. In the case of the following fixed fields, the values should be set as follows:

* gps_fix_type = 3
* gps_vertical_accuracy = 0.1
* gps_horizontal_accuracy = 0.1
* gps_speed_accuracy = 0.1
			
### Step 7: Write additional metadata to photo

#### GPX fields

Exiftool is unable to write all the custom fields in the video gpx created at step 4.

Now we can use the photo gpx file to assign the following values"

* gps_speed_next = GPSSpeed (speed converted into km/h)
* GPSSpeedRef = k
* gps_azimuth_next = GPSImgDirection (in degrees)
* GPSImgDirectionRef = m
* gps_pitch_next = GPSPitch

#### Camera data

<table class="tableizer-table">
<thead><tr class="tableizer-firstrow"><th>Video metadata field extracted</th><th>Example extracted</th><th>Image metadata field injected</th><th>Example injected</th></tr></thead><tbody>
 <tr><td>Trackn:DeviceName</td><td>GoPro Max</td><td>IFD0:Model</td><td>GoPro Max</td></tr>
</tbody></table>

### Spherical metadata (equirectangular videos only)

<table class="tableizer-table">
<thead><tr class="tableizer-firstrow"><th>Video metadata field extracted</th><th>Example extracted</th><th>Image metadata field injected</th><th>Example injected</th></tr></thead><tbody>
 <tr><td>XMP-GSpherical:StitchingSoftware</td><td>Spherical Metadata Tool</td><td>XMP-GPano:StitchingSoftware</td><td>Spherical Metadata Tool</td></tr>
 <tr><td>&nbsp;</td><td>&nbsp;</td><td>XMP-GPano:SourcePhotosCount</td><td>2</td></tr>
 <tr><td>&nbsp;</td><td>&nbsp;</td><td>XMP-GPano:UsePanoramaViewer</td><td>TRUE</td></tr>
 <tr><td>XMP-GSpherical:ProjectionType</td><td>equirectangular</td><td>XMP-GPano:ProjectionType</td><td>equirectangular</td></tr>
 <tr><td>Track1:SourceImageHeight</td><td>2688</td><td>XMP-GPano:CroppedAreaImageHeightPixels</td><td>2688</td></tr>
 <tr><td>Track1:SourceImageWidth</td><td>5376</td><td>XMP-GPano:CroppedAreaImageWidthPixels</td><td>5376</td></tr>
 <tr><td>Track1:SourceImageHeight</td><td>2688</td><td>XMP-GPano:FullPanoHeightPixels</td><td>2688</td></tr>
 <tr><td>Track1:SourceImageWidth</td><td>5376</td><td>XMP-GPano:FullPanoWidthPixels</td><td>5376</td></tr>
 <tr><td>&nbsp;</td><td>&nbsp;</td><td>XMP-GPano:CroppedAreaLeftPixels</td><td>0</td></tr>
 <tr><td>&nbsp;</td><td>&nbsp;</td><td>XMP-GPano:CroppedAreaTopPixels</td><td>0</td></tr>
</tbody></table>

Note, some spatial fields are always fixed (e.g. XMP-GPano:SourcePhotosCount b/c GoPro 360 cameras only have 2 lenses), so no video metadata field needs to be extracted and injected.

### Step 8: Done

You now have:

* a set of geotagged .jpg photos in a directory (`VIDEONAME_DATETIME`)
* a video gpx (step 4) in the same directory (VIDEONAME_video.gpx)
* a photo gpx (step 6) in the same directory (VIDEONAME_frames.gpx)

## Support

Join our Discord community and get in direct contact with the Trek View team, and the wider Trek View community.

[Join the Trek View Discord server](https://discord.gg/ZVk7h9hCfw).

## License

The code of this site is licensed under an [MIT License](/LICENSE).