import os
import sys
import logging
import requests
from datetime import datetime
from subprocess import Popen, PIPE

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S',
    level=logging.INFO)

with open(".env", "r") as fp:
    for line in fp.readlines():
        tokens = line.strip().split('=')

        if len(tokens) == 2:
            logging.info(f"New environment variable: {tokens}")
            os.environ[tokens[0]] = tokens[1]

ifttt_key = os.environ.get("IFTTT_KEY", None)

if ifttt_key is None:
    logging.error("Environment variable 'IFTTT_KEY' is None.")
    exit(1)

def print_usage():
    print(f"Usage: python3 {sys.argv[0]} <source> <dest> <job_id>")

def send_telegram_event_message(event, *values):
    json_data = None
    req_uri = f'https://maker.ifttt.com/trigger/{event}/with/key/{ifttt_key}'

    if len(values) == 0:
        requests.post(req_uri)
    else:
        json_data = {f"value{i+1}": val for i, val in enumerate(values)}
        requests.post(req_uri, json=json_data)

    logging.info(f"Made request to {req_uri}")

    if json_data is not None:
        logging.info(f"with JSON data {json_data}\n")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print_usage()
        exit(1)

    source = sys.argv[1].strip()
    dest = sys.argv[2].strip()
    job_id = sys.argv[3].strip()

    move_old_files_to = "dated_files"
    options="--checksum --verbose --filter-from=/Users/sazak/scripts/cronjobs/filter_rules"

    dest_underlined = "_".join(list(filter(lambda x: x != "", source.split('/'))))
    dest_path = f"{dest}:RCLONE/{dest_underlined}"

    os.environ['PATH'] = "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

    logging.info(f"Will sync {source} to {dest_path}\n")

    send_telegram_event_message("rclone_job_started", job_id, datetime.now().ctime())

    p = Popen(["/Users/sazak/Documents/Dev/rclone_jobber/rclone_jobber.sh",
            source, dest_path, move_old_files_to, options, job_id],
            stdin=PIPE, stdout=PIPE, stderr=PIPE)

    outs, errs = p.communicate()
    finish_time = datetime.now().ctime()

    errs = errs.decode().strip()

    if errs != "":
        logging.error(f"An error occured in rclone jobber (stderr):")
        
        for line in errs.split("\n"):
            logging.error(line)

        send_telegram_event_message("rclone_job_error", job_id, errs, finish_time)
        exit(1)

    outs = outs.decode().strip().split("\n")

    if "ERROR" in outs[-1]:
        logging.error(f"An error occured in rclone jobber (stdout):")
        
        for line in outs:
            logging.error(line)

        send_telegram_event_message("rclone_job_error", job_id, outs[-1], finish_time)
        exit(1)

    send_telegram_event_message("rclone_job_ok", job_id, finish_time)