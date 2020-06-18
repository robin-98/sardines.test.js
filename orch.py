#!/usr/bin/env python3
from env.lib.network_builder import create_networks
from env.lib.image_builder import build_images
from env.lib.container_builder import build_containers
from env.lib.db_builder import create_postgres_databases
from env.sardines import deploy_repository
from env.sardines import deploy_agent
from env.lib.utils import exec_cmd
import time

EnvLevels = ["infrastructure", "sardines", "services"]

def setupEnv(
    level:str = None,
    skipLevel: str = None,
    networkConfFile: str = None,
    imageConfFile: str = None,
    containerConfFile: str = None,
    dbConfFileList: list = None,
    repoDeployFileList: list = None,
    repoHostList: list = None,
    agentHostList: list = None,
    ignoreCmdErr: bool = False
):
    """Only setup the environment for the future tests
    """
    if level is None or level not in EnvLevels:
        raise Exception('illegal level {}'.format(level))

    skipIndex = -1
    if skipLevel is not None and skipLevel in EnvLevels:
        skipIndex = EnvLevels.index(skipLevel)

    levelIndex = EnvLevels.index(level)
    for step in range(len(EnvLevels)):
        if step <= skipIndex:
            continue
        if step > levelIndex:
            break
        if step == 0:
            create_networks(networkConfFile)
            print('networks have been created')
            build_images(imageConfFile)
            print('images have been built')
            build_containers(containerConfFile, ignoreCmdErr = ignoreCmdErr)
            for dbConfFile in dbConfFileList:
                create_postgres_databases(dbConfFile)
            print('test envrionment has been set at [{}] level'.format(EnvLevels[step]))
        elif step == 1:
            print('begin to deploy repositories')
            for i in range(min(len(repoDeployFileList), len(repoHostList))):
                deploy_repository(repoHostList[i], repoDeployFileList[i], ignoreCmdErr = ignoreCmdErr)
            print('begin to deploy agents')
            for i in range(len(agentHostList)):
                deploy_agent(agentHostList[i], repoHostList[0], ignoreCmdErr = ignoreCmdErr)
            print('test envrionment has been set at [{}] level'.format(EnvLevels[step]))
            pass
        elif step == 2:
            print('begin to deploy services')
            if skipIndex < 1:
                print('waiting the deployment of agents for 60 more seconds')
                time.sleep(60)

            for host in args.agent_hosts:
                cmd = ''
                if 'agent' in host:
                    cmd = "deploy_service.py --repo-deploy-plan deploy-repository.json --hosts root@{} --application dietitian --tags test {}".format(host, host)
                # elif 'nginx' in host:
                #     cmd = "deploy_service.py --repo-deploy-plan deploy-repository.json --hosts root@{} --application sardines-built-in-services --services /access_point/nginx:* --tags test {}".format(host, host)

                exec_cmd(
                    args.repo_hosts[0], 
                    cmd, 
                    ignoreCmdErr = args.ignoreCmdErr, 
                    environment = ['PATH=./node_modules/.bin', 'PATH=./bin']
                )
            print('test envrionment has been set at [{}] level'.format(EnvLevels[step]))
        else:
            pass


if __name__ == '__main__':
    import argparse
    argParser = argparse.ArgumentParser(description='orchestrate a test')
    argParser.add_argument(
        '--level',
        type=str,
        required=False,
        default='services',
        help='set the test envrionment level: {}'.format(str.join(', ', EnvLevels))
    )
    argParser.add_argument(
        '--skip-level',
        type=str,
        required=False,
        help='skip levels below and including the specified level in the envrionment hierarchy: {}'.format(str.join(', ', EnvLevels))
    )
    argParser.add_argument(
        '--config-networks',
        type=str,
        required=False,
        default="./conf/env/networks.json",
        help='networks configuration file'
    )
    argParser.add_argument(
        '--config-images',
        type=str,
        required=False,
        default="./conf/env/images.json",
        help='images configuration file'
    )
    argParser.add_argument(
        '--config-containers',
        type=str,
        required=False,
        default="./conf/env/containers.json",
        help='containers configuration file'
    )
    argParser.add_argument(
        '--config-db',
        nargs="+",
        type=str,
        required=False,
        default=["./conf/env/db-postgres-test.json", "./conf/env/db-postgres-dev.json"],
        help='database configuration files, seperated by space'
    )
    argParser.add_argument(
        '--config-repo',
        nargs="+",
        type=str,
        required=False,
        default=["./conf/env/deploy-repository-1.json"],
        help='repository deploy plan files, seperated by space'
    )
    argParser.add_argument(
        '--repo-hosts',
        nargs="+",
        type=str,
        required=False,
        default=["nw-test-repo-1"],
        help='repository hosts, seperated by space'
    )
    argParser.add_argument(
        '--agent-hosts',
        nargs="+",
        type=str,
        required=False,
        default=["nw-test-client-1", "nw-test-client-2", "nw-test-client-3", "nw-test-nginx-1"],
        help='repository hosts, seperated by space'
    )
    argParser.add_argument(
        '--ignoreCmdErr',
        type=bool,
        required=False,
        default=False,
        help="stop custom commands if an error occure, it's useful to turn off when debugging those commands"
    )
    args = argParser.parse_args()

    beginTime = time.time()
    setupEnv(
        args.level,
        args.skip_level,
        args.config_networks,
        args.config_images,
        args.config_containers,
        args.config_db,
        args.config_repo,
        args.repo_hosts,
        args.agent_hosts,
        args.ignoreCmdErr
    )
    endTime = time.time()
    print("Job done in {} seconds".format(round(endTime - beginTime, 1)))

