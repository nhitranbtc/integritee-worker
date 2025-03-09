#!/usr/bin/env python3
"""
Launch handily a local dev setup consisting of some workers.

Example usage: `./local-setup/launch.py /local-setup/simple-config.py`

The workers logs are piped to `./log/worker1.log` etc. folder in the current-working dir.

run: `cd local-setup && tmux_logger.sh` to automatically `tail -f` these logs.
"""
import argparse
import json
import signal
from subprocess import STDOUT
from time import sleep
from typing import Union, IO

from py.worker import Worker
from py.helpers import GracefulKiller, mkdir_p

log_dir = 'log'
mkdir_p(log_dir)

def setup_worker(work_dir: str, source_dir: str, std_err: Union[None, int, IO]):
    print(f'Setting up worker in {work_dir}')
    print(f'Copying files from {source_dir}')
    worker = Worker(cwd=work_dir, source_dir=source_dir, std_err=std_err)
    worker.init_clean()
    print('Initialized worker.')
    return worker

def run_worker(config, i: int):
    log = open(f'{log_dir}/worker{i}.log', 'w+')
    w = setup_worker(f'tmp/w{i}', config["source"], log)

    print(f'Starting worker {i} in background')
    return w.run_in_background(log_file=log, flags=config["flags"], subcommand_flags=config["subcommand_flags"])

def main(processes, config_path):
    print('Starting workers in background')

    with open(config_path) as config_file:
        config = json.load(config_file)

    i = 1
    for w_conf in config["workers"]:
        processes.append(run_worker(w_conf, i))
        # sleep to prevent nonce clash when bootstrapping the enclave's account
        sleep(3)
        if i == 1:
            # Give worker 1 some time to register itself, otherwise key & state sharing will not work.
            sleep(60)
        i += 1

    # keep script alive until terminated
    signal.pause()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run a setup consisting of workers')
    parser.add_argument('config', type=str, help='Config for the workers')
    args = parser.parse_args()

    process_list = []
    killer = GracefulKiller(process_list)
    main(process_list, args.config)