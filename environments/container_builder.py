# module for building containers

import sys
import json
import os
import time
import docker

client = docker.from_env()

def build_containers(containerConfFile:str = None, configuration: dict = None, baseDir: str = None):
    """Build docker container instances according to the configuration
    """
    configBaseDir = baseDir
    if baseDir is None and containerConfFile is not None:
        configBaseDir = os.path.dirname(containerConfFile)
    if configBaseDir is None:
        configBaseDir = './'

    try:
        configList = configuration
        if configuration is None and containerConfFile is not None:
            with open(containerConfFile) as f:
                configList = json.load(f)
        if configList is None or type(configList) != list:
            raise Exception('container configuration is invalid')

        # Prepare the network list
        networkCache = {}
        for inst in client.networks.list():
            networkCache[inst.name] = inst

        # Prepare the container list
        containerCache = {}
        for inst in client.containers.list(all = True):
            containerCache[inst.name] = inst

        # Process the container one by one
        for config in configList:
            if "image" not in config:
                continue
            # Prepare parameters for docker container run command
            image = config["image"]
            command = None
            if "command" in config:
                command = config["commands"]
            if type(command) != list or len(command) == 0:
                command = None
            hostname = None
            if "hostname" in config:
                hostname = config["hostname"]
            if hostname is None:
                hostname = "vm"+round(time.time())
            # Create an basic instance of the container
            if hostname in containerCache:
                containerCache[hostname].remove(force = True)

            inst = client.containers.create(
                image,
                command = command,
                hostname = hostname,
                name = hostname,
                detach = True
            )
            containerCache[hostname] = inst

            # Connect to desired network
            if "networkInterfaces" in config:
                for interface in config["networkInterfaces"]:
                    if "network" not in interface:
                        continue
                    networkName = interface["network"]
                    if networkName not in networkCache:
                        continue
                    ipv4_address = None
                    if "ipv4" in config:
                        ipv4_address = config["ipv4"]
                    networkCache[networkName].connect(
                        inst.id, 
                        ipv4_address = ipv4_address
                    )

    except Exception as e:
        print('Error when building containers:', e)
