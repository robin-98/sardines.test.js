#!/usr/bin/env python3
import json
import os
import time
import tarfile
import docker
import sys
from env.lib.container_builder import copy_to_container

client = docker.from_env()

def create_postgres_databases(confFilePath:str = None, configuration: dict = None):
    configList = configuration
    execDir = os.path.dirname(sys.argv[0])
    dbScriptFile = "{}/env/lib/create_postgres_database.py".format(execDir)
    if not os.path.exists(dbScriptFile):
        raise Exception("Can not locate the script file [{}] for creating databases".format(dbScriptFile))

    if configuration is None \
        and ( confFilePath is None or not os.path.exists(confFilePath)):
        return

    workDir = "/sardines"
    tmpConfigFile = "./tmp_db_config.json"
    workUser = "postgres"
    workGroup = "postgres"
    try:
        if configList is None:
            with open(confFilePath) as f:
                configList = json.load(f)
        if type(configList) == dict:
            configList = [configList]
        elif type(configList) != list:
            raise Exception('Invalid configuration format') 

        # prepare the container cache
        containerCache = {}
        for inst in client.containers.list():
            containerCache[inst.name] = inst
        # process the configuration list
        targetDbScriptFile = "/sardines/create_postgres_database.py"
        targetConfigFile = "/sardines/db_config.json"
        for config in configList:
            if "type" not in config or "settings" not in config:
                continue
            if config["type"] != "postgres":
                continue
            settings = config["settings"]
            if "host" not in settings:
                continue
            if settings["host"] not in containerCache:
                continue
            inst = containerCache[settings["host"]]
            tmpConfig = config.copy()
            tmpConfig["settings"]["host"] = "localhost"
            with open(tmpConfigFile, "w") as f:
                json.dump(tmpConfig, f)
            (exit_code, output) = inst.exec_run(
                "mkdir -p {}".format(workDir)
            )
            if exit_code != 0:
                print(output)
                raise Exception('failed to create work directory at {} on container {}'.format(workDir, inst.name))

            copy_to_container(inst, dbScriptFile, targetDbScriptFile, mode="770", user = workUser, group = workGroup)
            copy_to_container(inst, tmpConfigFile, targetConfigFile, user = workUser, group = workGroup)
            (exit_code, output) = inst.exec_run(
                "{} --database-settings-file {}".format(targetDbScriptFile, targetConfigFile),
                user = workUser,
                stream = False
            )
            print(output.decode("utf8"))
            if exit_code != 0:
                raise Exception('failed to create database on container {}'.format(inst.name))
            else:
                print('database has been created on container {}'.format(inst.name))
    except Exception as e:
        print('Error when creating databases:', e)
        raise e
    finally:
        if os.path.exists(tmpConfigFile):
            os.remove(tmpConfigFile)

