#!/usr/bin/env python3
import os
import tarfile
import time
import docker

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

    tarfilename = "{}_tmp_{}.tar".format(src, time.time())
    try:
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
    finally:
        if os.path.exists(tarfilename):
            os.remove(tarfilename)


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
                raise Exception('failed to start ssh service on the container [{}]'.format(container.name))
        else:
            print(output.decode("utf8"))
            raise Exception('failed to get ssh key for the container [{}]'.format(container.name))
    else:
        print(output.decode("utf8"))
        raise Exception('failed to setup ssh for the container [{}]'.format(container.name))

def get_ssh_pub_key(container)->str:
    """get public key of the container
    """
    if container is None:
        return ""

    (exit_code, output) = container.exec_run(
        "cat /root/.ssh/id_rsa.pub",
        stream = False
    )
    if exit_code == 0:
        pubkey = output.decode("utf8")
        return pubkey
    else:
        print(output.decode("utf8"))
        raise Exception('failed to get ssh public key on container [{}]'.format(container.name))

def build_ssh_trust_relationships(configList:list = None,  hosts:list = None, sshkeyCacheInMem: dict = None, containerCacheInMem: dict = None):
    if sshkeyCacheInMem is not None:
        sshkeyCache = sshkeyCacheInMem
    else:
        sshkeyCache = {}
    if containerCacheInMem is not None:
        containerCache = containerCacheInMem
    else:
        containerCache = {}
        for inst in client.containers.list(all = True):
            containerCache[inst.name] = inst

    # Populate sshkeyCache if hosts is not None
    shouldBuildSsh = True
    if hosts is not None and configList is None:
        raise Exception('ERROR when trying to build ssh trust between containers, please provide configurations of the containers in a list')
    elif hosts is not None:
        shouldBuildSsh = False
        for host in hosts:
            for config in configList:
                if "hostname" in config and config["hostname"] == host:
                    if "ssh" in config and config["ssh"] == True:
                        shouldBuildSsh = True
                        break
        if shouldBuildSsh:
            for config in configList:
                if "hostname" not in config:
                    continue
                if "ssh" not in config or config["ssh"] != True:
                    continue
                hostname = config["hostname"]
                if hostname not in containerCache:
                    continue
                if hostname in sshkeyCache:
                    continue
                sshkeyCache[hostname] = get_ssh_pub_key(containerCache[hostname])
    
    if not shouldBuildSsh:
        return

    if len(sshkeyCache.keys()) > 0 and shouldBuildSsh:
        print("setting up ssh trust relationships")
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
                errMsg = 'failed to scan host key for container {}'.format(host)
                print(errMsg)
                raise Exception(errMsg)

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
        print("ssh trust relationships have been setup")
