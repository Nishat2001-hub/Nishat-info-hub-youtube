import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from src import approval
from src import main as factory
from src.state import History, StateError

class ApprovalTests(unittest.TestCase):
    def test_wrong_digest_never_reads_oauth_or_uploads(self):
        with patch('src.approval.bundle_digest', return_value='b'*64), patch('src.approval.youtube_upload.client') as client, patch('src.approval.report'):
            self.assertEqual(approval.main(['--approved-sha256', 'a'*64]), 1)
            client.assert_not_called()

    def test_digest_binds_video_and_metadata(self):
        with tempfile.TemporaryDirectory() as d, patch('src.approval.OUT', Path(d)):
            video, meta = Path(d)/'short.mp4', Path(d)/'metadata.json'
            video.write_bytes(b'video'); meta.write_text('{}')
            first = approval.bundle_digest()
            meta.write_text('{"title":"changed"}')
            self.assertNotEqual(first, approval.bundle_digest())
            meta.write_text('{}'); video.write_bytes(b'changed')
            self.assertNotEqual(first, approval.bundle_digest())

    def test_checkpoint_failure_prevents_upload(self):
        history = History()
        history.data['entries']['test'] = {'status':'rendered'}
        with tempfile.TemporaryDirectory() as d, patch('src.approval.OUT',Path(d)), patch('src.approval.bundle_digest',return_value='a'*64), patch('src.approval.History',return_value=history), patch.object(history,'load',return_value=history), patch.object(history,'mark',side_effect=StateError()), patch('src.approval.youtube_upload.client',return_value=object()), patch('src.approval.youtube_upload.upload_private') as upload, patch('src.approval.report'):
            (Path(d)/'metadata.json').write_text(json.dumps({'content_key':'test','privacyStatus':'private'}))
            self.assertEqual(approval.main(['--approved-sha256','a'*64]),1)
            upload.assert_not_called()

    def test_generation_never_uploads_with_credentials_present(self):
        history = History()
        metadata = {'duration_seconds':10,'voice_providers':['test'],'script_provider':'curated'}
        with patch('src.main.History',return_value=history), patch.object(history,'load',return_value=history), patch.object(history,'mark'), patch('src.main.render',return_value=metadata), patch('src.main.bundle_digest',return_value='a'*64), patch('src.main.report'), patch('src.youtube_upload.client') as client, patch('src.youtube_upload.upload_private') as upload:
            self.assertEqual(factory.main([]),0)
            client.assert_not_called(); upload.assert_not_called()

    def test_real_approved_artifact_uploads_once_and_blocks_repeat(self):
        history = History()
        history.data['entries']['test'] = {'status':'rendered'}
        with tempfile.TemporaryDirectory() as d, patch('src.approval.OUT',Path(d)), patch('src.approval.bundle_digest',return_value='a'*64), patch('src.approval.History',return_value=history), patch.object(history,'load',return_value=history), patch.object(history,'save'), patch('src.approval.youtube_upload.client',return_value=object()), patch('src.approval.youtube_upload.upload_private',return_value='id') as upload, patch('src.approval.youtube_upload.verify',return_value='processed'), patch('src.approval.report'):
            (Path(d)/'metadata.json').write_text(json.dumps({'content_key':'test','privacyStatus':'private'}))
            self.assertEqual(approval.main(['--approved-sha256','a'*64]),0)
            self.assertEqual(approval.main(['--approved-sha256','a'*64]),1)
            self.assertEqual(upload.call_count,1)
