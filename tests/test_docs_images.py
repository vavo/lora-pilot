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
        self.assertTrue(references, "Expected local documentation images to validate")
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
            ('  JaVaScRiPt:alert(1)  ', 'README.md', ''),
            ('java\tscript:alert(1)', 'README.md', ''),
            ('java\nscript:alert(1)', 'README.md', ''),
            ('\x00javascript:alert(1)', 'README.md', ''),
            ('vbscript:msgbox(1)', 'README.md', ''),
            ('blob:https://example.com/unsafe', 'README.md', ''),
            (' HTTPS://example.com/a.png ', 'README.md', 'HTTPS://example.com/a.png'),
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

    def test_assets_reject_symlink_escapes_but_keep_contained_links(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            docs = root / 'docs'
            assets = docs / 'assets'
            (assets / 'nested').mkdir(parents=True)
            sibling = docs / 'assets-private'
            sibling.mkdir()
            (sibling / 'secret.png').write_bytes(b'private-image')
            image = assets / 'nested' / 'a b.PNG'
            image.write_bytes(b'public-image')
            (assets / 'internal.png').symlink_to(image)
            (assets / 'escape.png').symlink_to(sibling / 'secret.png')
            (assets / 'linked-dir').symlink_to(sibling, target_is_directory=True)
            with patch.object(portal, '_docs_root_candidates', return_value=[docs]):
                for path in ['nested/a%20b.PNG', 'internal.png', 'nested%5ca%20b.PNG']:
                    with self.subTest(path=path):
                        response = self.client.get('/api/docs/assets/' + path)
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(response.content, b'public-image')
                for path in ['escape.png', 'linked-dir/secret.png',
                             '%2e%2e/assets-private/secret.png', '%252e%252e/secret.png',
                             'nested%00/secret.png']:
                    with self.subTest(path=path):
                        response = self.client.get('/api/docs/assets/' + path)
                        self.assertIn(response.status_code, (400, 404))
                        self.assertNotIn(b'private-image', response.content)

            escaped_docs = root / 'escaped-docs'
            escaped_docs.mkdir()
            (escaped_docs / 'assets').symlink_to(sibling, target_is_directory=True)
            with patch.object(portal, '_docs_root_candidates', return_value=[escaped_docs]):
                response = self.client.get('/api/docs/assets/secret.png')
                self.assertEqual(response.status_code, 404)
                self.assertNotIn(b'private-image', response.content)
