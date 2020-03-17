#!/usr/bin/env python3

import docker
import os
import json
import sys
import time
from lib.container_builder import copy_to_container

client = docker.from_env()
containerCache = {}
for inst in client.containers.list():
    containerCache[inst.name] = inst

def deploy_repository(hostname: str = None, deployPlanFile: str = None, workdir:str = '/sardines/shoal'):
    try:
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

def deploy_agent(agentHost: str = None, repoHost: str = None, workdir: str = "/sardines/shoal"):
    try:
        if agentHost is None or agentHost not in containerCache:
            raise Exception("invalid agent host {}".format(agentHost))
        if repoHost is None or repoHost not in containerCache:
            raise Exception("invalid repository host {}".format(repoHost))

        print("begin deploying agent on container {} from the repository {}".format(agentHost, repoHost))
        repoInst = containerCache[repoHost]
        (exit_code, output) = repoInst.exec_run(
            "./bin/deploy_host.py --repo-deploy-file ./deploy-repository.json --host-name {} --os-user root".format(agentHost),
            stream = False,
            workdir = workdir
        )
        if exit_code != 0:
            errMsg = "agent deployment on container {} failed, exit code: {}".format(agentHost, exit_code)
            print(errMsg)
            print(output.decode("utf8"))
            raise Exception(errMsg)
        else:
            print(output.decode("utf8"))
            print("agent deployed on container {}".format(agentHost))
            print("")
    except Exception as e:
        print('Error while deploying agent on container {}'.format(agentHost), e)
        raise e


if __name__ == "__main__":
    import argparse
    argParser = argparse.ArgumentParser(description='build testing system and run test cases')
    argParser.add_argument(
        "--action",
        type=str,
        required=True,
        help="action to perform: deploy-repo, deploy-agents, deploy-services"
    )
    argParser.add_argument(
        "--repo-deploy-plan",
        type=str,
        required=False,
        help="deploy plan file path for a repository to deploy"
    )
    argParser.add_argument(
        "--repo-host",
        type=str,
        required=True,
        help="repository hostname of the container to perform DevOps actions"
    )
    argParser.add_argument(
        "--hosts",
        type=str,
        required=False,
        help="hostname of the container to perform action, seperated by ','"
    )
    argParser.add_argument(
        "--workdir",
        type=str,
        required=False,
        default="/sardines/shoal",
        help="workdir for executing commands on the container"
    )
    args = argParser.parse_args()

    if args.action == "deploy-repo":
        deploy_repository(args.repo_host, args.repo_deploy_plan, args.workdir)
    elif args.action == "deploy-agents":
        if args.hosts:
            for host in args.hosts.split(','):
                deploy_agent(host, args.repo_host, args.workdir)
            print("all agents have been deployed")


