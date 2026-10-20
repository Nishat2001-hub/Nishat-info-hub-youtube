import os
import unittest
from unittest.mock import patch
from src import preflight, youtube_upload


class PreflightTests(unittest.TestCase):
    def test_missing_secrets_never_constructs_client(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(youtube_upload, 'client') as client, patch.object(preflight, 'report') as report:
            self.assertEqual(preflight.main(), 0)
            client.assert_not_called()
            self.assertEqual(report.call_args.args[0], 'needs_setup')

    def test_configured_credentials_only_verify_channel(self):
        values = {name: 'test' for name in youtube_upload.SECRET_NAMES}
        with patch.dict(os.environ, values, clear=True), patch.object(youtube_upload, 'client') as client, patch.object(youtube_upload, 'upload_private') as upload, patch.object(preflight, 'report') as report:
            self.assertEqual(preflight.main(), 0)
            client.assert_called_once_with()
            upload.assert_not_called()
            self.assertTrue(report.call_args.kwargs['channel_verified'])

    def test_auth_error_does_not_log_secret_exception(self):
        values = {name: 'test' for name in youtube_upload.SECRET_NAMES}
        with patch.dict(os.environ, values, clear=True), patch.object(youtube_upload, 'client', side_effect=RuntimeError('SECRET')), patch.object(preflight, 'report') as report:
            self.assertEqual(preflight.main(), 1)
            self.assertNotIn('SECRET', str(report.call_args))
