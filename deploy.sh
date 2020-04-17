#!/bin/bash

set -ex

old=$(docker images --format  '{{index .Repository}}:{{index .Tag}}' | grep "myelinio/myelin-drift-detection:0.2." | cut -d"." -f3|uniq|sort -n|tail -n1)
new=$(( old+1 ))

old_version=0.2.${old}
new_version=0.2.${new}
echo "Migrating from ${old_version} to ${new_version}"
docker build -t myelinio/myelin-drift-detection:${new_version} -f Dockerfile.drift .
docker push  myelinio/myelin-drift-detection:${new_version}


old_version_sub=0.2.${old}
new_version_sub=0.2.${new}
sed -e "s|$old_version_sub|$new_version_sub|g" spark-task.yaml > /tmp/spark-task.yaml
mv /tmp/spark-task.yaml spark-task.yaml



kubectl -n myelin-app  delete --force -f spark-task.yaml || true
sleep 2

kubectl -n myelin-app delete po -l spark-role=driver || true
sleep 2

kubectl -n myelin-app  replace --force -f spark-task.yaml
