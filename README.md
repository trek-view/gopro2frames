# GoPro 360 mp4 video to frames

Converts GoPro mp4s with equirectangular projections into single frames with correct metadata.

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

If you plan to use .360 videos with this script, you must clone our MAX2Sphere script

```
$ git clone https://github.com/trek-view/MAX2Sphere
$ cd MAX2Sphere
$ make -f Makefile
```

_See MAX2Sphere repo for full install information._

Wait for it to build and then go back to your main directory

```
$ cd ..
```

To keep things clean on your system, run it in a virtual environment:

```
$ python3 -m venv env
$ source env/bin/activate
$ pip3 install -r requirements.txt
```

## Usage

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
* `-t` enables timewarp mode. You NEED to use this if video was shot in timewarp mode, else telemetry will be inaccurate. You must also pass the timewarp mode used. No default
	* `2x`
	* `5x`
	* `10x`
	* `15x`
	* `30x`
* `-m` custom MAX2Sphere path, default: ./MAX2sphere/MAX2sphere
* `-f` custom ffmpeg install path, default: default binding
* `-n` nadir/watermark logo path and size (between 12 - 20, in increments of 1. see: Nadir/watermark section below for more info) default: none
* `-d` enable debug mode, default: false. If flag is passed, will be set to true.

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

### Test cases

[A full library of sample files for each camera can be accessed here](https://guides.trekview.org/explorer/developer-docs/sequences/capture).

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
$ python3 gfm.py -r 1 GS018422.mp4
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
python3 gfm.py -n /Users/dgreenwood/logo/trekview.png 12 GS018422.mp4
```

## Support

Join our Discord community and get in direct contact with the Trek View team, and the wider Trek View community.

[Join the Trek View Discord server](https://discord.gg/ZVk7h9hCfw).

## License

The code of this site is licensed under an [MIT License](/LICENSE).
