# module for building containers
import json
import os
import time
import tarfile
import docker

client = docker.from_env()

def copy_dir_to_container(container, src:str = None, dst:str = None, filterList = None):
    """Copy source file in a directory to the container
    """
    print('trying to copy {} to {}:{}'.format(src, container.name, dst))
    if container is None or src is None or dst is None:
        return
    if not os.path.exists(src):
        raise Exception('source [{}] does not exist'.format(src))

    try:
        tarfilename = "{}_tmp_{}.tar".format(src, time.time())
        tar = tarfile.open(tarfilename, mode='w')
        try:
            if os.path.isdir(src):
                def filterFunc(item: tarfile.TarInfo):
                    if filterList is None:
                        return item
                    else:
                        for filterItem in filterList:
                            if filterItem in item.path:
                                return None
                    return item

                tar.add(src, arcname = os.path.basename(dst), filter = filterFunc)
            else:
                tar.add(src, arcname = os.path.basename(src))
        finally:
            tar.close()

        data = open(tarfilename, 'rb').read()
        container.put_archive(os.path.dirname(dst), data)
        os.remove(tarfilename)
        print('copy done from {} to {}:{}'.format(src, container.name, dst))
    except Exception as e:
        print('Error when copying source dir to the container', e)
        raise

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

        # Prepare the image list
        imageCache = {}
        for img in client.images.list(all=True):
            for t in img.tags:
                imageCache[t] = img

        # Prepare the network list
        networkCache = {}
        for inst in client.networks.list():
            networkCache[inst.name] = inst

        # Prepare the container list
        containerCache = {}
        for inst in client.containers.list(all = True):
            containerCache[inst.name] = inst

        # Prepare the IP Address cache
        # And generate temporary hostname for the container if hostname is not provided
        ipaddrCache = {}
        for config in configList:
            hostname = None
            if "hostname" in config:
                hostname = config["hostname"]
            else:
                hostname = "vm"+round(time.time())
                config["hostname"] = hostname

            if "networkInterfaces" in config:
                for interface in config["networkInterfaces"]:
                    if "network" not in interface:
                        continue
                    network = interface["network"]
                    if network not in ipaddrCache:
                        ipaddrCache[network] = {}
                    if "hosts" not in ipaddrCache[network]:
                        ipaddrCache[network]["hosts"] = set()
                    ipaddrCache[network]["hosts"].add(hostname)
                    if "interfaces" not in ipaddrCache[network]:
                        ipaddrCache[network]["interfaces"] = {}

                    interfaceName = hostname
                    if "name" in interface and interface["name"] != "hostanme":
                        interfaceName = interface["name"]

                    ipaddrCache[network]["interfaces"][interfaceName] = {}
                    if "ipv4" in interface:
                        ipaddrCache[network]["interfaces"][interfaceName] = interface["ipv4"]
                    elif "ipv6" in interface:
                        ipaddrCache[network]["interfaces"][interfaceName] = interface["ipv6"]

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
            hostname = config["hostname"]

            # Prepare extra_hosts
            extraHosts = {}
            for network in ipaddrCache:
                if hostname in ipaddrCache[network]["hosts"]:
                    extraHosts.update(ipaddrCache[network]["interfaces"])

            # Create an basic instance of the container
            if hostname in containerCache:
                containerCache[hostname].remove(force = True)
            # Keep the container running in background
            inst = client.containers.run(
                image,
                command = command,
                hostname = hostname,
                name = hostname,
                detach = True,
                tty = True,
                extra_hosts = extraHosts
            )
            containerCache[hostname] = inst

            # Copy files
            if "copy" in config:
                for copy in config["copy"]:
                    if "source" not in copy or "target" not in copy:
                        continue
                    if "source" == "" or "target" == "":
                        continue
                    if not os.path.exists(copy["source"]):
                        continue
                    if "filter" in copy:
                        filterList = copy["filter"]
                    if os.path.isdir(copy["source"]):
                        copy_dir_to_container(inst, copy["source"], copy["target"], filterList)

            # Connect to desired network
            if "networkInterfaces" in config:
                for interface in config["networkInterfaces"]:
                    if "network" not in interface:
                        continue
                    networkName = interface["network"]
                    if networkName not in networkCache:
                        continue
                    ipv4_address = None
                    if "ipv4" in interface:
                        ipv4_address = interface["ipv4"]
                    print("container [{}] ip adress [{}] is on".format(hostname, ipv4_address))
                    networkCache[networkName].connect(
                        inst.id, 
                        ipv4_address = ipv4_address
                    )

            # Commit to build an image if needed
            if "commit" in config and "image" in config["commit"] and "tag" in config["commit"]:
                tag = "{}:{}".format(config["commit"]["image"], config["commit"]["tag"])
                if tag in imageCache:
                    client.images.remove(imageCache[tag].id, force=True)
                imgInst = inst.commit()
                imgInst.tag(tag)
                print("new image [{}] has been built".format(tag))

    except Exception as e:
        print('Error when building containers:', repr(e))
