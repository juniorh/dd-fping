#!/usr/bin/env python3
import subprocess
import time
from hashlib import md5
from datadog_checks.base import AgentCheck

class FpingCheck(AgentCheck):
    def __init__(self, name, init_config, instances):
        super(FpingCheck, self).__init__(name, init_config, instances)
        self._basename = "fping"
        self._ping_timeout = float(self.init_config.get('ping_timeout', 2.0))
        self._check_interval = int(self.init_config.get('check_interval', 10))
        self._global_tags = self.init_config.get('tags', {})

    def _instance_tags(self, instance):
        tags = self._global_tags.copy()
        tags.update(instance.get('tags', {}))
        tags['dst_addr'] = instance['addr']
        return [f"{k}:{v}" for k, v in tags.items()]

    def check(self, instance):
        addr = instance.get('addr')
        if not addr:
            raise Exception("Missing required parameter: addr")

        tags = self._instance_tags(instance)
        fping = Fping([addr], self._ping_timeout)
        start_time = time.time()
        results = fping.run()
        elapsed = time.time() - start_time
        loss_cnt = 0
        total_cnt = 0
        for host, rtt in results.items():
            total_cnt += 1
            if rtt is None:
                loss_cnt += 1
            else:
                self.histogram(f"{self._basename}.rtt", rtt, tags=tags)

        # Send counts
        self.count(f"{self._basename}.total_cnt", total_cnt, tags=tags)
        self.count(f"{self._basename}.loss_cnt", loss_cnt, tags=tags)

        # Send an event if packet loss detected
        if loss_cnt > 0:
            self.event({
                'timestamp': int(time.time()),
                'event_type': self._basename,
                'msg_title': f"fping timeout for {addr}",
                'msg_text': f"ICMP timeout detected for {addr}, {loss_cnt}/{total_cnt} lost",
                'aggregation_key': md5(addr.encode()).hexdigest(),
                'tags': tags,
            })
        self.log.info(f"Checked {addr}, elapsed: {elapsed:.2f}s, loss: {loss_cnt}/{total_cnt}")

class Fping:
    def __init__(self, hosts, timeout):
        self._hosts = hosts
        self._timeout = int(float(timeout) * 1000)

    def run(self):
        result = {}
        try:
            ping = subprocess.Popen(
                ["fping", "-C1", "-q", "-B1", "-r1", "-i10", "-t", str(self._timeout)] + self._hosts,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        except OSError:
            raise Exception("Command not found: fping")
        _, error = ping.communicate()
        for line in error.splitlines():
            if ':' not in line:
                continue
            addr, rtt_info = line.split(':', 1)
            addr = addr.strip()
            rtt_info = rtt_info.strip()
            # support modern fping output: "8.8.8.8 : [0], 84 bytes, 10.2 ms"
            try:
                if 'ms' in rtt_info:
                    rtt_value = rtt_info.split()[-2]  # ambil angka sebelum 'ms'
                    result[addr] = float(rtt_value)
                else:
                    result[addr] = float(rtt_info)
            except (ValueError, IndexError):
                result[addr] = None
        if not result:
            raise Exception(f"Invalid addresses: {','.join(self._hosts)}")
        return result
