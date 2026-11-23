"""Persist bubble visibility without old appearance-only clients resetting it."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from apps.Portal import app as portal


class UiSettingsTests(unittest.TestCase):
    def test_visibility_survives_reload_and_appearance_only_updates(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(
                portal, 'CONTROLPILOT_SETTINGS_PATH', Path(temporary) / 'settings.json'):
            with TestClient(portal.app) as client:
                initial = client.get('/api/settings').json()
                self.assertTrue(initial['notifications_bubble'])
                self.assertTrue(initial['copilot_bubble'])
                response = client.post('/api/settings/ui', json={
                    'theme': 'dark', 'sidebar_compact': False,
                    'notifications_bubble': False, 'copilot_bubble': False})
                self.assertEqual(response.status_code, 200, response.text)
                # Theme/sidebar controls and older clients omit the new fields.
                response = client.post('/api/settings/ui', json={'theme': 'light', 'sidebar_compact': True})
                self.assertEqual(response.status_code, 200, response.text)
                loaded = client.get('/api/settings').json()
                self.assertFalse(loaded['notifications_bubble'])
                self.assertFalse(loaded['copilot_bubble'])
                self.assertEqual(loaded['theme'], 'light')
                self.assertTrue(loaded['sidebar_compact'])
                response = client.post('/api/settings/ui', json={
                    'theme': 'light', 'sidebar_compact': True, 'copilot_bubble': True})
                self.assertTrue(response.json()['copilot_bubble'])
                self.assertFalse(response.json()['notifications_bubble'])
