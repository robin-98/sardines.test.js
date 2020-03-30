#!/usr/bin/env python3

# Created on 3/6/2020, by Robin, robin@naturewake.com
import argparse
from lib.container_builder import build_containers
from lib.db_builder import create_postgres_databases
from lib.image_builder import build_images
from lib.network_builder import create_networks

# Execute from the command line
if __name__ == "__main__":

    argParser = argparse.ArgumentParser(description='create en envrionment for testing')
    argParser.add_argument('--build-images', type=str, required=False, help='Build image according to configuration file, which in JSON format with dockerfile addresses')
    argParser.add_argument('--create-networks', type=str, required=False, help='Create a custom network according to a configuration file, which in JSON format with all network settings')
    argParser.add_argument('--build-containers', type=str, required=False,
        help='Build container instances according to a configuration file, which in JSON format with all container settings')
    argParser.add_argument('--create-postgres-db', type=str, required=False,
        help='Build databases in container instances according to a configuration file, which in JSON format with all container settings')
    argParser.add_argument('--hosts', nargs="+", type=str, required=False, help="target host list, seperated by ','")
    argParser.add_argument('--ignoreCmdErr', type=bool, required=False, default=True, help="if set false, stop custom commands if an error occure")
    args = argParser.parse_args()

    if args.build_images is not None:
        build_images(args.build_images)
    
    if args.create_networks is not None:
        create_networks(args.create_networks)

    if args.build_containers is not None:
        build_containers(args.build_containers, hosts = args.hosts, ignoreCmdErr = args.ignoreCmdErr)

    if args.create_postgres_db is not None:
        create_postgres_databases(args.create_postgres_db)

