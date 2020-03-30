#!/usr/bin/env bash

# Create application account
./env/sardines.py --action exec-cmd --cmd "lib/manager/manageRepository.js --create-account=dietitian-mobile:Dietitian@2019 deploy-repository.json" --ignoreCmdErr True --hosts nw-test-repo-1

# Deploy services
./env/sardines.py --action exec-cmd --cmd 'bin/deploy_service.py --repo-deploy-plan deploy-repository.json --hosts root@nw-test-client-1 root@nw-test-client-2 root@nw-test-client-3 --application dietitian' --env 'PATH=./node_modules/.bin:./bin --tags test 20200330 auth tencent' --hosts nw-test-repo-1

# Remove service runtimes
./env/sardines.py --action exec-cmd --cmd 'lib/manager/manageRepository.js --remove-service-runtimes --hosts=root@nw-test-client-1,root@nw-test-client-2,root@nw-test-client-3 --application=dietitian deploy-repository.json' --env 'PATH=./node_modules/.bin:./bin' --hosts nw-test-repo-1

# Re-build repository container
./env/env.py --build-containers ./conf/env/containers.json --hosts nw-test-repo-1

# Deploy repository
./env/sardines.py --action deploy-repo --repo-deploy-plan ./conf/env/deploy-repository-1.json --repo-host nw-test-repo-1