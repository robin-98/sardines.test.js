# module for building containers
import json
import os
import time
import tarfile
import docker
import sys

client = docker.from_env()

def copy_to_container(container, src:str = None, dst:str = None, filterList = None, user: str = "root", group: str = "root", mode:str = None):
    """Copy source file in a directory to the container

    parameter:
        mode: a string such as "700", "422", "777", "600", "400", which is used to 'chmod' command
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
                tar.add(src, arcname = os.path.basename(dst))
        finally:
            tar.close()

        data = open(tarfilename, 'rb').read()
        container.put_archive(os.path.dirname(dst), data)
        os.remove(tarfilename)

        container.exec_run(
            'chown -R {}:{} {}'.format(user, group, dst)
        )
        if mode is not None:
            container.exec_run(
                'chmod -R {} {}'.format(mode, dst)
            )
        print('copy done from {} to {}:{}'.format(src, container.name, dst))
    except Exception as e:
        print('Error when copying source dir to the container', e)
        raise

def setup_ssh(container)-> str:
    """Setup ssh for the container instance, and return the public key
    """
    if container is None:
        return ""

    (exit_code, output) = container.exec_run(
        "ssh-keygen -t rsa -N '' -f /root/.ssh/id_rsa",
        stream=False
    )
    if exit_code == 0:
        (exit_code, output) = container.exec_run(
            "cat /root/.ssh/id_rsa.pub",
            stream=False
        )
        if exit_code == 0:
            sshkey = output.decode("utf8")
            (exit_code, output) = container.exec_run(
                "service ssh start",
                stream = False
            )
            if exit_code == 0:
                return sshkey
            else:
                print(output.decode("utf8"))
                raise Exception('failed to start ssh service on the container')
        else:
            print(output.decode("utf8"))
            raise Exception('failed to get ssh key for the container')
    else:
        print(output.decode("utf8"))
        raise Exception('failed to setup ssh for the container')


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

        # Prepare the ssh key cache
        sshkeyCache = {}

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
                    if "name" in interface and interface["name"] != "hostname":
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
            hostname = config["hostname"]

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
            # Keep the container running in background
            print("building container {} from image {}...".format(hostname, image))
            inst = client.containers.run(
                image,
                hostname = hostname,
                name = hostname,
                detach = True,
                tty = True,
                extra_hosts = extraHosts,
                ports = ports
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
                        print("[{}:{}/{}] command execution started...".format(hostname, workdir, cmd))
                        (exit_code, output) = inst.exec_run(
                            cmd,
                            workdir = workdir,
                            environment = environment,
                            stream=False
                        )
                        print(output.decode("utf8"))
                        # for line in output:
                        #     print(line.decode("utf8"))
                        print("[{}:{}/{}] command execution finished with exit code: {}\n".format(hostname, workdir, cmd, exit_code))
                        if exit_code > 0:
                            print("building process of container {} failed".format(hostname))
                            sys.exit(exit_code)

            # normal operations have been done                            
            print("container {} has been built from image {}\n".format(hostname, image))


        # Prepare the host keys
        tmpHostkeyFile = "./tmp-hostkeys.txt"
        for host in sshkeyCache:
            inst = containerCache[host]
            # scan host keys
            (exit_code, output) = inst.exec_run(
                "ssh-keyscan -H {}".format(host),
                stream = False
            )
            if exit_code == 0:
                with open(tmpHostkeyFile, 'a') as f:
                    f.write(output.decode("utf8"))
            else:
                print('failed to scan host key for container {}'.format(host))

        # spread ssh trust
        tmpSshkeyFile = "./tmp-sshkeys.txt"
        for hostX in sshkeyCache:
            inst = containerCache[hostX]
            lines = []
            for hostY in sshkeyCache:
                if hostX != hostY:
                    lines.append(sshkeyCache[hostY])
            with open(tmpSshkeyFile, 'w') as f:
                f.writelines(lines)
            copy_to_container(inst, tmpSshkeyFile, '/root/.ssh/authorized_keys')
            copy_to_container(inst, tmpHostkeyFile, '/root/.ssh/known_hosts')
        os.remove(tmpSshkeyFile)
        os.remove(tmpHostkeyFile)

        print("")
        # Commit and build images if needed
        for config in configList:
            hostname = config["hostname"]
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
