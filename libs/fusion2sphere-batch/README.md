# Fusion2Sphere-batch

Fusion2Sphere-batch is based upon (Fusion2Sphere and MAX2sphere-batch) and takes input and output directory and converts them to equirectangular projection.

[A full description of the scripts logic can be seen here](https://github.com/trek-view/fusion2sphere).

## Installation

The fusion2sphere-batch command line utility should build out of the box on Linux using the simple Makefile provided. The only external dependency is the standard jpeg library (libjpeg), the lib and include directories need to be on the gcc build path. The same applies to MacOS except Xcode and command line tools need to be installed.

```
$ git clone https://github.com/trek-view/fusion2sphere-batch
$ make -f Makefile
$ @SYSTEM_PATH/fusion2sphere-batch
```

## Usage

```
$ ./fusion2spherebatch -w 4096 -b 5 -g 1 -h 1 -o ./%06d.jpg -x ./front/%06d.jpg ./back/%06d.jpg ./param.txt
```

Options:

* -w n: sets the output image size, default: twice fisheye width
* -a n: sets antialiasing level, default: 2
* -b n: longitude width for blending, default: no blending
* -q n: blend power, default: linear
* -e n: optimise over n random steps
* -p n n n: range search aperture, center and rotations, default: 10 20 5
* -f flag needs two images one from front and second from back.
* -o flag for output directory.
* -x flag for input directory where first is consider the front and second is back.
* -g flag is for start image.
* -h flag is for end image.
* -d: debug mode
