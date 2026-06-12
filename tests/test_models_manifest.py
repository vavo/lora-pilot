import tempfile
import unittest
from pathlib import Path

from apps.Portal.services import models as models_service


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config" / "models.manifest"
REFERENCE_MANIFEST = ROOT / "config" / "models.manifest.default"


def manifest_entries(path):
    entries = {}
    with path.open() as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            name, kind, source, subdir, *rest = line.split("|")
            entries[name] = {
                "kind": kind,
                "source": source,
                "subdir": subdir,
                "include": rest[0] if rest else "",
                "size": rest[1] if len(rest) > 1 else "",
            }
    return entries


class ModelsManifestTests(unittest.TestCase):
    def test_shipped_manifest_contains_reference_manifest_entries(self):
        shipped = manifest_entries(MANIFEST)
        reference = manifest_entries(REFERENCE_MANIFEST)

        missing = sorted(set(reference) - set(shipped))

        self.assertEqual(missing, [])

    def test_manifest_contains_new_comfy_quantized_entries(self):
        entries = manifest_entries(MANIFEST)
        expected = {
            "ideogram4-nvfp4": ("hf_file", "Comfy-Org/Ideogram-4:diffusion_models/ideogram4_nvfp4_mixed.safetensors", "diffusion_models", "5.11GB"),
            "ideogram4-unconditional-nvfp4": ("hf_file", "Comfy-Org/Ideogram-4:diffusion_models/ideogram4_unconditional_nvfp4_mixed.safetensors", "diffusion_models", "5.11GB"),
            "ideogram4-qwen3vl-8b-nvfp4": ("hf_file", "Comfy-Org/Ideogram-4:text_encoders/qwen3vl_8b_nvfp4.safetensors", "text_encoders", "5.87GB"),
            "lens-turbo-mxfp8": ("hf_file", "Comfy-Org/Lens:diffusion_models/lens_turbo_mxfp8.safetensors", "diffusion_models", "5.18GB"),
            "lens-gpt-oss-20b-nvfp4": ("hf_file", "Comfy-Org/Lens:text_encoders/gpt_oss_20b_nvfp4.safetensors", "text_encoders", "12.33GB"),
            "pixeldit-1300m-1024px-mxfp8": ("hf_file", "Comfy-Org/PixelDiT:diffusion_models/pixeldit_1300m_1024px_mxfp8.safetensors", "diffusion_models", "1.33GB"),
            "pixeldit-gemma-2-2b-fp8": ("hf_file", "Comfy-Org/PixelDiT:text_encoders/gemma_2_2b_it_elm_fp8_scaled.safetensors", "text_encoders", "2.44GB"),
            "pid-flux2-1024-to-4096-mxfp8": ("hf_file", "Comfy-Org/PixelDiT:diffusion_models/pid_flux2_1024_to_4096_4step_mxfp8.safetensors", "diffusion_models", "1.41GB"),
            "pid-flux2-512-to-2048-mxfp8": ("hf_file", "Comfy-Org/PixelDiT:diffusion_models/pid_flux2_512_to_2048_4step_mxfp8.safetensors", "diffusion_models", "1.41GB"),
        }

        for name, (kind, source, subdir, size) in expected.items():
            with self.subTest(name=name):
                self.assertIn(name, entries)
                self.assertEqual(entries[name]["kind"], kind)
                self.assertEqual(entries[name]["source"], source)
                self.assertEqual(entries[name]["subdir"], subdir)
                self.assertEqual(entries[name]["size"], size)

    def test_manifest_names_are_unique(self):
        names = []
        with MANIFEST.open() as handle:
            for raw in handle:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                names.append(line.split("|", 1)[0])

        duplicates = sorted({name for name in names if names.count(name) > 1})

        self.assertEqual(duplicates, [])

    def test_new_manifest_entries_parse_with_expected_types_and_sizes(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            parsed = models_service.parse_manifest(
                MANIFEST,
                MANIFEST,
                tmp_path / "models",
                tmp_path / "config",
            )

        by_name = {entry.name: entry for entry in parsed}

        self.assertEqual(by_name["ideogram4-nvfp4"].type, "checkpoint")
        self.assertEqual(by_name["ideogram4-qwen3vl-8b-nvfp4"].type, "text_encoder")
        self.assertEqual(by_name["lens-gpt-oss-20b-nvfp4"].type, "text_encoder")
        self.assertGreater(by_name["pid-flux2-512-to-2048-mxfp8"].expected_size_bytes, 0)


if __name__ == "__main__":
    unittest.main()
