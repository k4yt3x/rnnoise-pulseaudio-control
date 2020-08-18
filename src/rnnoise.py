#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Creator: RNNoise Controller
Author: K4YT3X
Date Created: August 18, 2020
Last Modified: August 18, 2020
"""

# built-in imports
import argparse
import pathlib
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import traceback
import urllib

# third-party imports
import requests

PACMD = "/usr/bin/pacmd"
PACTL = "/usr/bin/pactl"


def parse_arguments():
    """parse command line arguments
    """
    parser = argparse.ArgumentParser(
        prog="rnnoise", formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "action",
        help="action to perform",
        choices=["install", "uninstall", "enable", "disable"],
    )

    parser.add_argument(
        "-p",
        "--path",
        type=pathlib.Path,
        help="path which RNNoise is installed under",
        default=pathlib.Path().home() / ".local" / "share" / "rnnoise",
    )

    parser.add_argument(
        "-m",
        "--monitor",
        help="enable monitor mode (route denoised audio to output sink)",
        action="store_true",
    )

    return parser.parse_args()


def download(url, save_as=None, save_path=None, chunk_size=4096) -> pathlib.Path:
    """download file to local with requests library
    Arguments:
        url {string} -- download url
        save_as {string/pathlib.Path} -- output file (default: {None})
        save_path {string/pathlib.Path} -- folder to save downloaded file to (default: {None})
    Keyword Arguments:
        chunk_size {number} -- download stream chunk size (default: {4096})
    Returns:
        pathlib.Path -- full path of downloaded file
    """

    # create requests stream for steaming file
    stream = requests.get(url, stream=True, allow_redirects=True)

    # determine output file path
    # if exact output file name specified
    if save_as:
        output_file = pathlib.Path(save_as)

    # if output directory specified
    # or if no output is specified
    else:

        # get file name
        file_name = None
        if "content-disposition" in stream.headers:
            disposition = stream.headers["content-disposition"]
            try:
                file_name = re.findall("filename=(.+)", disposition)[0].strip('"')
            except IndexError:
                pass

        # if save_path is not specified, use current directory
        if save_path is None:
            save_path = pathlib.Path(".")
        else:
            save_path = pathlib.Path(save_path)

        # create target folder if it doesn't exist
        save_path.mkdir(parents=True, exist_ok=True)

        # if no file name could be determined
        # create file name from URL
        if file_name is None:
            output_file = save_path / stream.url.split("/")[-1]
        else:
            output_file = save_path / file_name

        # decode url encoding
        output_file = pathlib.Path(urllib.parse.unquote(str(output_file)))

    # get total size for progress bar if provided in headers
    total_size = 0
    if "content-length" in stream.headers:
        total_size = int(stream.headers["content-length"])

    # print download information summary
    print(f"Downloading: {url}")
    print(f"Total size: {total_size}")
    print(f"Chunk size: {chunk_size}")
    print(f"Saving to: {output_file}")

    # write content into file
    with open(output_file, "wb") as output:
        for chunk in stream.iter_content(chunk_size=chunk_size):
            if chunk:
                output.write(chunk)

    # return the full path of saved file
    return output_file


def get_default_sinks() -> tuple:
    """get PulseAudio default input and output sinks

    Returns:
        tuple: a tuple of the name of input sink and output sink
    """
    pacmd_stat = subprocess.run([PACMD, "stat"], capture_output=True)

    for line in pacmd_stat.stdout.decode().split("\n"):
        if line.startswith("Default source name: "):
            input_sink = line.split(": ")[1]
        if line.startswith("Default sink name: "):
            output_sink = line.split(": ")[1]

    return input_sink, output_sink


def enable_rnnoise():
    """load RNNoise plugin into PulseAudio
    """
    print("Enabling RNNoise for PulseAudio", file=sys.stderr)
    print("Loading PulseAudio module", file=sys.stderr)

    ladspa_file = args.path / "bin" / "ladspa" / "librnnoise_ladspa.so"
    input_sink, output_sink = get_default_sinks()

    # check if librnnoise_ladspa.so exists
    if ladspa_file.is_file():
        print(f"Found librnnoise_ladspa.so at: {ladspa_file}", file=sys.stderr)
    else:
        print("librnnoise_ladspa.so not found", file=sys.stderr)
        sys.exit(1)

    print(f"Found input sink: {input_sink}", file=sys.stderr)
    print(f"Found output sink: {output_sink}", file=sys.stderr)

    commands = [
        [
            PACMD,
            "load-module",
            "module-null-sink",
            "sink_name=mic_denoised_out",
            "rate=48000",
        ],
        [
            PACMD,
            "load-module",
            "module-ladspa-sink",
            "sink_name=mic_raw_in",
            "sink_master=mic_denoised_out",
            "label=noise_suppressor_mono",
            f"plugin={ladspa_file}",
            "control=95",
        ],
        [
            PACMD,
            "load-module",
            "module-loopback",
            f"source={input_sink}",
            "sink=mic_raw_in",
            "channels=1",
        ],
        [
            PACMD,
            "load-module",
            "module-remap-source",
            "source_name=denoised",
            "master=mic_denoised_out.monitor",
            "channels=1",
        ],
        [PACMD, "set-default-source", "denoised"],
    ]

    for command in commands:
        print(shlex.join(command), file=sys.stderr)
        subprocess.run(command, check=True)


def disable_rnnoise():
    """unload RNNoise plugin from PulseAudio
    """
    print("Disabling RNNoise for PulseAudio", file=sys.stderr)
    print("Unloading modules from PulseAudio", file=sys.stderr)

    commands = [
        [PACTL, "unload-module", "module-loopback"],
        [PACTL, "unload-module", "module-null-sink"],
        [PACTL, "unload-module", "module-ladspa-sink"],
        [PACTL, "unload-module", "module-remap-source"],
    ]

    for command in commands:
        print(shlex.join(command), file=sys.stderr)
        subprocess.run(command)


def enable_monitoring():
    """enable monitoring mode on the denoised output
    """
    print("Enabling monitoring on denoised input", file=sys.stderr)

    input_sink, output_sink = get_default_sinks()

    command = [
        PACMD,
        "load-module",
        "module-loopback",
        "latency_msec=1",
        "source=denoised",
        f"sink={output_sink}",
    ]

    print(shlex.join(command), file=sys.stderr)
    subprocess.run(command)


# parse command line arguments
args = parse_arguments()

# download and install RNNoise file
if args.action == "install":

    if args.path.is_dir():
        print(f"Deleting existing RNNoise files at {args.path}", file=sys.stderr)
        shutil.rmtree(args.path)

    print("Downloading the latest RNNoise release file from GitHub", file=sys.stderr)

    download_url = None
    latest_release_json = requests.get(
        "https://api.github.com/repos/werman/noise-suppression-for-voice/releases/latest"
    ).json()
    for asset in latest_release_json["assets"]:
        if asset["name"].startswith("linux"):
            download_url = asset["browser_download_url"]

    # if download URL is not found
    if download_url is None:
        print(
            "Error: failed to find Real-time Noise Suppression Plugin latest release download URL",
            file=sys.stderr,
        )
        sys.exit(1)

    rnnoise_tarfile_path = download(download_url, save_as="/tmp/rnnoise.tar.gz")

    print(f"Extracting downloaded archive to: {args.path}", file=sys.stderr)
    rnnoise_tarfile = tarfile.open(rnnoise_tarfile_path)
    rnnoise_tarfile.extractall(args.path)
    rnnoise_tarfile_path.unlink()
    print(f"RNNoise has been installed to: {args.path}", file=sys.stderr)

# delete installed RNNoise files from system
elif args.action == "uninstall":

    if args.path.is_dir():
        # disable RNNoise before removal
        disable_rnnoise()

        print(f"Removing RNNoise directory: {args.path}")
        shutil.rmtree(args.path)

    else:
        print("Specified RNNoise directory not found")
        sys.exit(1)

# enable RNNoise
elif args.action == "enable":
    try:
        enable_rnnoise()

        if args.monitor is True:
            enable_monitoring()

    except Exception:
        disable_rnnoise()
        traceback.print_exc()

# disable RNNoise
elif args.action == "disable":
    disable_rnnoise()
