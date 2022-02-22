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
$ python3 gfm.py VIDEO_NAME.mp4
```

You can set all opitons in the [`config.ini`] file.

The file has the following structure:

```
[DEFAULT]
magick_path=
ffmpeg_path=
frame_rate=
time_warp=
quality=
logo_image=
logo_percentage=
debug=
```

* `magick_path`: path to imagemagick
	* default (if left blank): assumes imagemagick is installed globally
* `ffmpeg_path` (if left blank): path to ffmpeg
	* default: assumes ffmpeg is installed globally
* `frame_rate`: sets the frame rate (frames per second) for extraction,
	* default: `1`
* `quality`: sets the extracted quality between 1-6. 1 being the highest quality (but slower processing). This is value used for ffmpeg `-q:v` flag.
	* default: `1`
* `time_warp`: You NEED to use this if video was shot in timewarp mode, else telemetry will be inaccurate. The script does not support timewarp mode set to Auto (because it's impossible to determine the capture rate). Set the timewarp speed used when shooting in this field, either `2x`, `5x`, `10x`, `15x`, `30x`
	* default: blank (not timewarp)
* `logo_image`: Path to logofile used for nadir / watermark
	* default: blank (do not add logo)
* `logo_percentage`: overlay size of nadir / watermark between 8 - 20, in increments of 1.
	* default: 12 (only used if `logo_image` set)
* `debug`: enable debug mode. True of false
	* Default: `FALSE`

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

This scripte only accepts videos:

* Must be shot on GoPro camera
* Must have telemetry (GPS enabled when shooting)

It supports both 360 and non-360 videos. In the case of 360 videos, these must be processed by GoPro Software to final mp4 versions.

This script has currently been tested with the following GoPro cameras:

* GoPro HERO
	* HERO 8
	* HERO 9
	* HERO 10
* GoPro MAX
* GoPro Fusion

It is very likely that older cameras are also supported, but we provide no support for these as they have not been tested.

### Logic

The general processing pipeline of gopro-frame-maker is as follows;

![](/docs/gopro-frame-maker-flow.jpg)

[Image source here](https://docs.google.com/drawings/d/1i6givGQnGsu7dW2fLt3qVSWaHDiP0TCciY_DtY5_mc4/edit)

[To read how this script works in detail, please read this post](/docs/LOGIC.md).

### Test cases

[A full library of sample files for each camera can be accessed here](https://guides.trekview.org/explorer/developer-docs/sequences/capture).

#### Examples (MacOS)

##### Extract at a frame rate of 1 FPS

```
[DEFAULT]
magick_path=
ffmpeg_path=
frame_rate= 1
time_warp=
quality= 1
logo_image=
logo_percentage=
debug=
```

```
$ python3 gfm.py samples/GS018422.mp4
```

##### Run with debug mode

```
[DEFAULT]
magick_path=
ffmpeg_path=
frame_rate= 1
time_warp=
quality= 1
logo_image=
logo_percentage=
debug=TRUE
```

```
$ python3 gfm.py GS018422.mp4
```

##### Extract frames at lowest quality

```
[DEFAULT]
magick_path=
ffmpeg_path=
frame_rate= 1
time_warp=
quality= 6
logo_image=
logo_percentage=
debug=TRUE
```

```
$ python3 gfm.py GS018422.mp4
```

##### Extract from a timewarp video shot at 5x speed

```
[DEFAULT]
magick_path=
ffmpeg_path=
frame_rate= 1
time_warp= 5x
quality= 1
logo_image=
logo_percentage=
debug=TRUE
```

```
$ python3 gfm.py -t 5x GS018422.mp4
```

##### Use a custom ffmpeg path

```
[DEFAULT]
magick_path=
ffmpeg_path= /Users/dgreenwood/bin/ffmpeg
frame_rate= 1
time_warp= 
quality= 1
logo_image=
logo_percentage=
debug=TRUE
```

```
python3 gfm.py GS018422.mp4
```

##### Add a custom nadir

```
[DEFAULT]
magick_path=
ffmpeg_path=
frame_rate= 1
time_warp= 
quality= 1
logo_image= /Users/dgreenwood/logo/trekview.png
logo_percentage= 12
debug=TRUE
```

```
python3 gfm.py -n /Users/dgreenwood/logo/trekview.png -p 12 GS018422.mp4
```

## Support

Join our Discord community and get in direct contact with the Trek View team, and the wider Trek View community.

[Join the Trek View Discord server](https://discord.gg/ZVk7h9hCfw).

## License

The code of this site is licensed under an [MIT License](/LICENSE).