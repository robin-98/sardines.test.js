#!/usr/bin/env python3

import docker
import os
import json
import sys
import time
from lib.container_builder import copy_to_container

client = docker.from_env()

def deploy_repository(hostname: str = None, deployPlanFile: str = None, workdir:str = '/sardines/shoal'):
    try:
        containerCache = {}
        for inst in client.containers.list():
            containerCache[inst.name] = inst
        if hostname is None or hostname not in containerCache:
            raise Exception('target container {} does not exist'.format(hostanme))
        if deployPlanFile is None or not os.path.exists(deployPlanFile):
            raise Exception('deploy plan file {} does not exist'.format(deployPlanFile))
        inst = containerCache[hostname]
        copy_to_container(inst, deployPlanFile, "{}/deploy-repository.json".format(workdir))
        (exit_code, output) = inst.exec_run(
            "npm run startRepo",
            workdir = workdir,
            tty = True,
            stream = False,
            detach = True
        )
        if exit_code is not None:
            print(output.decode("utf8"))
            raise Exception("error when executing startRepo command on container")
        else:
            print("repository has been deployed on container {}".format(hostname))
    except Exception as e:
        print('Error while deploying repository on container {}:'.format(hostname), e)
        raise e



if __name__ == "__main__":
    import argparse
    argParser = argparse.ArgumentParser(description='build testing system and run test cases')
    argParser.add_argument(
        "--deploy-repo",
        type=str,
        required=False,
        help="deploy plan file path for a repository to deploy"
    )
    argParser.add_argument(
        "--host",
        type=str,
        required=False,
        help="hostname of the container to perform action"
    )
    argParser.add_argument(
        "--workdir",
        type=str,
        required=False,
        default="/sardines/shoal",
        help="workdir for executing commands on the container"
    )
    args = argParser.parse_args()

    if args.deploy_repo and args.host:
        deploy_repository(args.host, args.deploy_repo, args.workdir)

