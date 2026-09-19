# BATCH 165 — New Server Read-Only Environment Inventory

Date: 2026-09-19
Target: 92.118.190.101 (`hamicard`)
Mode: Read-only inventory; no installation, deployment, configuration, or mutation performed.

## Verdict

`NEW_SERVER_CLEAN_FOR_PLANNING`

The host is a clean Ubuntu VM suitable for planning a multi-project deployment. It is not yet an application runtime and no project was found in the inspected standard paths.

## OS

- Operating system: Ubuntu 24.04.5 LTS (Noble)
- Kernel: Linux 6.8.0-86-generic
- Architecture: x86-64
- Virtualization: KVM
- Hostname: `hamicard`

## Resources

- CPU: 4 vCPU
- Memory: 7.7 GiB total, 7.1 GiB available at inventory time
- Swap: 1.0 GiB, unused
- Root filesystem: 58 GiB, 7.4 GiB used, 50 GiB available (13%)
- `/boot`: 881 MiB, 15% used
- EFI: 105 MiB, 6% used
- Block devices: single primary `vda` disk with standard boot partitions; no application data volumes detected

## Users and access

- Inventory SSH user: `antigravity`
- `antigravity`: uid 1001, primary group `antigravity`, member of `sudo` and `users`
- Existing interactive user: `myjafar` (uid 1000)
- No additional project service users were observed in the final account listing.

## Running services

Only base OS/VM services were observed, including SSH, systemd networking/resolution, journald, rsyslog, cron, unattended-upgrades, QEMU guest agent, and standard Ubuntu device/session services. No application service, reverse proxy, database, Redis, worker, or tunnel service was found.

## Listening ports

- TCP 22: SSH on IPv4 and IPv6
- Local DNS resolver ports 53 on loopback
- Local-only port 6011 on loopback/IPv6 loopback
- No public application port (8000, 80, 443, database, Redis) was listening.

## Docker

Docker is not installed (`docker: command not found`). Consequently, no Docker containers, networks, or volumes exist on this host.

## Existing project paths

- `/opt`: exists and is empty apart from `.` and `..`
- `/srv`: exists and is empty apart from `.` and `..`
- `/var/www`: absent
- No `ai-teacher` or other application directory was found in the inspected standard locations.

## SSH posture

The requested `sshd -T | grep ...` check returned no matching lines in the inventory session, so the effective values for `permitrootlogin`, `passwordauthentication`, and `pubkeyauthentication` remain **UNVERIFIED**. No SSH configuration was changed.

## Potential conflicts

No application-level port, Docker resource, project path, database, Redis instance, reverse proxy, or systemd application unit was detected. The only foreseeable shared-host concerns are the existing `myjafar` account, base OS services, and the single root filesystem; future projects must use isolated directories, users/services, Compose project names, networks, volumes, environment files, and explicit ports.

## Recommended isolation model

- One directory under `/opt/apps/<project>` per project.
- Dedicated service user where runtime permissions require it.
- Separate Compose project name, environment file, network, and named volumes.
- Explicit non-overlapping host ports and a separately reviewed edge/reverse-proxy plan.
- No system-wide package, SSH, firewall, daemon, or kernel changes without a dedicated approval gate.

## Mutation audit

- Package installation: none
- Docker installation: none
- Project creation or file transfer: none
- Deploy/rebuild/restart/reboot: none
- SSH/firewall/user/group changes: none
- Database creation or migration: none
- Cloudflare/webhook changes: none

## Gate status

`NEW_SERVER_CLEAN_FOR_PLANNING`

Gate 165 commit remains HOLD pending Commander review.
