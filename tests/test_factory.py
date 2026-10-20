import base64
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from src.content import validate, select, duplicate, Exhausted
from src.state import History, StateError
from src import main as factory
from src import youtube_upload as upload
from src.common import ROOT


class CatalogTests(unittest.TestCase):
    def test_entire_catalog_valid_and_no_repeat_when_exhausted(self):
        topics = json.loads((ROOT / 'data/topics.json').read_text())
        entries = {}
        with patch.dict(os.environ, {'GEMINI_API_KEY': ''}):
            for _ in topics:
                topic, _ = select(entries, '2026-10-14')
                self.assertFalse(duplicate(topic, entries))
                entries[topic['key']] = topic
            with self.assertRaises(Exhausted):
                select(entries, '2026-10-15')
        self.assertEqual(len(entries), len(topics))

    def test_ai_failure_falls_back_without_leaking_exception(self):
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'not-a-real-key'}), \
             patch('src.content.ai_topic', side_effect=RuntimeError('SECRET')):
            topic, warning = select({}, '2026-10-14')
        self.assertEqual(topic['provider'], 'curated')
        self.assertNotIn('SECRET', warning)

    def test_similar_scripts_blocked(self):
        topic = validate(json.loads((ROOT / 'data/topics.json').read_text())[0])
        self.assertTrue(duplicate(topic, {'other': {'script': topic['script'] + ' ', 'title': 'other'}}))


class HistoryTests(unittest.TestCase):
    def test_repository_api_endpoint_has_no_trailing_slash(self):
        import io
        history = History()
        history.repo, history.token = 'owner/repo', 'test-only'
        with patch('urllib.request.urlopen', return_value=io.BytesIO(b'{"default_branch":"main"}')) as request:
            self.assertEqual(history.api('GET', '')['default_branch'], 'main')
            self.assertEqual(request.call_args.args[0].full_url, 'https://api.github.com/repos/owner/repo')

    def test_corrupt_local_history_is_not_ignored(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'GITHUB_ACTIONS': ''}):
            path = Path(directory) / 'history.json'
            path.write_text('{"version":1,"entries":{"key":{"status":"unknown"}}}')
            with self.assertRaises(StateError):
                History(path).load()

    def test_missing_history_on_existing_branch_is_not_reset(self):
        import urllib.error
        history = History()
        history.remote = True
        missing = urllib.error.HTTPError('https://api.github.com/', 404, 'Not Found', {}, None)
        with patch.object(history, 'api', side_effect=[missing, {'object': {'sha': 'exists'}}]), patch.object(history, 'save') as save:
            with self.assertRaises(StateError):
                history.load()
            save.assert_not_called()

    def test_upload_intent_survives_restart(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'GITHUB_ACTIONS': ''}):
            path = Path(directory) / 'history.json'
            history = History(path).load()
            history.mark('test', 'uploading', day='2026-10-14')
            restarted = History(path).load()
            self.assertEqual(restarted.ambiguous(), ['test'])
            restarted.mark('test', 'uploaded', video_id='verified-id', privacy='private')
            self.assertEqual(History(path).load().ambiguous(), [])

    def test_lost_state_write_response_is_reconciled(self):
        history = History()
        history.remote = True
        history.data = {'version': 1, 'entries': {'key': {'status': 'uploading'}}}
        content = base64.b64encode(json.dumps(history.data).encode()).decode()
        with patch.object(history, 'api', side_effect=[TimeoutError(), {'content': content, 'sha': 'saved'}]):
            history.save()
        self.assertEqual(history.sha, 'saved')

    def test_state_conflict_is_never_overwritten(self):
        history = History()
        history.remote = True
        content = base64.b64encode(json.dumps({'different': True}).encode()).decode()
        with patch.object(history, 'api', side_effect=[RuntimeError(), {'content': content, 'sha': 'new'}]):
            with self.assertRaises(StateError):
                history.save()


class FakeRequest:
    def __init__(self):
        self.calls = 0
    def next_chunk(self, num_retries):
        self.calls += 1
        if self.calls == 1:
            return object(), None
        return None, {'id': 'private-id', 'status': {'privacyStatus': 'private'}}


class FakeYouTube:
    def __init__(self):
        self.request = FakeRequest()
        self.body = None
        self.inserts = 0
    def videos(self):
        return self
    def insert(self, **kwargs):
        self.body = kwargs
        self.inserts += 1
        return self.request


class UploadTests(unittest.TestCase):
    metadata = {'title': 'Title', 'description': 'Description', 'privacyStatus': 'private'}
    def test_resumes_same_insert_and_forces_private_without_notifications(self):
        youtube = FakeYouTube()
        with tempfile.NamedTemporaryFile() as file:
            file.write(b'x' * 10001)
            file.flush()
            video_id = upload.upload_private(youtube, self.metadata, file.name, media_factory=lambda *a, **k: k)
        self.assertEqual(video_id, 'private-id')
        self.assertEqual(youtube.inserts, 1)
        self.assertEqual(youtube.request.calls, 2)
        self.assertEqual(youtube.body['body']['status']['privacyStatus'], 'private')
        self.assertFalse(youtube.body['notifySubscribers'])
        self.assertTrue(youtube.body['media_body']['resumable'])

    def test_synthetic_or_public_upload_rejected_before_insert(self):
        youtube = FakeYouTube()
        for extra in ({'smoke_test': True}, {'test_render': True}, {'privacyStatus': 'public'}, {'privacyStatus': 'unlisted'}):
            with self.assertRaises(RuntimeError):
                upload.upload_private(youtube, {**self.metadata, **extra})
        self.assertEqual(youtube.inserts, 0)


class PipelineTests(unittest.TestCase):
    def test_ambiguous_history_blocks_even_render(self):
        history = History()
        history.data['entries']['key'] = {'status': 'uploading'}
        with patch('src.main.History', return_value=history), \
             patch.object(history, 'load', return_value=history), \
             patch('src.main.render') as render, patch('src.main.report'):
            self.assertEqual(factory.main([]), 1)
            render.assert_not_called()

    def test_completed_day_is_skipped(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        history = History()
        history.data['entries']['key'] = {'status': 'uploaded', 'day': datetime.now(ZoneInfo('Asia/Dhaka')).date().isoformat()}
        with patch('src.main.History', return_value=history), \
             patch.object(history, 'load', return_value=history), \
             patch('src.main.render') as render, patch('src.main.report'):
            self.assertEqual(factory.main([]), 0)
            render.assert_not_called()


if __name__ == '__main__':
    unittest.main()

