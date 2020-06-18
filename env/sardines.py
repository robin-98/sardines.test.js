#!/usr/bin/env python3
#
# Example of deploy service:
# ./sardines.py --action deploy-services --repo-host nw-test-repo-1 --repo-deploy-plan deploy-repository.json --hosts nw-test-nginx-1 --application sardines-built-in-services --services /access_point/nginx:setup --init-parameters ./sample_initParams/nginx_setup.json --tags test nginx
#

import docker
import os
import json
import sys
import time
if __name__ == "__main__":
    from lib.utils import copy_to_container
    from lib.utils import exec_cmd
else:
    from env.lib.utils import copy_to_container
    from env.lib.utils import exec_cmd

client = docker.from_env()

def deploy_repository(hostname: str = None, deployPlanFile: str = None, workdir:str = '/sardines/shoal', ignoreCmdErr: bool = False):
    try:
        beginTime = time.time()
        print('preparing deploy repository, caching container instances...')
        containerCache = {}
        for inst in client.containers.list():
            containerCache[inst.name] = inst
        print('container instances have been cached')
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
            stream = ignoreCmdErr,
            detach = True
        )
        endTime = time.time()
        if not ignoreCmdErr and exit_code != 0 and exit_code is not None:
            if type(output) == str:
                print('ERROR of deploying repository:', output, ", exit code:", exit_code)
            else:
                print('ERROR of deploying repository:', output.decode("utf8"), ", exit code:", exit_code)
            raise Exception("error when executing startRepo command on container")
        else:
            if ignoreCmdErr:
                for line in output:
                    print(line.decode("utf8"))
            elif type(output) == str:
                print(output)
            else:
                print(output.decode("utf8"))
            print("repository has been deployed on container {} in {} seconds".format(hostname, round(endTime - beginTime, 1)))
    except Exception as e:
        print('Error while deploying repository on container {}:'.format(hostname), e)
        raise e

def deploy_agent(agentHost: str = None, repoHost: str = None, workdir: str = "/sardines/shoal", ignoreCmdErr: bool = False):
    try:
        beginTime = time.time()
        print('preparing deploy repository, caching container instances...')
        containerCache = {}
        for inst in client.containers.list():
            containerCache[inst.name] = inst
        print('container instances have been cached')
        if agentHost is None or agentHost not in containerCache:
            raise Exception("invalid agent host {}".format(agentHost))
        if repoHost is None or repoHost not in containerCache:
            raise Exception("invalid repository host {}".format(repoHost))

        print("begin deploying agent on container {} from the repository {}".format(agentHost, repoHost))
        repoInst = containerCache[repoHost]
        (exit_code, output) = repoInst.exec_run(
            "./bin/deploy_host.py --repo-deploy-file ./deploy-repository.json --host-name {} --os-user root".format(agentHost),
            stream = ignoreCmdErr,
            workdir = workdir
        )
        endTime = time.time()
        if not ignoreCmdErr and exit_code != 0 and exit_code is not None:
            errMsg = "agent deployment on container {} failed, exit code: {}".format(agentHost, exit_code)
            print(errMsg)
            if type(output) == str:
                print("ERROR of deploying agent:", output)
            else:
                print("ERROR of deploying agent:", output.decode("utf8"))
            raise Exception(errMsg)
        else:
            if ignoreCmdErr:
                for line in output:
                    print(line.decode("utf8"))
            elif type(output) == str:
                print(output)
            else:
                print(output.decode("utf8"))
            print("agent deployed on container {} in {} seconds".format(agentHost, round(endTime - beginTime,1)))
            print("")
    except Exception as e:
        print('Error while deploying agent on container {}'.format(agentHost), e)
        raise e

def deploy_service(
    repoDeployPlanFilePath: str = 'deploy-repository.json',
    repoHost: str = None,
    targetHosts: list = None,
    application: str = None,
    services: list = None,
    tags: list = None,
    providerSettingsFile:str = None,
    initParamFile: str = None,
    ignoreCmdErr: bool = False,
    workdir: str = '/sardines/shoal',
    env: list = None,
    ):

    containerCache = {}
    for inst in client.containers.list():
        containerCache[inst.name] = inst
    print('container instances have been cached') 

    hoststr = ''
    for host in targetHosts:
        hoststr += 'root@' + host + ' '
    cmd = "deploy_service.py --repo-deploy-plan {} --hosts {} --application {}".format(
        repoDeployPlanFilePath, hoststr, application
    )
    if services is not None or len(services) != 0:
        cmd = "{} --services {}".format(cmd, ' '.join(services))
    if tags is not None or len(tags) != 0:
        cmd = "{} --tags {}".format(cmd, ' '.join(tags))
    
    if initParamFile is not None:
        exec_cmd(repoHost, 'mkdir -p {}/deployments'.format(workdir), ignoreCmdErr = ignoreCmdErr)
        targetFileName = '{}/deployments/initParams_{}_{}.json'.format(workdir, application, time.time())
        copy_to_container(containerCache[repoHost], initParamFile, targetFileName)
        cmd = "{} --init-parameters {}".format(cmd, targetFileName)
    if providerSettingsFile is not None:
        exec_cmd(repoHost, 'mkdir -p {}/deployments'.format(workdir), ignoreCmdErr = ignoreCmdErr)
        targetFileName = '{}/deployments/providerSettings_{}_{}.json'.format(workdir, application, time.time())
        copy_to_container(containerCache[repoHost], providerSettingsFile, targetFileName)
        cmd = "{} --providers {}".format(cmd, targetFileName)
    
    environment = env
    if env is None:
        environment = ['PATH=./node_modules/.bin', 'PATH=./bin']
    exec_cmd(
        repoHost, 
        cmd, 
        ignoreCmdErr = ignoreCmdErr, 
        workdir = workdir,
        environment = environment
    )

# Executed from command line
if __name__ == "__main__":
    import argparse
    argParser = argparse.ArgumentParser(description='build testing system and run test cases')
    argParser.add_argument(
        "--action",
        type=str,
        required=True,
        help="action to perform: deploy-repo, deploy-agents, deploy-services, exec-cmd"
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
        required=False,
        help="repository hostname of the container to perform DevOps actions"
    )
    argParser.add_argument(
        "--hosts",
        nargs = '+',
        type=str,
        required=False,
        help="hostname of the container to perform action, seperated by space"
    )
    argParser.add_argument(
        "--application",
        type=str,
        required=False,
        help="application to be deployed if action = 'deploy-services"
    )
    argParser.add_argument(
        "--services",
        nargs="+",
        type=str,
        required=False,
        help="services to be deployed if action = 'deploy-services"
    )
    argParser.add_argument(
        "--tags",
        nargs="+",
        type=str,
        required=False,
        help="tags of the services to be deployed if action = 'deploy-services"
    )
    argParser.add_argument(
        "--init-parameters",
        type=str,
        required=False,
        help="a json file containing the initialization parameters of the services to be deployed if action = 'deploy-services"
    )
    argParser.add_argument(
        "--provider-settings",
        type=str,
        required=False,
        help="a json file containing the initialization parameters of the services to be deployed if action = 'deploy-services"
    )
    argParser.add_argument(
        "--workdir",
        type=str,
        required=False,
        default="/sardines/shoal",
        help="workdir for executing commands on the container"
    )
    argParser.add_argument(
        "--cmd",
        type=str,
        required=False,
        help="command to execute on target hosts, which are defined by the argument --hosts"
    )
    argParser.add_argument(
        "--env",
        action = 'append',
        type=str,
        required=False,
        help="environment variable. Such as 'PATH=/usr/bin', this will append this line of PATH to existing PATH variable. For other variables, the value will be set directly no matter whether already exists or not"
    )
    argParser.add_argument(
        "--ignoreCmdErr",
        type=bool,
        required=False,
        default = False,
        help="if set true, will ignore any error on execution of commands"
    )
    args = argParser.parse_args()

    if args.action == "deploy-repo":
        if not args.repo_host:
            print("--repo-host is required")
            sys.exit(1)
        deploy_repository(args.repo_host, args.repo_deploy_plan, args.workdir, ignoreCmdErr = args.ignoreCmdErr)
    elif args.action == "deploy-agents":
        if not args.repo_host:
            print("--repo-host is required")
            sys.exit(1)
        if args.hosts:
            for host in args.hosts:
                deploy_agent(host, args.repo_host, args.workdir, ignoreCmdErr = args.ignoreCmdErr)
            print("all agents have been deployed")
    elif args.action == 'deploy-services':
        if not args.application:
            print("--application is required")
            sys.exit(1)
        else:
            deploy_service(
                args.repo_deploy_plan, 
                args.repo_host, 
                args.hosts, 
                args.application, 
                args.services, 
                args.tags, 
                args.provider_settings,
                args.init_parameters,
                args.ignoreCmdErr,
                args.workdir,
                args.env
            )
            print("services have been deployed on hosts [{}]".format(' '.join(args.hosts)))
    elif args.action == "exec-cmd":
        if args.cmd and args.hosts:
            for host in args.hosts:
                exec_cmd(host, args.cmd, workdir = args.workdir, ignoreCmdErr = args.ignoreCmdErr, environment = args.env)
            print("Command [{}] has been executed on host [{}]".format(args.cmd, args.hosts))
    else:
        print('action [{}] is not supported'.format(args.action))
        sys.exit(1)


