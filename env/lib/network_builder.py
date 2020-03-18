# module for building networks
import json
import os
import time
import tarfile
import docker
import sys

client = docker.from_env()

def create_networks(netConfFile:str = None, configuration:dict = None):
    """To create custom networks according to configuration

    Arguments:
    netConfFile: the filepath of configuration of custom netowrks, in JSON format
    configuration: an already loaded dictionary for the network configuration
    """

    try:
        netConf = configuration
        if configuration is None and netConfFile is not None:
            with open(netConfFile) as f:
                netConf = json.load(f)
        if netConf is None:
            raise Exception('can not read configuration data')
        # list local networks
        netlist = [x.name for x in client.networks.list()]
        # process the network configuration
        for networkName in netConf.keys():
            if networkName in netlist:
                continue
            conf = netConf[networkName]
            if "subnet" in conf.keys() and "gateway" in conf.keys():
                ipam_config = docker.types.IPAMConfig(
                    pool_configs = [docker.types.IPAMPool(
                        subnet = conf["subnet"],
                        gateway = conf["gateway"]
                    )]
                )
            driver = "bridge"
            if "driver" in conf.keys():
                driver = conf["driver"]
            client.networks.create(
                networkName,
                driver = driver,
                ipam = ipam_config
            )
            print('network [{}] is created'.format(networkName))

    except Exception as e:
        print('Error when creating network:', e)
