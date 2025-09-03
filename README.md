# Smart Home

Intro

This is setup smart home on Raspberry Pi Zero W.
The HomeBridge as main application.

## Feature

- It contains intalled software: homebridge, zigbee2mqtt, mosquitto
- Support DHT sensors - Digital-Humidity-Temperature
- Enable UART (disable Linux serial console)

- Сервер времени (NTP) - systemd-timesyncd

# Setup

## Setting Raspberry Pi

### Install OS

[Raspberry Pi OS](https://www.raspberrypi.org/software/)

### Setup WiFi

### Enable SSH

## Run script ansible

### Prepea environment

You need to install package to local host: sshpass, python3-venv.

Requirements:
- python3
- uv

```bash
uv venv
uv pip install -r requirements.txt

# If usage 'uv' activation don't need
# . ./.venv/bin/activate

# don't install this (already in repository)
# uv run ansible-galaxy role install -r requirements.yml
# uv run ansible-galaxy collection install -r requirements.yml
```

### Setup

```bash
uv run ansible-playbook -i inventory playbook.yaml
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

## NTP

```bash
# Проверка состояния службы
timedatectl status
# Более подробная служебная информация
timedatectl timesync-status
```

https://wiki.archlinux.org/title/Systemd-timesyncd_(%D0%A0%D1%83%D1%81%D1%81%D0%BA%D0%B8%D0%B9)
