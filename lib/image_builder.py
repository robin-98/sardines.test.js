# module for building images
import json
import os
import time
import tarfile
import docker
import sys

client = docker.from_env()

def build_images(imgConfFile:str = None, configuration: dict = None, baseDir: str = None):
    """Build docker images

    argument list:
    imgConfFile: image configuration file path
    configuration: an already loaded dictionary object of the configuration file content
    baseDir: used to resolve the file path within the configuration dictionary
    """
    try:
        imgConf = configuration
        confBaseDir = '.'
        if baseDir is not None:
            confBaseDir = baseDir
        if imgConf is None and imgConfFile is not None:
            with open(imgConfFile) as f:
                imgConf = json.load(f)
                confBaseDir = os.path.dirname(imgConfFile)
        # get local images 
        localImages = client.images.list()
        localImageTags = []
        for img in localImages:
            localImageTags.extend(img.tags)
        # build images
        for imgName in imgConf.keys():
            for imgTag in imgConf[imgName].keys():
                conf = imgConf[imgName][imgTag]
                dockerfile = None
                if type(conf) == dict and conf["dockerfile"] is not None:
                    dockerfile = conf["dockerfile"]
                elif type(conf) == str:
                    dockerfile = conf
                if dockerfile is None:
                    raise Exception('invalid dockerfile for building image {}:{}'.format(imgName, imgTag))
                # Dcoker file path is dockerfile
                dockerfile = os.path.relpath(os.path.join(confBaseDir, dockerfile))
                if not os.path.exists(dockerfile):
                    raise Exception('dockerfile does not exist at {} for building image {}:{}'.format(dockerfile, imgName, imgTag))
                # check whether the image already exists
                tag = '{}:{}'.format(imgName, imgTag)
                if tag not in localImageTags:
                    with open(dockerfile, 'rb') as df:
                        (imgInst, log) = client.images.build(fileobj = df, tag = tag)
                    print(log)
                    print('docker image [{}] has been built'.format(tag))
    except Exception as e:
        print('Error when building image:', e)