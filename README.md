# GoPro 360 mp4 video to frames

Converts GoPro mp4s with equirectangular projections into single frames with correct metadata.

## Installation

TODO 

## Usage

### Camera support

This video only accepts mp4 videos shot on a GoPro 360 camera (and processed to mp4 with GoPro stitching software).

A series of validations are run to ensure this. If the script fails any of these checks, you will see an error returned.

[The full list of validations can be read here](https://guides.trekview.org/explorer/developer-docs/sequence-functions/upload#video-mp-4).

This script has currently been tested with the following GoPro cameras:

* GoPro MAX
* GoPro Fusion

### Script

```
$  [options] videofile
```

Options:

* -r n sets the frame rate (frames per second) for extraction, default: 5
* -q n sets the extracted quality between 2-6. 2 being the highest quality (but slower processing), default: 1
* -d enable debug mode, default: off

#### Examples (MacOS)

##### TODO


## Support

Join our Discord community and get in direct contact with the Trek View team, and the wider Trek View community.

[Join the Trek View Discord server](https://discord.gg/ZVk7h9hCfw).

## License

The code of this site is licensed under an [MIT License](/LICENSE).