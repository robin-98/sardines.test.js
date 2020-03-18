#!/usr/bin/env python3
from env.lib.network_builder import create_networks
from env.lib.image_builder import build_images
from env.lib.container_builder import build_containers
from env.lib.db_builder import create_postgres_databases
from env.sardines import deploy_repository
from env.sardines import deploy_agent
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
    agentHostList: list = None
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
            build_containers(containerConfFile)
            for dbConfFile in dbConfFileList:
                create_postgres_databases(dbConfFile)
            print('test envrionment has been set at [{}] level'.format(EnvLevels[step]))
        elif step == 1:
            print('begin to deploy repositories')
            for i in range(min(len(repoDeployFileList), len(repoHostList))):
                deploy_repository(repoHostList[i], repoDeployFileList[i])
            print('begin to deploy agents')
            for i in range(len(agentHostList)):
                deploy_agent(agentHostList[i], repoHostList[0])
            print('test envrionment has been set at [{}] level'.format(EnvLevels[step]))
            pass
        elif step == 2:
            pass
        else:
            pass


if __name__ == '__main__':
    import argparse
    argParser = argparse.ArgumentParser(description='orchestrate a test')
    argParser.add_argument(
        '--level',
        type=str,
        required=False,
        default='sardines',
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
        type=str,
        required=False,
        default="./conf/env/db-postgres-test.json,./conf/env/db-postgres-dev.json",
        help='database configuration files, seperated by ","'
    )
    argParser.add_argument(
        '--config-repo',
        type=str,
        required=False,
        default="./conf/env/deploy-repository-1.json",
        help='repository deploy plan files, seperated by ","'
    )
    argParser.add_argument(
        '--repo-hosts',
        type=str,
        required=False,
        default="nw-test-repo-1",
        help='repository hosts, seperated by ",", '
    )
    argParser.add_argument(
        '--agent-hosts',
        type=str,
        required=False,
        default="nw-test-client-1,nw-test-client-2,nw-test-client-3",
        help='repository hosts, seperated by ",", '
    )
    args = argParser.parse_args()
    beginTime = time.time()
    setupEnv(
        args.level,
        args.skip_level,
        args.config_networks,
        args.config_images,
        args.config_containers,
        args.config_db.split(","),
        args.config_repo.split(","),
        args.repo_hosts.split(","),
        args.agent_hosts.split(",")
    )
    endTime = time.time()
    print("Job done in {} seconds".format(round(endTime - beginTime, 1)))

