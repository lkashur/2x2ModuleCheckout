# LArPix Charge Readout System Acceptance Testing
##Version 1
### Scripts and procedures for testing at LArTF

**Verifying Connection to PACMAN Board**

To check a connection can be made to the PACMAN boards, use the command:

```
$ ping acd-pacman01
```

If the ping is successful, log into the PACMAN to power the tiles, and then verify the correct power is drawn:

```
ssh root@acd-pacman01
#enter password
$ ./power_up_all.sh
$ ./report_power.sh
```

The reported currents should be approximately as follows:

- VDDA 1870 mV
- VDDD 1650 mV
- IDDA 150-200 mA
- IDDD 500-550 mA

If the measurements shown are far out of spec, contact someone familar with the CRS before proceeding.

End the ssh session from PACMAN

```
$ exit
```

**Establish Hydra Networks**

First, make sure that the file *io/pacman.json* has the correct io group, PACMAN host name listed.

Create the hydra network and test all UART connections on the tiles (do this for one tile at a time):

```
$ python3 map_uart_links_qc.py --pacman_tile X --tile_id XXX
```

where X is the tile number of the tile under test, and XXX us the unique specifier for the tile (invariant in case tiles are moved around). 

This script will print to screen information about the results of the UART testing, and it will write a hydra-network configuration file. The important things to note are:

1) Are all 4 root-ext connections working?
2) Are all 100 ASICs incoorperated into the hydra network?
3) Is there a large increase (since the last time testing this tile) in the number of failed UARTs?

The output hydra-network file will be named *tile-id-XXX-pacman-tile-X.json*. Make a directory *configs* and move these files into it.

**Disable High Leakage Channels**
```
$ python3 trigger_rate_qc.py –-controller_config tile-id-<tile id no.> -pacman-tile <pacman tile no.>.json --disabled_list <path to already existing disable list
```
This algorithm runs twice producing two output hdf5 files. Each ASIC is tested one at a time,
counting the trigger rate with channel thresholds at half dynamic range. The provided disabled
list is comprised of previously identified failed channels. Channels that exceed a prespecified
trigger rate (defaults are 10 kHz and 1khz) are added to the output disabled list with filename
trigger-rate-DO-NOT-ENABLE-channel-list-<timestamp>.json

**Measure AC Noise**

```
$ python3 pedestal_qc.py --controller_config tile-id -<tile idno.> -pacman-tile<pacman tile no.>.json --disabled_list
trigger-rate-DO-NOT-ENABLE-channel-list-<timestamp>.json
```
This algorithm samples sub-threshold charge at periodic intervals. The algorithm runs twice
such that channels identified to be exceptionally noisy are disabled before the second iteration
of the algorithm. Two output pedestal files (pedestal_<timestamp>_*.h5 and
recursive_<timestamp>.h5) and an updated bad channels list
(pedestal-bad-channels-<timestamp>.json) are produced.

**Configure for Self Triggering, Verifying Triggering Stability**

To configure ASIC threshold settings, do the following;

```
$ python3 threshold_qc.py --controller_config tile-id-<tile id
no.>-pacman-tile<pacman tile no.>.json --disabled_list
pedestal-bad-channels-<timestamp>.json --pedestal_file
recursive_<timestamp>.h5
```

For each ASIC in your hydra network, an ASIC configuration file with filename config-*.json
will be produced. Move these ASIC configuration files to a dedicated directory:
```
$ mkdir asic_configs/tile-id-<tile id no.>/
$ mv config-*.json asic_configs/tile-id-<tile id no.>/
```
Increase the global threshold by 1 DAC, to lower the trigger rate:
```
$ python3 increment_global.py asic_configs/tile-id-<tile id no.>/*
--inc 1
```
To take self-triggered data, do the following:
```
$ python3 start_run_log_raw.py --controller_config tile-id-<tile id
no.>-pacman-tile<pacman tile no.>.json --config_name 
asic_configs/tile-id-<tile id no.>
```
By default, self triggered data will be taken for a default run time of 10 minutes. If the average
trigger rate exceeds ~1 kHz, increase the global threshold DAC further. The target tile trigger
rate is O(100) Hz.
Convert the raw binary file to the hdf5 file format with the packet dataset:

```
$ python3 larpix-control/scripts/convert_rawhdf5_to_hdf5.py
--input_filename <raw file>.h5 --output_filename <packet fle>.h5
```
Plot the mean ADC, ADC RMS, and trigger rate to verify uniformity.
