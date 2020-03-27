#!/usr/bin/env bash

./env/sardines.py --action exec-cmd --cmd "lib/manager/manageRepository.js --create-account=dietitian-mobile:Dietitian@2019 deploy-repository.json" --ignoreCmdErr True --hosts nw-test-repo-1

./env/sardines.py --action exec-cmd --cmd "bin/deploy_service.py --repo-deploy-plan deploy-repository.json --hosts nw-test-client-1,nw-test-client-2,nw-test-client-3 --application dietitian" --ignoreCmdErr True --hosts nw-test-repo-1