#!/usr/bin/env python
import argparse
import datetime
import json
import logging
import re
import subprocess
import time


__version__ = '1.1.2'


logger = logging.getLogger(__name__)


r_recv = re.compile(' ([0-9]+) packets received')
r_wrong = re.compile(' ([0-9]+) packets to unknown port received')
r_miss = re.compile(' ([0-9]+) packet receive errors')


def get_args():
    desc = 'Report UDP packet statistics to stdout or CloudWatch.'
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('--region', help='AWS region (default: us-east-1)',
                        type=str, default='us-east-1')
    parser.add_argument('--loop', action='store_true')
    parser.add_argument('--to-cloudwatch', action='store_true')
    parser.add_argument('--to-stdout', action='store_true')
    parser.add_argument('--cw-asg', action='store_true',
                        help='report with Auto Scaling Group dimension')
    parser.add_argument('--show-rates', action='store_true')
    parser.add_argument('--rate-sample-time', type=float, default=20.,
                        help=('Either the loop interval (with --loop) or '
                              'cron interval if running from cron '
                              '(in seconds)'))
    parser.add_argument('--stats-file', type=str, required=True)
    parser.add_argument('--loglevel', type=str, default='WARN')
    parser.add_argument('--log-file', type=str, required=False)
    return parser.parse_args()


def gen_stats():
    ns = subprocess.check_output(['netstat', '-su'])
    return {
        'received': int(r_recv.search(ns).groups(0)[0]),
        'wrong': int(r_wrong.search(ns).groups(0)[0]),
        'missed': int(r_miss.search(ns).groups(0)[0]),
        'dt': datetime.datetime.now(),
    }


def save_stats(s, path):
    s = s.copy()
    s['dt'] = s['dt'].isoformat()
    with open(path, 'w') as outf:
        json.dump(s, outf)


def load_stats(path):
    import dateutil.parser
    try:
        with open(path, 'r') as inf:
            s = json.load(inf)
        s['dt'] = dateutil.parser.parse(s['dt'])
        return s
    except IOError:
        return None


def get_instance_id():
    import requests
    url = 'http://169.254.169.254/latest/meta-data/instance-id'
    return requests.get(url).content


def get_autoscaling_group_name(region):
    import boto.ec2
    c = boto.ec2.connect_to_region(region)
    instance_id = get_instance_id()
    reservations = c.get_all_instances(instance_ids=[instance_id])
    if len(reservations) == 0:
        logger.error('get_autoscaling_group_name: reservation not found')
        return None
    instances = reservations[0].instances
    if len(instances) == 0:
        logger.error('get_autoscaling_group_name: instance not found')
        return None
    tag = 'aws:autoscaling:groupName'
    if tag not in instances[0].tags:
        logger.error('get_autoscaling_group_name: tag not found')
        return None
    return instances[0].tags[tag]


def report_cw_put(cw, dt, received, wrong, missed, dim):
    cw.put_metric_data(
        namespace='System/Linux',
        name='UdpRxSuccess',
        value=received,
        unit='Count',
        timestamp=dt,
        dimensions=dim)
    cw.put_metric_data(
        namespace='System/Linux',
        name='UdpRxWrongPort',
        value=wrong,
        unit='Count',
        timestamp=dt,
        dimensions=dim)
    cw.put_metric_data(
        namespace='System/Linux',
        name='UdpRxDropped',
        value=missed,
        unit='Count',
        timestamp=dt,
        dimensions=dim)


def report_cw(args, dt, tdiff, received, wrong, missed):
    import boto.ec2.cloudwatch
    cw = boto.ec2.cloudwatch.connect_to_region(args.region)
    dim = {'InstanceId': get_instance_id()}
    report_cw_put(cw, dt, received, wrong, missed, dim)
    logging.info('reported instance stats to CloudWatch')
    if args.cw_asg:
        asg = get_autoscaling_group_name(args.region)
        if asg is None:
            logger.error('report_cw: Auto Scaling Group name not found, '
                         'not reporting to CloudWatch')
        else:
            dim = {'AutoScalingGroupName': asg}
            report_cw_put(cw, dt, received, wrong, missed, dim)
            logging.info('reported asg stats to CloudWatch')


def report_stdout(args, dt, tdiff, received, wrong, missed):
    if args.show_rates:
        print(
            '{} - {} qps receive - {} qps wrong port - {} qps miss'
            .format(
                dt,
                received / tdiff,
                wrong / tdiff,
                missed / tdiff))
    else:
        print('{} - {} qps receive - {} qps wrong port - {} qps miss'
              .format(dt, received, wrong, missed))


def report(args):
    s_prev = load_stats(args.stats_file)
    s = gen_stats()
    save_stats(s, args.stats_file)
    if not s_prev:
        logger.info(str(s['dt']) + ' can report stats in ' +
                    str(args.rate_sample_time) + 's')
        return
    tdiff = (s['dt'] - s_prev['dt']).total_seconds()
    if tdiff > args.rate_sample_time + 15.:
        logger.info(str(s['dt']) + ' can report stats in ' +
                    str(args.rate_sample_time) + 's')
        return
    received = s['received'] - s_prev['received']
    if received < 0:
        logger.error("received was < 0. old val: %s, new val: %s",
                     s_prev['received'], s['received'])
        return
    wrong = s['wrong'] - s_prev['wrong']
    if wrong < 0:
        logger.error("wrong was < 0. old val: %s, new val: %s",
                     s_prev['wrong'], s['wrong'])
        return
    missed = s['missed'] - s_prev['missed']
    if missed < 0:
        logger.error("missed was < 0. old val: %s, new val: %s",
                     s_prev['missed'], s['missed'])
        return
    if args.to_cloudwatch:
        report_cw(args, s['dt'], tdiff, received, wrong, missed)
    if args.to_stdout:
        report_stdout(args, s['dt'], tdiff, received, wrong, missed)


def main(args):
    if args.loop:
        while True:
            report(args)
            time.sleep(args.rate_sample_time)
    else:
        report(args)


if __name__ == '__main__':
    args = get_args()
    if args.log_file:
        logging.basicConfig(level=getattr(logging, args.loglevel),
                            filename=args.log_file)
    else:
        logging.basicConfig(level=getattr(logging, args.loglevel))
    try:
        main(args)
    except KeyboardInterrupt:
        print('')
