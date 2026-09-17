# Host SSH Recovery Runbook

## Purpose and boundary

This runbook is for the owner/provider console after access is available. It is evidence-first. Do not apply a correction until the read-only diagnosis identifies its cause. It does not authorize deployment, rollback, migration, database changes, or production configuration changes.

## Read-only diagnosis

Run from the provider console and capture output without exposing secrets:

```bash
uptime
free -m
cat /proc/pressure/io
vmstat 5 3
iostat -xz 5 3                 # if installed
ps -eo state,pid,ppid,user,cmd | awk '$1 ~ /D/ {print}'
df -h
df -i
ps aux | grep -E '[s]shd|[c]odex'
loginctl list-sessions
getent passwd codex
journalctl -u ssh -n 100 --no-pager
journalctl -k --since '24 hours ago' --no-pager
tail -100 /var/log/auth.log 2>/dev/null
```

Also inspect filesystem responsiveness and Docker metadata without reading environment values:

```bash
timeout 10 stat / /opt /var/lib/docker
docker ps -a
docker stats --no-stream
```

## Diagnosis split

- Network and key authentication are already known to pass from Gates 052–053.
- The current failure is post-auth session/channel execution, which remains unclassified until the console evidence is available.
- Correlate any D-state, I/O PSI, kernel/storage errors, PAM failures, shell path, process limits, or session failures before selecting a correction.

## Recovery ordering

1. Preserve evidence and current runtime state.
2. Apply only the smallest cause-specific correction, with an explicit rollback path.
3. Re-test a bounded noninteractive command as `codex`.
4. Re-run the read-only host/storage Gate 051 checks.
5. Close operational release only after host metrics and application health remain stable.

Reboot is a last resort and requires a separate approval. Never use it to replace diagnosis.

## Lockout protection

Do not globally disable `PasswordAuthentication`, alter root access, change PAM/sshd/firewall settings, or remove keys until an independent owner/admin access path is proven and rollback is documented. Do not kill processes or restart services as an exploratory step.

## Security follow-up

After recovery, define a separate hardening gate for the previously observed brute-force activity (for example, rate limiting or Fail2ban). Do not execute hardening in this runbook.

## Prohibited in this gate

No deployment, image switch, migration, database mutation, environment/secret edit, Cloudflare/webhook change, volume cleanup, or changes to `mentor-bot` or the old rollback environment.
