#!/usr/bin/bash
# Author: K4YT3X
# Date Created: August 18, 2020
# Last Modified: August 18, 2020

# print help message if no action is defined
if [ -z "$1" ]; then
    echo "No action specified"
    echo "Usage: rnnoise.sh [enable|disable]"
    exit 0
fi

# get paths and variables
parent_path="/home/k4yt3x/Applications/linux_rnnoise"
input_sink=$(pacmd stat | grep -o -P "(?<=Default source name: ).*")
output_sink=$(pacmd stat | grep -o -P "(?<=Default sink name: ).*")
ladspa_file=$parent_path/bin/ladspa/librnnoise_ladspa.so

# output information for debugging purposes
echo "Input sink:" $input_sink
echo "Output sink:" $output_sink

# ehck
if [ -f "$ladspa_file" ]; then
    echo "$ladspa_file exists"
else
    echo "$ladspa_file doesn't exist, aborting script execution"
    exit 1
fi

if [ "$1" == "enable" ]; then
    pacmd load-module module-null-sink sink_name=mic_denoised_out rate=48000
    pacmd load-module module-ladspa-sink sink_name=mic_raw_in sink_master=mic_denoised_out label=noise_suppressor_mono plugin=$ladspa_file control=95
    pacmd load-module module-loopback source=$input_sink sink=mic_raw_in channels=1
    pacmd load-module module-remap-source source_name=denoised master=mic_denoised_out.monitor channels=1
    pacmd set-default-source denoised
elif [ "$1" == "disable" ]; then
    pactl unload-module module-loopback
    pactl unload-module module-null-sink
    pactl unload-module module-ladspa-sink
    pactl unload-module module-remap-source
else
    echo "Unrecognized action: $1"
    echo "Usage: rnnoise.sh [enable|disable]"
    exit 1
fi
