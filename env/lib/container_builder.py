# module for building containers
import json
import os
import time
import docker
import sys
if __name__ == "lib.container_builder":
    from lib.utils import setup_ssh
    from lib.utils import copy_to_container
    from lib.utils import build_ssh_trust_relationships
else:
    from env.lib.utils import setup_ssh
    from env.lib.utils import copy_to_container
    from env.lib.utils import build_ssh_trust_relationships

client = docker.from_env()

def build_containers(
    containerConfFile:str = None, 
    configuration: dict = None, 
    baseDir: str = None, 
    hosts: [] = None,
    ignoreCmdErr: bool = False
):
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

        # Prepare the ssh key cache
        sshkeyCache = {}

        # Prepare the IP Address cache
        # And generate temporary hostname for the container if hostname is not provided
        ipaddrCache = {}
        hostFilter = None
        if hosts is not None and type(hosts) == list:
            hostFilter = hosts
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
                    if "name" in interface and interface["name"] != "hostname":
                        interfaceName = interface["name"]

                    ipaddrCache[network]["interfaces"][interfaceName] = {}
                    if "ipv4" in interface:
                        ipaddrCache[network]["interfaces"][interfaceName] = interface["ipv4"]
                    elif "ipv6" in interface:
                        ipaddrCache[network]["interfaces"][interfaceName] = interface["ipv6"]

        # Build the container one by one
        for config in configList:
            if "image" not in config:
                continue
            # Prepare parameters for docker container run command
            image = config["image"]
            hostname = config["hostname"]

            if hostFilter is not None and hostname not in hostFilter:
                continue

            # Prepare extra_hosts
            extraHosts = {}
            for network in ipaddrCache:
                if hostname in ipaddrCache[network]["hosts"]:
                    extraHosts.update(ipaddrCache[network]["interfaces"])

            # Ports to expose
            ports = {}
            if "ports" in config and type(config["ports"]) == dict:
                ports = config["ports"]

            # Create an basic instance of the container
            if hostname in containerCache:
                containerCache[hostname].remove(force = True)
            # Envrionment variables
            environment = {}
            if "environment" in config:
                environment = config["environment"]
            # Volumes
            volumes = {}
            if "volumes" in config:
                for key in config["volumes"]:
                    v = config["volumes"][key]
                    if type(v) == dict and "bind" in v and "mode" in v:
                        volumes[key] = v
            # Keep the container running in background
            print("building container {} from image {}...".format(hostname, image))
            inst = client.containers.run(
                image,
                hostname = hostname,
                name = hostname,
                detach = True,
                tty = True,
                extra_hosts = extraHosts,
                ports = ports,
                environment = environment,
                volumes = volumes
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
                        copy_to_container(inst, copy["source"], copy["target"], filterList)

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

            # setup ssh
            if "ssh" in config and config["ssh"] == True:
                sshkey = setup_ssh(inst)
                sshkeyCache[hostname] = sshkey
                print("container [{}] ssh has been setup".format(hostname))

            # exec commands
            if "commands" in config:
                commands = config["commands"]
                commandList = None
                if "cmd" in commands:
                    commandList = commands["cmd"]
                if commandList is not None \
                    and type(commandList) == list \
                    and len(commandList) > 0:
                    workdir = "/"
                    if "workdir" in commands:
                        workdir = commands["workdir"]
                    environment = {}
                    if "environment" in commands:
                        environment = commands["environment"]
                    for cmd in commandList:
                        cmdStart = time.time()
                        print("[{}:{}/{}] command execution started at <{}>...".format(hostname, workdir, cmd, time.ctime()))
                        (exit_code, output) = inst.exec_run(
                            cmd,
                            workdir = workdir,
                            environment = environment,
                            stream = ignoreCmdErr
                        )
                        if not ignoreCmdErr:
                            print(output.decode("utf8"))
                        else:
                            for line in output:
                                print(line.decode("utf8"))
                        cmdEnd = time.time()
                        print("[{}:{}/{}] command execution finished in {} seconds with exit code: {}\n".format(hostname, workdir, cmd, round(cmdEnd - cmdStart, 1), exit_code))
                        if not ignoreCmdErr and exit_code > 0:
                            print("building process of container {} failed".format(hostname))
                            sys.exit(exit_code)

            # normal operations have been done                            
            print("container {} has been built from image {}\n".format(hostname, image))

        # build or rebuild ssh trust relationships
        build_ssh_trust_relationships(configList, hostFilter, sshkeyCache, containerCache)

        print("")
        # Commit and build images if needed
        for config in configList:
            hostname = config["hostname"]
            if hostFilter is not None and hostname not in hostFilter:
                continue
            inst = containerCache[hostname]
            # Commit to build an image if needed
            if "commit" in config and "image" in config["commit"] and "tag" in config["commit"]:
                tag = "{}:{}".format(config["commit"]["image"], config["commit"]["tag"])
                if tag in imageCache:
                    client.images.remove(imageCache[tag].id, force=True)
                imgInst = inst.commit()
                imgInst.tag(tag)
                print("new image [{}] has been built".format(tag))
        print("everything is done")

    except Exception as e:
        print('Error when building containers:', repr(e))
        raise
