# GoPro 360 mp4 video to frames

Converts GoPro mp4s with equirectangular projections into single frames with correct metadata.

## Explorer

If you don't / can't run this script locally, our cloud product, Explorer, provides almost all of this scripts functionality in a web app.

* [Explorer app](https://explorer.trekview.org/).
* [Explorer docs](https://guides.trekview.org/explorer/overview).

## Installation

You must have:

* ffmpeg
    * by default we bind to default path, so test by running `ffmpeg` in your cli
* exiftool
    * by default we bind to default path, so test by running `exiftool` in your cli

Installed on you system.

You can then install the required Trek View components:

This repo:

```
$ git clone https://github.com/trek-view/gopro-frame-maker
$ cd gopro-frame-maker
```

### Note for GoPro MAX Users

If you plan to use .360 videos with this script, you must clone our MAX2Sphere script

```
$ git clone https://github.com/trek-view/MAX2sphere
$ cd MAX2sphere
$ make -f Makefile
```

_See MAX2Sphere repo for full install information._

Wait for it to build and then go back to your main directory

```
$ cd ..
```

### Using a virtual environment

To keep things clean on your system, run it in a virtual environment:

```
$ python3 -m venv env
$ source env/bin/activate
$ pip3 install -r requirements.txt
```

## Usage

### Added support to use [config.ini](https://github.com/trek-view/gopro-frame-maker/blob/dev/config.ini) file 
If using config.ini file only videos (1 video in case of max, and 2 videos in case of fusion) needs to pass as the arguments all other flags will be taken from config.ini

### Options

```
$ python3 gfm.py [options] VIDEO_NAME.mp4
```

Options:

* `-r` n sets the frame rate (frames per second) for extraction, default: `5`. Options available:
	* `1`
	* `2` 
	* `5`
* `-q` n sets the extracted quality between 2-6. 1 being the highest quality (but slower processing), default: 1. This is value used for ffmpeg `-q:v` flag. Options available:
	* `1`
	* `2` 
	* `3`
	* `4`
	* `5`
* `-t` enables timewarp mode. You NEED to use this if video was shot in timewarp mode, else telemetry will be inaccurate. The script does not support timewarp mode set to Auto (because it's impossible to determine the capture rate). No default
	* `2x`
	* `5x`
	* `10x`
	* `15x`
	* `30x`
* `-m` custom MAX2Sphere path, default: ./MAX2sphere/MAX2sphere
* `-f` custom ffmpeg install path, default: default binding
* `-n` nadir/watermark logo path and size (between 12 - 20, in increments of 1. see: Nadir/watermark section below for more info) default: none
* `-d` enable debug mode, default: false. If flag is passed, will be set to true.

## Test cases

Our suite of test cases can be downloaded here:

* [Valid video files](https://guides.trekview.org/explorer/developer-docs/sequences/upload/good-test-cases)

### Run Tests

All the tests resides in `tests` folder.

To run all the tests, run:

```
python -m unittest discover tests -p '*_tests.py'
```



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

It is very likely that older cameras are also supported, but we provide no support for these as they have not been tested.

### Test cases

[A full library of sample files for each camera can be accessed here](https://guides.trekview.org/explorer/developer-docs/sequences/capture).

### Video requirements

* Must be shot on GoPro camera
* Must have telemetry (GPS enabled when shooting)

### Logic

The general processing pipeline of gopro-frame-maker is as follows;

![](/docs/gopro-frame-maker-flow.jpg)

[Image source here](https://docs.google.com/presentation/d/1Te7oUaPmlulYsZE6nqITC_sLjfDzDxwTmT5uM_EmXW8/edit#slide=id.p)

[To read how this script works in detail, read this post](https://guides.trekview.org/explorer/developer-docs/sequence-functions/process/gopro-video-telemetry).

### Validation

To ensure the video can be processed, the following metadata check is applied.

**1. Video contains GoPro telemetry**

We check video contains telemetry from GoPro by identifying the following metatag `<TrackN:MetaFormat>gpmd</TrackN:MetaFormat>`. _Note: TrackN where N = track number, which varies between GoPro cameras._ 

For dual GoPro Fisheye videos, this data is in the front video file.

If the script fails this check, you will see an error returned.

### Identify correct pipeline

In order to process the video in the correct flow, the following logic is checked

**Identify GoPro EAC .360**

It is possible to identify .360 files by searching for the following metatag `<Track1:CompressorName>H.265 encoder</Track1:CompressorName>`. _Note: TrackN where N = track number, which varies between GoPro cameras._ 

If true, pass to MAX2Sphere frame pipeline.

**Identify dual GoPro Fisheye**

It is possible to identify dual GoPro fisheyes by checking `ImageWidth` and `ImageHeight` of both videos. They should be either 2 videos = 2704 (w) x 2624 (h) OR 2 videos (w) = 1568 x 1504 (h)

If true, pass to fusion2sphere frame pipeline.

**Identify equirectangular mp4**

For .mp4 videos we can determine video is spherical (equirectangular) if it contains the following metatag `<XMP-GSpherical:ProjectionType>equirectangular</XMP-GSpherical:ProjectionType>`.

If true, pass to equirectangular frame pipeline.

**Identify equirectangular mp4**

Non-spherical mp4s can be identified if no `XMP-GSpherical:ProjectionType` tag is present.

If true, pass to HERO frame pipeline.

### Nadir / watermark

A square file to be used as a nadir (for equirectangular) or watermark (for flat) images can be passed to be used in the image. This feature is useful for adding a custom logo to extracted frame.

Nadir/watermark logo must be:

* <= 5mb
* .png
* square dimensions (with edges > 500 px)

You also need to pass nadir/watermark size a a % of image height. For example, passing `-n /path/to/nadir/logo.png 20` will result in the nadir/watermark having dimensions 20% of image height.

_Example of nadir image height (equirectangular)_

![](/docs/example-nadir-percentage-of-pano.jpeg)

_Example of watermark image height (non-equirectangular)_

![](/docs/example-watermark-percentage-of-photo.jpeg)

#### Examples (MacOS)

##### Extract at a frame rate of 1 FPS

```
$ python3 gfm.py -r 1 samples/GS018422.mp4
```

##### Run with debug mode

```
$ python3 gfm.py -d GS018422.mp4
```

##### Extract frames at lowest quality

```
$ python3 gfm.py -q 5 GS018422.mp4
```

##### Extract from a timewarp video shot at 5x speed

```
$ python3 gfm.py -t 5x GS018422.mp4
```

##### Use a custom ffmpeg path

```
python3 gfm.py -f /Users/dgreenwood/bin/ffmpeg GS018422.mp4
```

##### Use a custom MAX2Sphere path

```
python3 gfm.py -m /Users/dgreenwood/bin/MAX2sphere/MAX2sphere GS018422.mp4
```

##### Add a custom nadir

```
python3 gfm.py -n /Users/dgreenwood/logo/trekview.png -p 12 GS018422.mp4
```

## Support

Join our Discord community and get in direct contact with the Trek View team, and the wider Trek View community.

[Join the Trek View Discord server](https://discord.gg/ZVk7h9hCfw).

## License

The code of this site is licensed under an [MIT License](/LICENSE).
