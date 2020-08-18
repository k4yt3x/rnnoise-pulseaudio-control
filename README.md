# RNNoise PulseAudio Control

RNNoise installation and control script for PulseAudio on Linux.

This script is based on the following projects:

- https://github.com/werman/noise-suppression-for-voice
- https://github.com/xiph/rnnoise

## Usages

You need to have `python3` installed.

```shell
git clone https://github.com/k4yt3x/rnnoise-pulseaudio-control.git
python3 rnnoise-pulseaudio-control/src/rnnoise.py install
python3 rnnoise-pulseaudio-control/src/rnnoise.py enable
```

## Detailed Usages

Refer to the command line help message.

```console
usage: rnnoise [-h] [-p PATH] [-m] {install,uninstall,enable,disable}

positional arguments:
  {install,uninstall,enable,disable}
                        action to perform

optional arguments:
  -h, --help            show this help message and exit
  -p PATH, --path PATH  path which RNNoise is installed under (default: ~/.local/share/rnnoise)
  -m, --monitor         enable monitor mode (route denoised audio to output sink) (default: False)
```
