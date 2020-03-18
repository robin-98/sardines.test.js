# Sardines Test

* ## Tools
    1. [Jenkins for CI and test workflows](https://jenkins.io)
    2. [Github/Gitlab for source code](https//github.com)
    3. [Jest for ReactNative Mobile Apps](https://jestjs.io)

* ## Envrionment preparation

  + ### About Docker

      - [Install on Ubuntu Server 18.04](https://docs.docker.com/install/linux/docker-ce/ubuntu/)
          - Install packages to allow apt to use a repository over HTTPS:
            ```
            sudo apt-get install \
              apt-transport-https \
              ca-certificates \
              curl \
              gnupg-agent \
              software-properties-common
            ```

          - Add Docker’s official GPG key:
            ```
            curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
            ```
          Verify that you now have the key with the fingerprint 9DC8 5822 9FC7 DD38 854A E2D8 8D81 803C 0EBF CD88, by searching for the last 8 characters of the fingerprint.

          - Verify the fingerprint: `sudo apt-key fingerprint 0EBFCD88`

          - Use the following command to set up the stable repository:
            ```
            sudo add-apt-repository \
               "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
               $(lsb_release -cs) \
               stable"
            ```

          - Update the apt package index: `sudo apt-get update`
          - Install the latest version of Docker Engine - Community and containerd, or go to the next step to install a specific version:
            ```
            sudo apt-get install docker-ce docker-ce-cli containerd.io
            ```

      - [Change docker data file location to a seperated disk](https://www.guguweb.com/2019/02/07/how-to-move-docker-data-directory-to-another-location-on-ubuntu/)
          - Stop docker service: `sudo systemctl stop docker`

          - Add a `daemon.json` file to directory `/etc/docker`, which content is:
            ```
            {
                "graph": "/path/to/new/docker/datafile/location"
            }
            ```

          - Move old docker datafile to new location:
            ```
            sudo mv /var/lib/docker /path/to/new/docker/datafile/location
            ```

          - Start docker service: `sudo systemctl start docker`

      - Add current user to `docker` group to use docker commands: `sudo usermod -aG docker ${USER}`

  + ### Install [`docker for python: docker-py`](https://docker-py.readthedocs.io)

      - Install `python3` and `python3-pip`: `sudo apt-get install python3 python3-pip`
      
      - Install `docker-py`: `pip3 install docker`

  + ### Mount shared directory to VM host if needed:
      
      - Install vm tools: `sudo apt-get install open-vm-tools-desktop`

      - mount shared directory: 

        ```
        mkdir -p $HOME/Shared
        /usr/bin/vmhgfs-fuse -o auto_unmount .host:/ $HOME/Shared
        ```


* ## Testing mechanism

    + ###triggers: Source code changes of modules
    
    + ### Sequence of testing
        1. **a request of test** is issued
        1. **test planner** generate a test plan according to **the configuration**
        1. **code packer** pack each module into temporary package according to their versions sepcified in the test plan
            - clone sepcified version source code
            - update the reference relations in `package.json` to the wantted versions
            - publish temporary packages to **local npm repository**
        1. **environment creator** prepare testing envrionment
            - check whether there is such an envrionment has been setup
            - clean up previous envrionment if needed
            - create a seperated and independent envrionment using docker contianers, including:
                - 1x **nginx server**, for http request forwarding
                - 2x **repository server**
                - 1x **redis server**, for cache storage
                - 1x **postgres server**, for database storage
                - 1x **kafka server**, for message queue service
                - 4x **virtual machine**, for deploying agents
                - 1x **log miner**, to save all logs
            - update npm repository to **local npm repository** for all containers
        1. **test engine**
            - prepare configurations
                - generate service configurations for redis, postgres, kafka, and logger
                - generate the **deploy-plan** for repositories
                - generate agent host list
            - setup **base system**, ***halt at any error***
                - deploy repositories
                - deploy agents
                - check heartbeats
            - run **test cases**, ***halt at any error***
                - deploying application
                - update services

* ## Road map of developing

    1. base version: [2020-3-9]
        - ignoring **local npm repisotyr**, using public npm repository
        - ignoring **test planner** and **code packer**, using fixed version `*`
        - for **envrionment creator**, using fixed network configuration and environment settings
        - ignoring **nginx server**, **kafka server**
        - mixing **redis server**, **postgres server**, **log miner**
        - using single node of **repository server**
        - using fixed configurations
    1. full version: later if needed

* ## Module Design

    + ### Environment Creator

        - #### Input:
            - image list:
                ```
                {
                    "image name": {
                        "tag name": {
                            dockerfile: "a docker file to create the docker image"
                        }
                    }
                }
                ```
            - container list: 

                ```
                [
                    {
                        image: "image_name:tag",
                        hostname: "hostname of the container",
                        networkInterfaces: [
                            {
                                network: "network name",
                                ipv4: "ipv4 address",
                                ipv6: "ipv6 address",
                                ports: "port number"
                            }
                        ]
                    }
                ]
                ```
            - network set:

                ```
                {
                    "network name": {
                        driver: "default: bridge, Driver to manage the Network",
                        ipv6: "true/false",
                        gateway: "IPv4 or IPv6 Gateway for the master subnet",
                        subnet: "Subnet in CIDR format that represents a network segment",
                        label: "default: network name"
                    }
                }
                ```

        - #### Output: a running envrionment with several running docker container instances

        - #### Verify
            - telnet exposed ports

    + ### Test Engine





    

