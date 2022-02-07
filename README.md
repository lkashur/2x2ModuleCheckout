# 2x2ModuleCheckout
Testing scripts for ArgonCube 2x2 TPC module charge charge readout system.

# Connectivity Tests
## Tile Power Draw
Connect to PACMAN, enable power to tiles, and report the voltage and current draw of each tile.
```
ssh root@acd-pacman01
./power_up_all.sh
./report_power.sh
```

## Establish Hydra Networks
Create Hydra networks using algorithm in map_uart_links_qc.py.  This algorithm produces a JSON network configuration file for each tile.  
```
python3 map_uart_links_qc.py --pacman_tile <tile #> --tile_id <tile id #>
```

# Functionality Tests
## Trigger Rate
Identify channels with high trigger rates using algorithm in trigger_rate_qc.py.  This algorithm sets channel thresholds at half dynamic range and runs in self-trigger mode with no periodic reset.  The algorithm uses two iterations: a first iteration to identify channels with rates > 10 kHz and a second iteration to identify channels with rates > 1 kHz.  
```
Enter trigger_rate_qc.py usage here.
```

## Pedestal
Identify channels with high baseline or noise using pedestal.py, where chips are run using an internal periodic trigger.  
```
Enter pedestal_qc.py usage here.
```

## Channel Thresholding

## Self-Trigger
