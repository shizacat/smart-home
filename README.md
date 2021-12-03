# Description

This is setup smart home on Raspberry Pi Zero W.
The HomeBridge as main application.

## Feature

- Enable UART and disable Linux serial console

# Setup

## Setting Raspberry Pi

### Install OS

[Raspberry Pi OS](https://www.raspberrypi.org/software/)

## Run script ansible

### Prepea environment

You need to install package to local host: sshpass, python3-venv.

```bash
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt

# don't install this (already in repository)
# ansible-galaxy role install -r requirements.yml
# ansible-galaxy collection install -r requirements.yml
```

### Setup

```bash
ansible-playbook -i inventory playbook.yaml
```

## Links

- [UART configuration](https://www.raspberrypi.org/documentation/configuration/uart.md)
- https://gist.github.com/carry0987/372b9fefdd8041d0374f4e08fbf052b1


# Maintance

## Homebridge and Co

```shell
# Show logs
journalctl -f -u homebridge.service
```

### Install plugin

```bash
npm install -g --save homebridge-mqttthing@latest
```

## Chrony

```console
# Check status
chronyc tracking
```
