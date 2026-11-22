"""Batch orchestration for Kohya converters; no model weights or GPU needed."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from apps.Portal.services.lora_conversion import comparison_loras


def checkpoint(path, value=b'\0\0\0\0'):
    path.parent.mkdir(parents=True, exist_ok=True)
    header = json.dumps({'source.weight': {'dtype': 'F32', 'shape': [1], 'data_offsets': [0, 4]}}).encode()
    header += b' ' * (-len(header) % 8)
    path.write_bytes(len(header).to_bytes(8, 'little') + header + value)


def converter_environment(root):
    scripts = root / 'kohya/sd-scripts'
    networks = scripts / 'networks'
    networks.mkdir(parents=True, exist_ok=True)
    networks.joinpath('__init__.py').touch()
    source = '''import json,os
from pathlib import Path
def main(args):
    source = Path(args.src_path).read_bytes()
    size = int.from_bytes(source[:8], 'little')
    header = json.loads(source[8:8+size])
    header = {key.replace('source.', 'converted.'): value for key,value in header.items()}
    encoded = json.dumps(header).encode()
    encoded += b' ' * (-len(encoded) % 8)
    Path(args.dst_path).write_bytes(len(encoded).to_bytes(8,'little') + encoded + source[8+size:])
    with open('calls.txt','a') as log: log.write(str(os.getpid()) + '\\n')
'''
    for module in ['convert_anima_lora_to_comfy', 'convert_hunyuan_image_lora_to_comfy']:
        networks.joinpath(module + '.py').write_text(source)
    return {'KOHYA_ROOT': str(root / 'kohya'), 'TRAINPILOT_PYTHON_BIN': sys.executable}


class ConversionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.models = self.root / 'models'
        self.run = dict(id='a' * 32, spec={'family': 'hunyuan_image21'})
        self.names = ['ControlPilot/' + self.run['id'] + f'/epoch{i}.safetensors' for i in range(3)]
        for name in self.names:
            checkpoint(self.models / 'loras' / name)
        self.environment = converter_environment(self.root)

    def test_one_process_converts_all_checkpoints_and_reuses_cached_copies(self):
        original = {name: (self.models / 'loras' / name).read_bytes() for name in self.names}
        for family in ['anima', 'hunyuan_image21']:
            self.run['spec']['family'] = family
            with patch.dict('os.environ', self.environment):
                converted = comparison_loras(self.models, self.run, self.names)
                self.assertEqual(comparison_loras(self.models, self.run, self.names), converted)
            self.assertEqual([Path(name).name for name in converted], [Path(name).name for name in self.names])
            for name in converted:
                data = (self.models / 'loras' / name).read_bytes()
                size = int.from_bytes(data[:8], 'little')
                self.assertIn('converted.weight', json.loads(data[8:8+size]))
                self.assertEqual(data[8+size:], b'\0\0\0\0')
        calls = (self.root / 'kohya/sd-scripts/calls.txt').read_text().splitlines()
        self.assertEqual(len(calls), 6)
        self.assertEqual(len(set(calls[:3])), 1)
        self.assertEqual(len(set(calls[3:])), 1)
        self.assertEqual(original, {name: (self.models / 'loras' / name).read_bytes() for name in self.names})

    def test_changed_checkpoint_gets_a_new_copy_without_overwriting_the_old_one(self):
        with patch.dict('os.environ', self.environment):
            first = comparison_loras(self.models, self.run, self.names[:1])[0]
            checkpoint(self.models / 'loras' / self.names[0], b'\0\0\x80?')
            second = comparison_loras(self.models, self.run, self.names[:1])[0]
        self.assertNotEqual(first, second)
        self.assertTrue((self.models / 'loras' / first).exists())

    def test_conversion_failure_never_publishes_partial_checkpoints(self):
        tool = self.root / 'kohya/sd-scripts/networks/convert_hunyuan_image_lora_to_comfy.py'
        tool.write_text('def main(args):\n raise RuntimeError("conversion fixture failure")\n')
        before = hashlib.sha256((self.models / 'loras' / self.names[0]).read_bytes()).digest()
        with patch.dict('os.environ', self.environment), self.assertRaises(HTTPException):
            comparison_loras(self.models, self.run, self.names)
        self.assertEqual(list((self.models / 'loras/ControlPilot' / self.run['id'] / 'comfy').rglob('*.safetensors')), [])
        self.assertEqual(hashlib.sha256((self.models / 'loras' / self.names[0]).read_bytes()).digest(), before)

    def test_symlinked_conversion_cache_cannot_escape_the_model_library(self):
        outside = self.root / 'outside'; outside.mkdir()
        cache = self.models / 'loras/ControlPilot' / self.run['id'] / 'comfy'
        cache.symlink_to(outside, target_is_directory=True)
        with patch.dict('os.environ', self.environment), self.assertRaises(HTTPException):
            comparison_loras(self.models, self.run, self.names)
        self.assertEqual(list(outside.iterdir()), [])

    def test_lumina_uses_its_original_format_without_a_converter(self):
        self.run['spec']['family'] = 'lumina2'
        self.assertEqual(comparison_loras(self.models, self.run, self.names), self.names)
