# Описание

Настройка сервера умного дома. За основу взят HomeBridge. В качестве железа - raspberry pi zero w.

## Зависимости

- https://github.com/geerlingguy/ansible-role-docker_arm@4.1.0

# Setup

## Setting Raspberry Pi

### Install OS

[Raspberry Pi OS](https://www.raspberrypi.org/software/)

### Enable UART and disable Linux serial console

By default, the primary UART is assigned to the Linux console.
If you wish to use the primary UART for other purposes,
you must reconfigure Raspberry Pi OS. This can be done by using **raspi-config**:

- Start raspi-config: `sudo raspi-config`.
- Select option 3 - Interface Options.
- Select option P6 - Serial Port.
- At the prompt Would you like a login shell to be accessible over serial? answer `No`
- At the prompt Would you like the serial port hardware to be enabled? answer `Yes`
- Exit raspi-config and reboot the Pi for changes to take effect.

## Run script ansible

Prepea environment:

You need to install package to local host: sshpass, python3-venv.

```bash
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt

# don't install this (already in repository)
# ansible-galaxy install geerlingguy.docker_arm
# ansible-galaxy install geerlingguy.pip
# ansible-galaxy collection install community.docker
```

Run script:

```bash
ansible-playbook -i inventory playbook.yaml
```

## Homebridge

### Install plagin

If he isn't install from UI, you will install inside docker container.

Enter into container and run:

```bash
npm install -g --save homebridge-mqttthing@latest
```

## Ссылки

- [UART configuration](https://www.raspberrypi.org/documentation/configuration/uart.md)
