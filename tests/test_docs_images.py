import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from apps.Portal import app as portal

ROOT = Path(__file__).resolve().parents[1]


class DocsImageTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(portal.app)
        self.addCleanup(self.client.close)
        auth = patch.object(portal, '_controlpilot_request_authenticated', return_value=True)
        auth.start()
        self.addCleanup(auth.stop)

    def resolve_images(self, references):
        if not shutil.which('node'):
            self.skipTest('Node.js is required for Docs renderer checks')
        script = '''
const fs = require('fs'), vm = require('vm');
const context = vm.createContext({window: {}});
vm.runInContext(fs.readFileSync('apps/Portal/static/js/docs.js', 'utf8'), context);
const refs = JSON.parse(fs.readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify(refs.map(([src, source]) =>
  context.sanitizeImageReference(src, source))));
'''
        return json.loads(subprocess.check_output(
            ['node', '-e', script], cwd=ROOT, input=json.dumps(references), text=True))

    def test_all_local_markdown_images_resolve_and_are_served(self):
        references = []
        for path in [ROOT / 'README.md', *(ROOT / 'docs').rglob('*.md')]:
            content = path.read_text()
            images = re.findall(r'!\[[^\]]*\]\(([^)]+)\)', content)
            images += re.findall(r'<img[^>]+src=["\']([^"\']+)', content)
            references.extend((src, path.relative_to(ROOT).as_posix())
                              for src in images if not src.startswith(('http:', 'https:', '//')))
        self.assertGreater(len(references), 20)
        with patch.object(portal, '_docs_root_candidates', return_value=[ROOT / 'docs']):
            for ref, url in zip(references, self.resolve_images(references)):
                with self.subTest(reference=ref, url=url):
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, 200)
                    self.assertTrue(response.headers['content-type'].startswith('image/'))
                    self.assertTrue(response.content)

    def test_image_resolution_keeps_external_urls_and_rejects_unsafe_schemes(self):
        cases = [
            ('../assets/images/a%20b.png?version=2#preview', 'docs/components/test.md',
             '/api/docs/assets/images/a%20b.png?version=2#preview'),
            ('/docs/assets/images/a.svg', 'docs/README.md', '/api/docs/assets/images/a.svg'),
            ('apps/Portal/static/logo.svg', 'README.md', '/logo.svg'),
            ('https://example.com/a.png', 'docs/test.md', 'https://example.com/a.png'),
            ('//example.com/a.png', 'docs/test.md', '//example.com/a.png'),
            ('/logo.svg', 'README.md', '/logo.svg'),
            ('javascript:alert(1)', 'README.md', ''),
            ('data:image/svg+xml,unsafe', 'README.md', ''),
            ('file:///etc/passwd', 'README.md', ''),
        ]
        self.assertEqual(self.resolve_images([row[:2] for row in cases]), [row[2] for row in cases])

    def test_assets_follow_docs_root_fallback_and_block_escape(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            primary, fallback = root / 'primary', root / 'fallback'
            (primary / 'assets').mkdir(parents=True)
            (fallback / 'assets').mkdir(parents=True)
            (fallback / 'assets' / 'diagram.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
            (root / 'private.png').write_bytes(b'private')
            (primary / 'assets' / 'escape.png').symlink_to(root / 'private.png')
            (primary / 'assets' / 'page.html').write_text('<script>alert(1)</script>')
            with patch.object(portal, '_docs_root_candidates', return_value=[primary, fallback]):
                response = self.client.get('/api/docs/assets/diagram.svg')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers['x-content-type-options'], 'nosniff')
                self.assertIn('sandbox', response.headers['content-security-policy'])
                for path in ['escape.png', 'page.html', '%2e%2e/private.png',
                             '%2fprivate.png', 'nested%5c..%5cprivate.png', 'C:private.png', 'missing.png']:
                    with self.subTest(path=path):
                        response = self.client.get('/api/docs/assets/' + path)
                        self.assertIn(response.status_code, (400, 404))
                        self.assertNotIn(b'private', response.content)

    def test_assets_keep_controlpilot_authentication(self):
        with patch.object(portal, '_controlpilot_request_authenticated', return_value=False):
            response = self.client.get('/api/docs/assets/images/learning-101/inference-101-overview.svg')
            self.assertEqual(response.status_code, 401)
