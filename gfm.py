import configparser, subprocess, threading, itertools, argparse, platform, logging, datetime, fnmatch, shutil, pandas as pd, shlex, html, copy, time, json, math, csv, os, re
from colorama import init, deinit, reinit, Fore, Back, Style
from gfmhelper import GoProFrameMakerHelper
from gfmmain import GoProFrameMaker

if __name__ == '__main__':
    init()

    print(Fore.GREEN + "########################################")
    print(Fore.GREEN + "#           GOPRO FRAME MAKER          #")
    print(Fore.GREEN + "########################################")
    print(Style.RESET_ALL)

    #parsing command line arguments
    parser = argparse.ArgumentParser()

    #input video files
    parser.add_argument("input", type=str, help="Input a valid video file.", nargs="+", )

    #check if .config is available
    cfg = GoProFrameMakerHelper.getConfig()
    if cfg['status'] == False:

        #ffmpeg binary
        parser.add_argument("-f", "--ffmpeg-path", type=str, help="Set the path for ffmpeg.")
        #ffmpeg options
        parser.add_argument("-r", "--frame-rate", type=int, help="Sets the frame rate (frames per second) for extraction (available=[0.5, 1, 2, 5]), default: 0.5.", default=0.5)
        parser.add_argument("-t", "--time-warp", type=str, help="Set time warp mode for gopro. available values are 2x, 5x, 10x, 15x, 30x")
        parser.add_argument("-q", "--quality", type=int, help="Sets the extracted quality between 2-6. 1 being the highest quality (but slower processing), default: 1. This is value used for ffmpeg -q:v flag. ", default=1)
        
        #nadir image & percentage
        parser.add_argument("-n", "--nadir-image", type=str, help="Nadir image to use on the extracted images.")
        parser.add_argument("-p", "--nadir-percentage", type=str, help="Nadir height percentage to use on the extracted images.")

        #max2spherebatch
        parser.add_argument("-m", "--max-sphere", type=str, help="Set the path for MAX2sphere binary.")

        #fusion2sphere
        parser.add_argument("-u", "--fusion-sphere", type=str, help="Set the path for fusion2sphere binary.")

        #debug option
        parser.add_argument("-d", "--debug", action='store_true', help="Enable debug mode, default: off.")

        #getting args
        args = parser.parse_args()

        #validate arguments
        gfmValidated = GoProFrameMakerHelper.validateArgs(args)
    else:
        #getting args
        args = parser.parse_args()

        #get config default
        default = cfg['config']
        default['input'] = args.input
        args = type('args', (object,), default)

        #validate arguments
        gfmValidated = GoProFrameMakerHelper.validateArgs(args)

    for info in gfmValidated['info']:
        print(Fore.BLUE + info)
        print(Style.RESET_ALL)

    for error in gfmValidated['errors']:
        print(Fore.RED + error)
        print(Style.RESET_ALL)
        exit(0)

    if((gfmValidated['status'] == True) and (len(gfmValidated['errors']) == 0)):
        gfm = GoProFrameMaker(gfmValidated['args'])
        selected_args = gfm.getArguments()
        for k, v in selected_args.items():
            print(Fore.GREEN + "{}: {}".format(k, v))
        print(Style.RESET_ALL)
        if selected_args['time_warp'] != '':
            print(Fore.RED + "\nTime warp value is selected, so the video is considered Time warped, if this is not supposed to be then please remove the value from config.ini key named: `time_warp`")
        print(Style.RESET_ALL)
        
        check = input(Fore.RED + "Are you sure you want to start processing?(y/n)")
        print(Style.RESET_ALL)
        check = 'y' if check.lower().strip() == 'y' else 'n'
        if check == 'y':
            gfm.initiateProcessing()
            print(Fore.GREEN + "\nProcessing finished! If there are no images in the folder please see logs to gain additional information.")
            print(Fore.GREEN + "\nYou can see {} folder to see the images.".format(selected_args['media_folder_full_path']))
            print(Fore.BLUE + "\nHave a nice day!")
            print(Style.RESET_ALL)
            exit(0)
        else:
            print(Fore.RED + "Processing stopped!")
            print(Style.RESET_ALL)
            
    else:
        input(Fore.RED + "Processing stopped!")
        print(Style.RESET_ALL)
    exit(0)
    


    

