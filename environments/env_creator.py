#!/usr/bin/env python3

# Created on 3/6/2020, by Robin, robin@naturewake.com
import argparse
import sys
import json
import os
import docker
from container_builder import build_containers
from db_builder import create_postgres_databases

client = docker.from_env()

def build_images(imgConfFile:str = None, configuration: dict = None, baseDir: str = None):
    """Build docker images

    argument list:
    imgConfFile: image configuration file path
    configuration: an already loaded dictionary object of the configuration file content
    baseDir: used to resolve the file path within the configuration dictionary
    """
    try:
        imgConf = configuration
        confBaseDir = '.'
        if baseDir is not None:
            confBaseDir = baseDir
        if imgConf is None and imgConfFile is not None:
            with open(imgConfFile) as f:
                imgConf = json.load(f)
                confBaseDir = os.path.dirname(imgConfFile)
        # get local images 
        localImages = client.images.list()
        localImageTags = []
        for img in localImages:
            localImageTags.extend(img.tags)
        # build images
        for imgName in imgConf.keys():
            for imgTag in imgConf[imgName].keys():
                conf = imgConf[imgName][imgTag]
                dockerfile = None
                if type(conf) == dict and conf["dockerfile"] is not None:
                    dockerfile = conf["dockerfile"]
                elif type(conf) == str:
                    dockerfile = conf
                if dockerfile is None:
                    raise Exception('invalid dockerfile for building image {}:{}'.format(imgName, imgTag))
                # Dcoker file path is dockerfile
                dockerfile = os.path.relpath(os.path.join(confBaseDir, dockerfile))
                if not os.path.exists(dockerfile):
                    raise Exception('dockerfile does not exist at {} for building image {}:{}'.format(dockerfile, imgName, imgTag))
                # check whether the image already exists
                tag = '{}:{}'.format(imgName, imgTag)
                if tag not in localImageTags:
                    with open(dockerfile, 'rb') as df:
                        (imgInst, log) = client.images.build(fileobj = df, tag = tag)
                    print(log)
                    print('docker image [{}] has been built'.format(tag))
    except Exception as e:
        print('Error when building image:', e)

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
    

# Execute from the command line
if __name__ == "__main__":

    baseDir = os.path.dirname(sys.argv[0])

    argParser = argparse.ArgumentParser(description='create en envrionment for testing')
    argParser.add_argument('--env', type=str, required=False, help='env tag, such as dev, prod, test, ..., if the env already created before and saved under the env name, then the env configuration file will be directly used to create the desired envrionment')
    argParser.add_argument('--build-images', type=str, required=False, help='Build image according to configuration file, which in JSON format with dockerfile addresses')
    argParser.add_argument('--create-networks', type=str, required=False, help='Create a custom network according to a configuration file, which in JSON format with all network settings')
    argParser.add_argument('--build-containers', type=str, required=False,
        help='Build container instances according to a configuration file, which in JSON format with all container settings')
    argParser.add_argument('--create-postgres-db', type=str, required=False,
        help='Build databases in container instances according to a configuration file, which in JSON format with all container settings')
    args = argParser.parse_args()

    if args.build_images is not None:
        build_images(args.build_images)
    
    if args.create_networks is not None:
        create_networks(args.create_networks)

    if args.build_containers is not None:
        build_containers(args.build_containers)

    if args.create_postgres_db is not None:
        create_postgres_databases(args.create_postgres_db)
