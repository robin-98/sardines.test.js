#!/usr/bin/env bash

./env/sardines.py --action exec-cmd --cmd "lib/manager/manageRepository.js --create-account=dietitian-mobile:Dietitian@2019 deploy-repository.json" --ignoreCmdErr True --hosts nw-test-repo-1

./env/sardines.py --action exec-cmd --cmd 'bin/deploy_service.py --repo-deploy-plan deploy-repository.json --hosts root@nw-test-client-1 root@nw-test-client-2 root@nw-test-client-3 --application dietitian' --env 'PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:./node_modules/.bin:./bin' --hosts nw-test-repo-1