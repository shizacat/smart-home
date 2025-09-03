# Ansible mosquitto role

Mosquitto™ is an open source (EPL/EDL licensed) message broker that implements the MQTT protocol versions 3.1 and 3.1.1. MQTT provides a lightweight method of carrying out messaging using a publish/subscribe model. This makes it suitable for "Internet of Things" messaging such as with low power sensors or mobile devices such as phones, embedded computers or microcontrollers like the Arduino.

More information about Mosquitto can be found here:
[https://mosquitto.org/](https://mosquitto.org/)

This role installs Mosquitto on the target server using the `apt-get` package manager. It works for Ubuntu and Debian servers and was tested with the help of docker containers. In comparison to other Ansible role tests where Ansible runs inside the container and is connecting to localhost, I decided to use the [Ansible docker connection](http://docs.ansible.com/ansible/intro_inventory.html#non-ssh-connection-types) (`ansible_connection=docker`). The build which run at [Travis CI](https://travis-ci.org/pbonrad/ansible-mosquitto) uses this functionality.

See also:
* GitHub project with Dockerfiles:  [https://github.com/pbonrad/ansible-docker-base](https://github.com/pbonrad/ansible-docker-base)

## Example Playbook

An example playbook is included in the `test.yml` file. You can use `run.sh` for running a test locally, which starts a docker container as the target.

    - hosts: all
      roles:
         - role: ansible-mosquitto
