"""Offline checks for the host-only Access membership updater."""

import contextlib
import io
import unittest
from unittest.mock import patch

from scripts import sync_access_group


CONFIG = {
    'DND_CF_ACCOUNT_ID': 'a' * 32,
    'DND_CF_GROUP_ID': 'b' * 32,
    'DND_CF_GROUP_NAME': 'DND Tools Editors',
    'DND_CF_API_TOKEN': 'test-token',
}


class AccessGroupSyncTests(unittest.TestCase):
    @patch.dict('os.environ', CONFIG)
    @patch('scripts.sync_access_group.desired_emails', return_value=['owner@example.test'])
    @patch('scripts.sync_access_group.api_request')
    def test_only_dedicated_email_group_is_updated_and_verified(self, request, _emails):
        group = {'name': CONFIG['DND_CF_GROUP_NAME'], 'include': [],
                 'exclude': [], 'require': []}
        request.side_effect = [group, group, group, {**group, 'include': [
            {'email': {'email': 'owner@example.test'}}]}]
        with contextlib.redirect_stdout(io.StringIO()):
            sync_access_group.sync(False)
            self.assertEqual(request.call_count, 1)
            sync_access_group.sync(True)
        self.assertEqual(request.call_count, 4)
        self.assertEqual(request.call_args_list[2].kwargs['method'], 'PUT')
        self.assertEqual(request.call_args_list[2].kwargs['body']['include'], [
            {'email': {'email': 'owner@example.test'}}])

    @patch.dict('os.environ', CONFIG)
    @patch('scripts.sync_access_group.api_request', return_value={
        'name': CONFIG['DND_CF_GROUP_NAME'], 'include': [{'everyone': {}}]})
    def test_broad_group_rule_is_never_overwritten(self, request):
        with self.assertRaisesRegex(RuntimeError, 'non-email rules'):
            sync_access_group.sync(True)
        self.assertEqual(request.call_count, 1)


if __name__ == '__main__':
    unittest.main()
