# dd-fping
Dadadog multi-target fping like smokeping

## requirements
- fping
- Datadog Agent v7+

## Installation
1. Install fping command
```
apt-get install fping
```

2. Allow fping executed by dd-agent user
```
chmod u+s `which fping`

```

2. Copy the files from this github repo to your host

```
  fping.py -> /etc/dd-agent/checks.d
  fping.yaml -> /etc/dd-agent/conf.d/fping.d
```

4. Test
```
datadog-agent version
  Agent 7.70.2 .....

sudo -u dd-agent fping -C2  -B1 -r1 -i10 -t 2000 127.0.0.1
sudo -u dd-agent datadog-agent check fping --log-level debug

systemctl restart datadog-agent
```

