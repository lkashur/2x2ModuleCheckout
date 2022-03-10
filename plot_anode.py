#!/usr/bin/env python3
import h5py
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import numpy as np
import json
import glob
import argparse

_default_anode=False
_default_histo=False
_default_asic_config_dir='tpc1_asic_configs'
_default_datalog_file='/data/LArPix/datalog_2022_02_08_16_15_54_CST.h5'
_default_controller_config=None
_default_geometry_file='multi_tile_layout-2.2.16-dict.json'

_default_threshold=False
_default_pixel_trim_dac=False
_default_global_threshold_dac=False
_default_channel_mask=False
_default_adc_mean=False
_default_adc_std=False
_default_channel_id_packet_rate=False
_default_io_channel_packet_rate=False
_default_tile_packet_rate=False

nonrouted_channels=[6,7,8,9,22,23,24,25,38,39,40,54,55,56,57]
routed_channels=[i for i in range(64) if i not in nonrouted_channels]

def unique_channel_id_from_identifiers(io_group, io_channel, chip_id, channel_id): return channel_id + 64 * ( chip_id + 256 * ( io_channel + 256 * ( io_group ) ) )

def unique_channel_id(d): return ((d['io_group'].astype(int)*256+d['io_channel'].astype(int))*256 + d['chip_id'].astype(int))*64 + d['channel_id'].astype(int)

def unique_2_channel_id(unique): return unique % 64

def unique_2_chip_id(unique): return (unique// 64) % 256

def unique_2_io_channel(unique): return(unique//(64*256)) % 256

def unique_2_io_group(unique): return(unique // (64*256*256)) % 256

def unique_2_chip_key_string(unique): return str(unique_2_io_group(int(unique)))+'-'+str(unique_2_io_channel(int(unique)))+'-'+str(unique_2_chip_id(int(unique)))


def tile_number_to_io_channels(tile_number):
    return [(tile_number-1)*4 + j for j in range(1, 5)]

def io_channel_to_tile_number(io_channel):
    for tile_number in range(1, 9):
        if io_channel in tile_number_to_io_channels(tile_number):
            return tile_number
    return -1

def parse_asic_config(asic_config_dir, geometry_dict, cryo=True, vdda=1770):
    offset=210; scale=1.45
    if cryo: offset=465; scale=2.34
    d = dict()
    for filename in glob.glob(asic_config_dir+'/*.json'):
        with open(filename,'r') as f:
            unique_name = filename.split("-")
            #print(unique_name)
            if unique_name[-1] != 'mod.json':
                io_group = int(unique_name[-4])
                io_channel = int(unique_name[-3])
                chip_id = int(unique_name[-2])
            else:
                io_group = int(unique_name[-5])
                io_channel = int(unique_name[-4])
                chip_id = int(unique_name[-3])   
            config_data = json.load(f)
            tile_number = io_channel_to_tile_number(io_channel)
            gt = config_data['register_values']['threshold_global']
            ptd = config_data['register_values']['pixel_trim_dac']
            cm = config_data['register_values']['channel_mask']
            if cm == [1]*64: print('ATTENTION all channels on ',io_group,'-',io_channel,'-',chip_id,'\t are disabled')
            for i in routed_channels:
                u = unique_channel_id_from_identifiers(io_group, io_channel, chip_id, i)
                if str(u) not in geometry_dict: 
                    flag = True
                    #print(tile_number)
                    #print(tile_number_to_io_channels(tile_number))
                    for tile_io_channel in tile_number_to_io_channels(tile_number):
                        if str(unique_channel_id_from_identifiers(io_group, tile_io_channel, chip_id, i)) in geometry_dict:
                            u = unique_channel_id_from_identifiers(io_group, tile_io_channel, chip_id, i)
                if not str(u) in geometry_dict:
                    continue
                d[u] = dict(
                    threshold = ((gt*vdda)/256.) + offset + scale*ptd[i],
                    global_dac = gt,
                    pixel_trim_dac = ptd[i],
                    channel_mask = cm[i],
                    x = geometry_dict[str(u)][0],
                    y = geometry_dict[str(u)][1]                    
                    )   
    return d            



def parse_packets(datalog_file, geometry_dict, max_index=500000):
    d = dict()
    f = h5py.File(datalog_file,'r')
    print(len(f['packets']),' packets')
    if len(f['packets'])<max_index: max_index=len(f['packets'])
    unixtime = f['packets'][:]['timestamp'][0:max_index][f['packets'][:]['packet_type'][0:max_index]==4]
    livetime = np.max(unixtime) - np.min(unixtime)
    data_mask=f['packets'][:]['packet_type'][0:max_index]==0
    valid_parity_mask=f['packets'][:]['valid_parity'][0:max_index]==1

    tile_rate, ioc_rate = [{} for i in range(2)]
    for iog in range(1,3):
        for ioc in range(1,33):
            io_group_mask=f['packets'][:]['io_group'][0:max_index]==iog
            io_channel_mask=f['packets'][:]['io_channel'][0:max_index]==ioc
            m = np.logical_and(io_group_mask, np.logical_and(io_channel_mask, np.logical_and(data_mask, valid_parity_mask)))
            adc = f['packets']['dataword'][0:max_index][m]
            ioc_rate[(iog,ioc)]= len(adc)
            tile = int((ioc-1)/4)+1
            if (iog,tile) not in tile_rate: tile_rate[(iog,tile)]=len(adc)
            else: tile_rate[(iog,tile)]+=len(adc)

    mask = np.logical_and(data_mask, valid_parity_mask)
    adc = f['packets']['dataword'][0:max_index][mask]
    unique_id = unique_channel_id(f['packets'][0:max_index][mask])
    unique_id_set = np.unique(unique_id)
    for i in unique_id_set:
        geo_i = str(i) 
        if str(i) not in geometry_dict:
            io_ch = unique_2_io_channel(i)
            io_gr = unique_2_io_group(i)
            chan_id = unique_2_channel_id(i)
            ch_id = unique_2_chip_id(i)
            tile_number = io_channel_to_tile_number(io_ch)
            for tile_io_channel in tile_number_to_io_channels(tile_number):
                if str(unique_channel_id_from_identifiers(io_gr, tile_io_channel, ch_id, chan_id)) in geometry_dict:
                    geo_i = str(unique_channel_id_from_identifiers(io_gr, tile_io_channel, ch_id, chan_id))
        if not (geo_i in geometry_dict):
            continue

        id_mask = unique_id == i
        masked_adc = adc[id_mask]
        tile = int((unique_2_io_channel(i)-1)/4)+1
        d[i] = dict(
            mean = np.mean(masked_adc),
            std = np.std(masked_adc),
            rate = len(masked_adc) / (livetime + 1e-9),
            iochannel_rate = ioc_rate[(unique_2_io_group(i), unique_2_io_channel(i))] / (livetime + 1e-9),
            tile_rate = tile_rate[(unique_2_io_group(i),tile)] / (livetime + 1e-9),
            x = geometry_dict[geo_i][0],
            y = geometry_dict[geo_i][1]
            )
    return d



### to extract single channel (X,Y) position: X == d[str(unique_channel_id)][0]; Y == d[str(unique_channel_id)][1]
def load_geometry(g):
    geom_dict = None
    with open(g,'r') as f: geom_dict = json.load(f)
    return geom_dict



def get_z_range(metric_string):
    if metric_string=='threshold': return (600,800)
    if metric_string=='pixel_trim_dac': return (0,31)
    if metric_string=='global_dac': return (20,40)
    if metric_string=='channel_mask': return (0,2)
    if metric_string=='mean': return(0,100)
    if metric_string=='std': return(0,10)
    if metric_string=='rate': return(0,250)
    if metric_string=='iochannel_rate': return(0,20)
    if metric_string=='tile_rate': return(0,20)


    
def plot_anode(metric_dict, metric_string, unit):
    zrange = get_z_range(metric_string); print(zrange)
    fig, ax = plt.subplots(1, 2, num=metric_string, figsize=(16,15))
    if metric_string=='threshold' or metric_string=='global_dac' or metric_string=='rate':
        c0 = fig.colorbar(ax[0].scatter([metric_dict[key]['x'] for key in metric_dict.keys() if unique_2_io_group(int(key))==1],
                                        [metric_dict[key]['y'] for key in metric_dict.keys() if unique_2_io_group(int(key))==1],
                                        c=[metric_dict[key][metric_string] for key in metric_dict.keys() if unique_2_io_group(int(key))==1],
                                        marker='s',s=1.5,vmin=zrange[0],vmax=zrange[1]), ax = ax[0])
        c1 = fig.colorbar(ax[1].scatter([metric_dict[key]['x'] for key in metric_dict.keys() if unique_2_io_group(int(key))==2],
                                        [metric_dict[key]['y'] for key in metric_dict.keys() if unique_2_io_group(int(key))==2],
                                        c=[metric_dict[key][metric_string] for key in metric_dict.keys() if unique_2_io_group(int(key))==2],
                                        marker='s',s=1.5,vmin=zrange[0],vmax=zrange[1]), ax = ax[1])
    else:
        c0 = fig.colorbar(ax[0].scatter([metric_dict[key]['x'] for key in metric_dict.keys() if unique_2_io_group(int(key))==1],
                                    [metric_dict[key]['y'] for key in metric_dict.keys() if unique_2_io_group(int(key))==1],
                                    c=[metric_dict[key][metric_string] for key in metric_dict.keys() if unique_2_io_group(int(key))==1],
                                    marker='s',s=1.5), ax = ax[0])
        c1 = fig.colorbar(ax[1].scatter([metric_dict[key]['x'] for key in metric_dict.keys() if unique_2_io_group(int(key))==2],
                                        [metric_dict[key]['y'] for key in metric_dict.keys() if unique_2_io_group(int(key))==2],
                                        c=[metric_dict[key][metric_string] for key in metric_dict.keys() if unique_2_io_group(int(key))==2],
                                        marker='s',s=1.5), ax = ax[1])
    for i in range(2):
        ax[i].set_xlabel('X [mm]')
        ax[i].set_ylabel('Y [mm]')
        ax[i].set_title('Anode '+str(i+1))
    c0.set_label(unit); c1.set_label(unit)

    plt.suptitle(metric_string)
    #plt.tight_layout()
#    plt.show()
    plt.savefig('anode'+'.png')



def plot_1d_histo(metric_dict, metric_string, unit):
    zrange = get_z_range(metric_string); print(zrange)
    fig, ax = plt.subplots(num=metric_string, figsize=(8,6))
    nbins = np.linspace(zrange[0], zrange[1], (zrange[1]-zrange[0])+1)
    if metric_string=='std' or metric_string=='rate' or metric_string=='global_dac': nbins = np.linspace(zrange[0], zrange[1], (zrange[1]-zrange[0])*4+1)
    if metric_string=='threshold': nbins = np.linspace(zrange[0], zrange[1], int((zrange[1]-zrange[0])/4))
    ax.hist([metric_dict[key][metric_string] for key in metric_dict.keys() if unique_2_io_group(int(key))==1],
            bins=nbins, alpha=0.5, label='Anode 1')
    ax.hist([metric_dict[key][metric_string] for key in metric_dict.keys() if unique_2_io_group(int(key))==2],
            bins=nbins, alpha=0.5, label='Anode 2')
    ax.set_xlabel(unit)
    ax.set_ylabel('Channel Count')
    ax.legend()
    ax.grid(True)
    plt.suptitle(metric_string)
    #plt.tight_layout()
    plt.show()
    #plt.savefig(plot_title+'.png')


    
def find_noisy(metric_dict, metric_string, cut):
    for key in metric_dict.keys():
        i = metric_dict[key][metric_string]
        if i>cut: print(unique_2_chip_key_string(key),'-',unique_2_channel_id(key),'\t ',metric_string,' \t value: ',i, '\t (cut ',cut,')')

        
    
def main(anode=_default_anode,
         histo=_default_histo,
         asic_config_dir=_default_asic_config_dir,
         datalog_file=_default_datalog_file,
         geometry_file=_default_geometry_file,
         threshold=_default_threshold,
         pixel_trim_dac=_default_pixel_trim_dac,
         global_threshold_dac=_default_global_threshold_dac,
         channel_mask=_default_channel_mask,
         adc_mean=_default_adc_mean,
         adc_std=_default_adc_std,
         channel_id_packet_rate=_default_channel_id_packet_rate,
         io_channel_packet_rate=_default_io_channel_packet_rate,
         tile_packet_rate=_default_tile_packet_rate,
         **kwargs):
    
    if geometry_file==None: print('Geometry file absent. Exiting early'); return
    geometry_dict = load_geometry(geometry_file)
    
    if threshold or pixel_trim_dac or global_threshold_dac or channel_mask:
        if asic_config_dir==None: print('ASIC config directory absent. Exiting early'); return
        d = parse_asic_config(asic_config_dir, geometry_dict)
        if threshold:
            if anode: plot_anode(d, 'threshold', 'mV')
            if histo: plot_1d_histo(d, 'threshold', 'mV')
        if pixel_trim_dac:
            if anode: plot_anode(d, 'pixel_trim_dac', 'DAC')
            if histo: plot_1d_histo(d, 'pixel_trim_dac', 'DAC')
        if global_threshold_dac:
            if anode: plot_anode(d, 'global_dac', 'DAC')
            if histo: plot_1d_histo(d, 'global_dac', 'DAC')
        if channel_mask:
            if anode: plot_anode(d, 'channel_mask', 'Boolean')
            if histo: plot_1d_histo(d, 'channel_mask', 'Boolean')
        
    if adc_mean or adc_std or channel_id_packet_rate or io_channel_packet_rate or tile_packet_rate:
        if datalog_file==None: print('Datalog file absent. Exiting early'); return
        d = parse_packets(datalog_file, geometry_dict)
        if adc_mean:
            if anode: plot_anode(d, 'mean', 'ADC')
            if histo: plot_1d_histo(d, 'mean', 'ADC')
        if adc_std:
            if anode: plot_anode(d, 'std', 'ADC')
            if histo: plot_1d_histo(d, 'std', 'ADC')
            #find_noisy(d, 'std', 10)
        if channel_id_packet_rate:
            if anode: plot_anode(d, 'rate', 'Hz')
            if histo: plot_1d_histo(d, 'rate', 'Hz')
            #find_noisy(d, 'rate', 100)
        if io_channel_packet_rate:
            if anode: plot_anode(d, 'iochannel_rate', 'Hz')
            if histo: plot_1d_histo(d, 'iochannel_rate', 'Hz')
        if tile_packet_rate:
            if anode: plot_anode(d, 'tile_rate', 'Hz')
            if histo: plot_1d_histo(d, 'tile_rate', 'Hz')

    return

        

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--anode', default=_default_anode, action='store_true', help='''Plot anode''')
    parser.add_argument('--histo', default=_default_histo, action='store_true', help='''Plot 1D histogram''')
    # input file paths
    parser.add_argument('--asic_config_dir', default=_default_asic_config_dir, type=str, help='''Path to ASIC config directory''')
    parser.add_argument('--datalog_file', default=_default_datalog_file, type=str, help='''Path to datalog file''')
    parser.add_argument('--geometry_file', default=_default_geometry_file, type=str, help='''Path to geometry file''')
    # the following require ASIC configuraton file
    parser.add_argument('--threshold', default=_default_threshold, action='store_true', help='''Plot channel threshold from ASIC config ''')
    parser.add_argument('--pixel_trim_dac', default=_default_pixel_trim_dac, action='store_true', help='''Plot pixel trim DAC from ASIC config ''')
    parser.add_argument('--global_threshold_dac', default=_default_global_threshold_dac, action='store_true', help='''Plot global threshold DAC from ASIC config ''')
    parser.add_argument('--channel_mask', default=_default_channel_mask, action='store_true', help='''Plot disabled channels from ASIC config''')
    # the following require datalog file
    parser.add_argument('--adc_mean', default=_default_adc_mean, action='store_true', help='''Plot channel mean ADC from datalog.hdf5 file ''')
    parser.add_argument('--adc_std', default=_default_adc_std, action='store_true', help='''Plot channel std. dev. ADC from datalog.hdf5 file ''')
    parser.add_argument('--channel_id_packet_rate', default=_default_channel_id_packet_rate, action='store_true', help='''Plot channel ID packet rate from datalog.hdf5 file ''') 
    parser.add_argument('--io_channel_packet_rate', default=_default_io_channel_packet_rate, action='store_true', help='''Plot IO channel packet rate from datalog.hdf5 file ''')
    parser.add_argument('--tile_packet_rate', default=_default_tile_packet_rate, action='store_true', help='''Plot tile packet rate from datalog.hdf5 file ''')
    args = parser.parse_args()
    main(**vars(args))
