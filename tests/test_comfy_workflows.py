import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / 'config/comfy-workflows'


class ComfyWorkflowTests(unittest.TestCase):
    def test_official_workflows_are_intact_and_self_contained(self):
        provenance = json.loads((BUNDLE / 'provenance.json').read_text())
        self.assertEqual(len(provenance['files']), 4)
        for entry in provenance['files']:
            with self.subTest(workflow=entry['file']):
                raw = (BUNDLE / entry['file']).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), entry['sha256'])
                workflow = json.loads(raw)
                graphs = [workflow] + workflow.get('definitions', {}).get('subgraphs', [])
                subgraphs = {g['id'] for g in graphs[1:]}
                for graph in graphs:
                    node_ids = {n['id'] for n in graph['nodes']}
                    self.assertEqual(len(node_ids), len(graph['nodes']))
                    for boundary in ('inputNode', 'outputNode'):
                        if boundary in graph:
                            node_ids.add(graph[boundary]['id'])
                    for link in graph['links']:
                        origin, target = ((link['origin_id'], link['target_id'])
                                          if isinstance(link, dict) else (link[1], link[3]))
                        self.assertIn(origin, node_ids)
                        self.assertIn(target, node_ids)
                    for node in graph['nodes']:
                        properties = node.get('properties', {})
                        self.assertIn(properties.get('cnr_id', 'comfy-core'), ('comfy-core',))
                        if len(node['type']) == 36 and node['type'].count('-') == 4:
                            self.assertIn(node['type'], subgraphs)

    def test_services_do_not_inherit_core_packages(self):
        for service in ('invoke', 'ai-toolkit', 'kohya'):
            text = (ROOT / f'scripts/build/install-{service}.sh').read_text()
            self.assertNotIn('add_shared_core_site_packages', text)
            self.assertIn(f'/opt/venvs/{service}/bin/python -m pip check', text)
        helpers = (ROOT / 'apps/TrainPilot/helpers.sh').read_text()
        self.assertIn('/opt/venvs/kohya/bin/python', helpers)
