# python3
import argparse
import json
import logging
import os
import sys
import time
from typing import Any, Final

import requests
import yaml

import wizard

ENCODING: Final[str] = "utf-8"
APP_NAME: Final[str] = 'atlassian-backup'
APP_VERSION: Final[str] = '0.1'

CONFIG_FILE: Final[str] = 'config.yaml'


class Atlassian:
    def __init__(self, config) -> None:
        self.config = config
        self.session = requests.Session()
        self.session.auth = (config['ATLASSIAN_EMAIL'], config['API_TOKEN'])
        self.session.headers.update(
            {'Content-Type': 'application/json', 'Accept': 'application/json'})
        self.payload = {
            "cbAttachments": self.config['INCLUDE_ATTACHMENTS'], "exportToCloud": "true"}
        self.start_confluence_backup = f"https://{self.config['ATLASSIAN_TENANT']}/wiki/rest/obm/1.0/runbackup"
        self.start_jira_backup = f"https://{self.config['ATLASSIAN_TENANT']}/rest/backup/1/export/runbackup"
        self.backup_status: dict = {}
        self.wait = 10

    def create_confluence_backup(self) -> str:
        backup = self.session.post(
            self.start_confluence_backup, data=json.dumps(self.payload))
        if backup.status_code != 200:
            raise Exception(backup, backup.text)
        else:
            print('-> Backup process successfully started')
            confluence_backup_status = f"https://{self.config['ATLASSIAN_TENANT']}/wiki/rest/obm/1.0/getprogress"
            time.sleep(self.wait)
            while 'fileName' not in self.backup_status.keys():
                self.backup_status = json.loads(
                    self.session.get(confluence_backup_status).text)
                print(
                    f"Current status: {self.backup_status['alternativePercentage']}; {self.backup_status['currentStatus']}")
                time.sleep(self.wait)
            return f"https://{self.config['ATLASSIAN_TENANT']}/wiki/download/{self.backup_status['fileName']}"

    def create_jira_backup(self) -> str:
        backup = self.session.post(
            self.start_jira_backup, data=json.dumps(self.payload))
        if backup.status_code != 200:
            raise Exception(backup, backup.text)
        else:
            task_id = json.loads(backup.text)['taskId']
            print(f'-> Backup process successfully started: taskId={task_id}')
            jira_backup_status = f"https://{self.config['ATLASSIAN_TENANT']}/rest/backup/1/export/getProgress?taskId={task_id}"
            time.sleep(self.wait)
            while 'result' not in self.backup_status.keys():
                self.backup_status = json.loads(
                    self.session.get(jira_backup_status).text)
                print(
                    f"Current status: {self.backup_status['status']} {self.backup_status['progress']}; {self.backup_status['description']}")
                time.sleep(self.wait)
            return f"https://{self.config['ATLASSIAN_TENANT']}/plugins/servlet/{self.backup_status['result']}"

    def download_file(self, url, local_filename) -> None:
        print(f'-> Downloading file from URL: {url}')
        r = self.session.get(url, stream=True)
        file_path = os.path.join(os.path.dirname(
            os.path.abspath(__file__)), 'backups', local_filename)
        with open(file_path, 'wb') as file_:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    file_.write(chunk)
        print(file_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('-w', action='store_true',
                        dest='wizard', help='activate config wizard')
    parser.add_argument('-c', action='store_true',
                        dest='confluence', help='activate confluence backup')
    parser.add_argument('-j', action='store_true',
                        dest='jira', help='activate jira backup')
    if parser.parse_args().wizard or (os.path.exists(os.path.join(get_root_dir(), CONFIG_FILE)) == False):
        wizard.create_config()

    config = read_config()

    if config['ATLASSIAN_TENANT'] == 'something.atlassian.net':
        raise ValueError(
            'You forgot to edit config.json or to run the backup script with "-w" flag')

    print(
        f"-> Starting backup; include attachments: {config['INCLUDE_ATTACHMENTS']}")
    atlass = Atlassian(config)
    if parser.parse_args().confluence:
        backup_url = atlass.create_confluence_backup()
    else:
        backup_url = atlass.create_jira_backup()

    print(f'-> Backup URL: {backup_url}')
    file_name = f"{time.strftime('%d%m%Y_%H%M')}_{backup_url.split('/')[-1].replace('?fileId=', '')}.zip"
    atlass.download_file(backup_url, file_name)


def get_root_dir() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    elif __file__:
        return os.path.dirname(__file__)
    else:
        return './'


def read_config() -> Any:
    config_path = os.path.join(get_root_dir(), CONFIG_FILE)
    with open(config_path, 'r') as config_file:
        return yaml.full_load(config_file)


if __name__ == "__main__":
    try:
        logging.basicConfig(filename=os.path.join(get_root_dir(), f'{APP_NAME}.log'),
                            encoding=ENCODING,
                            format='%(asctime)s:%(levelname)s:%(message)s',
                            datefmt="%Y-%m-%dT%H:%M:%S%z",
                            level=logging.INFO)

        excepthook = logging.error
        logging.info('Starting')
        main()
        logging.info('Exiting.')
    except KeyboardInterrupt:
        print('Cancelled by user.')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
    except Exception as ex:
        print(f'ERROR: {str(ex)}')
        try:
            sys.exit(1)
        except SystemExit:
            os._exit(1)
