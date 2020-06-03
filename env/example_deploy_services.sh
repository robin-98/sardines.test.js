#!/usr/bin/env bash

# Create application account
./env/sardines.py --action exec-cmd --cmd "lib/manager/manageRepository.js --create-account=dietitian-mobile:Dietitian@2019 deploy-repository.json" --ignoreCmdErr True --hosts nw-test-repo-1

# Deploy services
./env/sardines.py --action exec-cmd --cmd 'bin/deploy_service.py --repo-deploy-plan deploy-repository.json --hosts root@nw-test-client-1 root@nw-test-client-2 root@nw-test-client-3 --application dietitian --tags test 20200330 auth tencent' --env 'PATH=./node_modules/.bin:./bin' --hosts nw-test-repo-1

# Remove service runtimes
./env/sardines.py --action exec-cmd --cmd 'lib/manager/manageRepository.js --remove-service-runtimes --hosts=root@nw-test-client-1,root@nw-test-client-2,root@nw-test-client-3 --application=dietitian deploy-repository.json' --env 'PATH=./node_modules/.bin:./bin' --hosts nw-test-repo-1

# Re-build repository container
./env/env.py --build-containers ./conf/env/containers.json --hosts nw-test-repo-1

# Deploy repository
./env/sardines.py --action deploy-repo --repo-deploy-plan ./conf/env/deploy-repository-1.json --repo-host nw-test-repo-1


# Re-build nginx container
./env/env.py --build-containers ./conf/env/containers.json --hosts nw-test-nginx-1

# Deploy agent on nginx
./env/sardines.py --action deploy-agents --repo-deploy-plan ./conf/env/deploy-repository-1.json --repo-host nw-test-repo-1 --hosts nw-test-nginx-1


# Deploy built-in-services on nginx
./env/sardines.py --action exec-cmd --cmd 'deploy_service.py --repo-deploy-plan deploy-repository.json --hosts root@nw-test-nginx-1 --application sardines-built-in-services --tags test 20200401 nginx built-in' --env 'PATH=./node_modules/.bin:./bin' --hosts nw-test-repo-1

# Remove built-in-services on nginx
./env/sardines.py --action exec-cmd --cmd 'lib/manager/manageRepository.js --remove-service-runtimes --hosts=root@nw-test-nginx-1 --application=sardines-built-in-services deploy-repository.json' --env 'PATH=./node_modules/.bin:./bin' --hosts nw-test-repo-1

# Test Nginx service using command line HTTP request
curl --header "Content-Type: application/json" --request POST --data '{"msg":"xyz"}' http://172.20.20.131:8080/sardines-built-in-services/gateway/nginx/echo

