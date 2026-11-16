#!/usr/bin/env python3
"""Host-only Cloudflare Access group sync. No API token enters the web container."""

import argparse
import json
import os
import re
import subprocess
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def api_request(url, token, method='GET', body=None):
    request = Request(url, method=method, data=json.dumps(body).encode() if body is not None else None,
                      headers={'Authorization': 'Bearer ' + token,
                               'Content-Type': 'application/json'})
    try:
        with urlopen(request, timeout=10) as response:
            answer = json.load(response)
    except (HTTPError, URLError, TimeoutError) as error:
        raise RuntimeError('Cloudflare group API request failed (%s).' % getattr(error, 'code', 'network')) from error
    if not answer.get('success') or not isinstance(answer.get('result'), dict):
        raise RuntimeError('Cloudflare rejected the group request.')
    return answer['result']


def desired_emails():
    command = ['docker', 'compose', '-f', 'compose.yaml', '-f', 'compose.tunnel.yaml',
               'exec', '-T', 'app', 'python', 'manage.py', 'access_group_members']
    run = subprocess.run(command, check=True, capture_output=True, text=True)
    result = json.loads(run.stdout)
    emails = result['emails']
    if not emails or any(not isinstance(email, str) or '@' not in email for email in emails):
        raise RuntimeError('Invalid Django collaborator list.')
    return sorted(set(email.casefold() for email in emails))


def sync(apply):
    account = os.environ.get('DND_CF_ACCOUNT_ID', '')
    group_id = os.environ.get('DND_CF_GROUP_ID', '')
    group_name = os.environ.get('DND_CF_GROUP_NAME', '')
    token = os.environ.get('DND_CF_API_TOKEN', '')
    if (not re.fullmatch(r'[0-9a-f]{32}', account) or
            not re.fullmatch(r'[0-9a-f-]{32,36}', group_id) or
            not group_name or not token):
        raise RuntimeError('Set host-private Cloudflare account, group, name and API token variables.')
    url = 'https://api.cloudflare.com/client/v4/accounts/%s/access/groups/%s' % (account, group_id)
    group = api_request(url, token)
    if group.get('name') != group_name:
        raise RuntimeError('The configured group ID does not match the dedicated D&D Tools group name.')
    includes = group.get('include', [])
    if any(set(rule) != {'email'} or not isinstance(rule['email'], dict)
           for rule in includes):
        raise RuntimeError('The dedicated group contains non-email rules; refusing to modify it.')
    wanted = desired_emails()
    current = sorted(rule['email']['email'].casefold() for rule in includes)
    print('D&D Tools Access group: %d current, %d desired members.' % (len(current), len(wanted)))
    if current == wanted:
        print('Already synchronized.')
        return
    if not apply:
        print('Dry run only; pass --apply on the VPS host to synchronize.')
        return
    payload = {'name': group_name, 'include': [{'email': {'email': email}} for email in wanted],
               'exclude': group.get('exclude', []), 'require': group.get('require', [])}
    api_request(url, token, method='PUT', body=payload)
    confirmed = api_request(url, token)
    actual = sorted(rule['email']['email'].casefold() for rule in confirmed.get('include', []))
    if actual != wanted:
        raise RuntimeError('Group update returned an unexpected membership.')
    print('Cloudflare Access group synchronized and verified.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Write and verify the group update')
    args = parser.parse_args()
    try:
        sync(args.apply)
    except (RuntimeError, subprocess.CalledProcessError, ValueError, KeyError) as error:
        print('Access sync failed: %s' % error, file=sys.stderr)
        sys.exit(1)
