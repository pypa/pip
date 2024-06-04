FROM mcr.microsoft.com/devcontainers/base:ubuntu

RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
&& apt-get -y install --no-install-recommends subversion mercurial python3.10 python3.10-venv software-properties-common

# Bazaar install info: https://launchpad.net/~bzr/+archive/ubuntu/ppa
RUN add-apt-repository ppa:bzr/ppa -y
RUN apt-get -y install bzr 
