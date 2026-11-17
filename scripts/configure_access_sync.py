#!/usr/bin/env python3
"""Configure the host-only Access group sync without exposing its API token in a shell command."""

import argparse
import getpass
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from sync_access_group import sync


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--account-id', required=True)
    parser.add_argument('--group-id', required=True)
    parser.add_argument('--group-name', default='DND Tools Collaborators')
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error('Run this setup as root on the D&D Tools VPS.')
    if not re.fullmatch(r'[0-9a-f]{32}', args.account_id):
        parser.error('Invalid Cloudflare account ID.')
    if not re.fullmatch(r'[0-9a-f-]{32,36}', args.group_id):
        parser.error('Invalid Cloudflare Access group ID.')
    if not re.fullmatch(r'[A-Za-z0-9 _.-]{1,100}', args.group_name):
        parser.error('Invalid Cloudflare Access group name.')

    repository = Path(__file__).resolve().parents[1]
    if repository != Path('/opt/dndtools') or not (repository / 'compose.tunnel.yaml').is_file():
        parser.error('Run the script from the deployed /opt/dndtools checkout.')
    token = getpass.getpass('Cloudflare API token (input hidden): ').strip()
    if not re.fullmatch(r'[A-Za-z0-9_-]{20,200}', token):
        parser.error('Invalid API token format.')

    os.environ.update(DND_CF_ACCOUNT_ID=args.account_id, DND_CF_GROUP_ID=args.group_id,
                      DND_CF_GROUP_NAME=args.group_name, DND_CF_API_TOKEN=token)
    os.chdir(repository)
    sync(False)  # Validate the token, group identity, rule shape and Django source first.

    private_dir = Path('/etc/dndtools')
    private_dir.mkdir(mode=0o700, exist_ok=True)
    if private_dir.is_symlink():
        parser.error('Refusing a symlinked private configuration directory.')
    os.chmod(private_dir, 0o700)
    config_path = private_dir / 'access-sync.env'
    if config_path.is_symlink():
        parser.error('Refusing a symlinked Access configuration file.')
    fd, temporary = tempfile.mkstemp(prefix='.access-sync-', dir=private_dir)
    try:
        with os.fdopen(fd, 'w', encoding='ascii') as config:
            for name in ('DND_CF_ACCOUNT_ID', 'DND_CF_GROUP_ID', 'DND_CF_GROUP_NAME', 'DND_CF_API_TOKEN'):
                value = os.environ[name]
                config.write('%s=%s\n' % (name, value))
        os.chmod(temporary, 0o600)
        os.replace(temporary, config_path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

    sync(True)
    for suffix in ('service', 'timer'):
        source = repository / 'scripts' / 'systemd' / ('dndtools-access-sync.' + suffix)
        target = Path('/etc/systemd/system') / source.name
        shutil.copyfile(source, target)
        os.chmod(target, 0o644)
    for command in (('systemctl', 'daemon-reload'),
                    ('systemctl', 'enable', '--now', 'dndtools-access-sync.timer')):
        subprocess.run(command, check=True, env={key: value for key, value in os.environ.items()
                                                 if key != 'DND_CF_API_TOKEN'})
    print('Access membership synchronized; timer enabled. The API token remains in the root-only VPS file.')


if __name__ == '__main__':
    main()
