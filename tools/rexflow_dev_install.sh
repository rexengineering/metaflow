#!/bin/bash

set -ex

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
rex-k8s-context docker-desktop

echo "Pulling docker images for your rexflow installation"

aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 355508092300.dkr.ecr.us-west-2.amazonaws.com

for image in {flowd,healthd,throw-gateway,catch-gateway,exclusive-gateway,parallel-gateway,passthrough-container} ; do
    docker pull 355508092300.dkr.ecr.us-west-2.amazonaws.com/rex/rexflow-${image}:istio.rex.sh
    docker tag 355508092300.dkr.ecr.us-west-2.amazonaws.com/rex/rexflow-${image}:istio.rex.sh ${image}
done

docker pull 355508092300.dkr.ecr.us-west-2.amazonaws.com/rex/istio-proxy:1.8.2-istio.rex.sh
docker tag 355508092300.dkr.ecr.us-west-2.amazonaws.com/rex/istio-proxy:1.8.2-istio.rex.sh rex-proxy:1.8.2


echo "About to install istio on your cluster. If this fails, download istioctl: 'ISTIO_VERSION=1.8.2 curl -L https://istio.io/downloadIstio | sh -'"
istioctl install -y --set profile=demo

echo "creating conda environment"
conda create --name rexflow python=3.8
source activate rexflow
pip install -r requirements.txt

echo "installing rexflow into your cluster"
python -m deploy create --kafka




echo "\n\n\n\n\n\n\n\n\n\n\n\n\n\nSuccess!"
