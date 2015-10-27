# cloudwatch-udp-socket-reporter

Reports UDP socket statistics to CloudWatch:

* `UdpRxSuccess`: datagrams read off sockets' receive buffers
* `UdpRxWrongPort`: incoming datagrams sent to UDP ports to which no socket
  was bound ("unknown port" in netstat)
* `UdpRxDropped`: datagrams which did not make it into a socket's receive
  buffer because the buffer was full

The metrics are reported under the `System/Linux` namespace
("Linux System" in the CloudWatch console).

## Limitations

* This parses the output from `netstat -su` on Ubuntu -- hopefully your
  platform's `netstat` will have similar output
* This measures across all ports and interfaces

Both of these could be corrected by changing the script to read
success/dropped from `/proc/net/udp` and `/proc/net/udp6`, which is the
recommended approach in *Systems Performance* by Brendan Gregg. But `netstat`
was more convenient and it includes the "unknown port" count.

## Usage

```
usage: cw_udp_socket_reporter.py [-h] [--region REGION] [--loop]
                                 [--to-cloudwatch] [--to-stdout] [--cw-asg]
                                 [--show-rates]
                                 [--rate-sample-time RATE_SAMPLE_TIME]
                                 --stats-file STATS_FILE [--loglevel LOGLEVEL]
                                 [--log-file LOG_FILE]
```

Note that `RATE_SAMPLE_TIME` (seconds) must be at least the length of time between
subsequent calls to the script if it's being called on a schedule. It's dual-purpose
for both the loop interval (when using `--loop`) and to know whether the change
in metric values since the last call would be reasonable to report for the expected
time interval given the actual time interval.

## Requirements & Installation

See setup.py for Python library dependencies (`install_requires`).
A simple setup for cron would be to copy the script file into
`/usr/local/bin` and install the dependencies from PyPI to the system's Python
(as opposed to a virtualenv).

This has only been tested with Python 2.7 but I think it should work with Python 3.

AWS credentials are configured through boto. It is recommended that you
put an IAM role on the EC2 instance, but
[boto has backup options](http://boto.readthedocs.org/en/latest/boto_config_tut.html).

IAM policy requirements:

* `autoscaling:Describe*`
* `ec2:Describe*`
* `cloudwatch:PutMetricData`

### Example crontab

```
* * * * * /usr/local/bin/watch_netstat_udp.py --stats-file /var/watch_netstat_udp_stats --to-cloudwatch --cw-asg --region us-east-1 --log-file /var/log/cw-udp-cron-applog.log --rate-sample-time 60
```

This assumes the crontab's user can read/write `/var/watch_netstat_udp_stats`
and `/var/log/cw-udp-cron-applog.log`.
