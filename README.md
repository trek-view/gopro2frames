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

## Support

Join our Discord community and get in direct contact with the Trek View team, and the wider Trek View community.

[Join the Trek View Discord server](https://discord.gg/ZVk7h9hCfw).

## License

The code of this site is licensed under an [MIT License](/LICENSE).
