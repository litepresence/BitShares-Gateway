FROM ubuntu:focal

##
## BitShares Gateway
##
## build:
##   docker build -t bitshares-gateway .
##
## run: (development)
##   docker run -it --rm -p 4018:4018 --name BitSharesGateTest bitshares-gateway
##
## run: (production)
##   docker run -d -p 4018:4018 --restart=never --name BitSharesGateway bitshares-gateway
##
##  Note: restart policy is "never" until sure an automatic restart
##        wouldn't result in deposits intended for one recipient being
##        routed to another.
##
##  Config Files:
##
##    The config/ dir should contain files nodes.py and config.py customized
##    for the intended deployment.  These may be modeled after config-sample.py
##    and nodes-sample.py in the app/ directory.  The configpath argument may be
##    overridden at build time to pull config files from a different location.
##

ARG configpath=config

##
## Set up basic Python3 environment:
##

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y python3 \
    python3-pip python3-pkgconfig

##
## Install dependencies for BitShares Gateway:
##

WORKDIR /usr/src/init

COPY apt-packages.txt .
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y \
    $(grep -vE "^\s*#" apt-packages.txt  | tr "\n" " ")

COPY requirements.txt .
RUN pip3 install -r requirements.txt

##
## Install and configure BitShares Gateway app:
##

WORKDIR /usr/src/app
COPY app/ .
COPY $configpath/ .

RUN echo python3 -u Gateway.py >> ~/.bash_history
CMD ["bash"]
#CMD ["python3", "-u", "Gateway.py"]
