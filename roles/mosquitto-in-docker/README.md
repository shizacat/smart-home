Mosquitto MQTT Broker Role
==========================

Ansible role that installs and configures Mosquitto MQTT broker as a systemd service running in a Docker container.

## Overview

This role sets up Mosquitto MQTT broker using the official Eclipse Mosquitto Docker image, managed by systemd. It provides:

- Systemd service management with automatic restarts
- Docker container deployment for easy updates and isolation
- Persistent configuration, data, and log storage
- Secure authentication with user/password protection

## Requirements

- Docker installed on the target system
- Ansible 2.9 or higher

## Role Variables

### Default Variables (defaults/main.yml)
```yaml
mosquitto_u_user: user          # Default username
mosquitto_u_password: user      # Default password
mosquitto_listen: "127.0.0.1"  # Listen address
mosquitto_port: "1883"         # MQTT port
```

### Internal Variables (vars/main.yml)
```yaml
mosquitto_user: mosquitto           # System user
mosquitto_image_repo: eclipse-mosquitto  # Docker image
mosquitto_image_tag: 2.0.10         # Image version
docker_bin_dir: /usr/bin            # Docker binary location
bin_dir: /usr/local/bin             # Scripts location
```

## Usage

Include the role in your playbook:

```yaml
- hosts: mqtt_servers
  roles:
    - mosquitto
```

### Custom Configuration

Override default variables:

```yaml
- hosts: mqtt_servers
  roles:
    - role: mosquitto
      vars:
        mosquitto_u_user: "admin"
        mosquitto_u_password: "secure_password"
        mosquitto_listen: "0.0.0.0"
        mosquitto_port: "1883"
```

## Service Management

The role creates a systemd service (`mosquitto.service`) that:
- Starts the Mosquitto Docker container
- Automatically restarts on failure
- Manages container lifecycle
- Provides proper logging and monitoring

### Service Commands
```bash
# Start service
sudo systemctl start mosquitto

# Stop service  
sudo systemctl stop mosquitto

# Check status
sudo systemctl status mosquitto

# View logs
sudo journalctl -u mosquitto -f
```

## Files and Directories

- `/etc/mosquitto/` - Configuration files
- `/var/lib/mosquitto/` - Persistent data
- `/var/log/mosquitto/` - Log files
- `/etc/systemd/system/mosquitto.service` - Systemd service
- `/usr/local/bin/mosquitto` - Docker wrapper script

## License

MIT

## Author Information

This role was created for smart home MQTT broker deployment.
