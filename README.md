# RU-WiFi

RU-WiFi is a small CLI tool that keeps your RU captive portal session alive. It checks the portal, logs in when needed, and can run in the background as a systemd service.

## Features

- `ru-wifi setup`, `ru-wifi login`, `ru-wifi status`, `ru-wifi service`
- Secure password storage in the system keyring (KWallet/Secret Service)
- File-based credentials as a fallback (600 permissions)
- Automatic checks on a configurable interval (default: 3 minutes)
- Optional systemd sleep and NetworkManager hooks

## Install

```bash
python -m pip install .
```

## Quick start

1. Save credentials:

```bash
ru-wifi setup
```

2. Check status manually:

```bash
ru-wifi status
```

3. Run one login attempt:

```bash
ru-wifi login
```

## Background service (systemd)

Copy the unit file and enable it:

```bash
mkdir -p ~/.config/systemd/user
cp systemd/ru-wifi.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now ru-wifi.service
```

For a system-wide service, copy the same unit to `/etc/systemd/system/` and run:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ru-wifi.service
```

If your `ru-wifi` binary lives outside `~/.local/bin`, update `ExecStart` in the unit file
to the full path (for example `/usr/bin/ru-wifi`).

## Wake/sleep hook

```bash
sudo cp systemd/ru-wifi-sleep /etc/systemd/system-sleep/ru-wifi
sudo chmod +x /etc/systemd/system-sleep/ru-wifi
```

## NetworkManager dispatcher hook

```bash
sudo cp systemd/ru-wifi-nm-dispatcher /etc/NetworkManager/dispatcher.d/90-ru-wifi
sudo chmod +x /etc/NetworkManager/dispatcher.d/90-ru-wifi
```

## Configuration

Config lives in:

- User: `~/.config/ru-wifi/config.ini`
- System: `/etc/ru-wifi/config.ini`

Default portal URLs and fields:

- Login URL: `http://local.ru.ac.bd/login`
- Status URL: `http://local.ru.ac.bd/status`
- Username field: `username`
- Password field: `password`

You can override these during setup:

```bash
ru-wifi setup --login-url http://local.ru.ac.bd/login \
  --status-url http://local.ru.ac.bd/status \
  --username-field username \
  --password-field password \
  --interval 180
```

Extra login fields are supported with `--extra-fields key=value,key2=value2`.

## Credential storage

By default, passwords go into the system keyring. If keyring access fails, RU-WiFi stores the password in a local file with `600` permissions.

To force file storage:

```bash
ru-wifi setup --store file
```

For system-wide storage, run:

```bash
sudo ru-wifi setup --system --store file
```

## Notes

- Use `ru-wifi service --interval 300` to override the default check interval at runtime.
- Create an alias if you want `RU-WIFI` as the command name.
