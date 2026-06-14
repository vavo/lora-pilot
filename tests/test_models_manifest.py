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

    def test_shipped_manifest_matches_reference_manifest(self):
        self.assertEqual(MANIFEST.read_text(), REFERENCE_MANIFEST.read_text())

    def test_manifest_contains_ltx_23_entries(self):
        entries = manifest_entries(MANIFEST)
        expected = {
            "ltx-2.3-22b-dev-fp8": ("hf_file", "Lightricks/LTX-2.3-fp8:ltx-2.3-22b-dev-fp8.safetensors", "checkpoints"),
            "ltx-2.3-22b-distilled-fp8": ("hf_file", "Lightricks/LTX-2.3-fp8:ltx-2.3-22b-distilled-fp8.safetensors", "checkpoints"),
            "ltx-2.3-22b-dev": ("hf_file", "Lightricks/LTX-2.3:ltx-2.3-22b-dev.safetensors", "checkpoints"),
            "ltx-2.3-22b-distilled": ("hf_file", "Lightricks/LTX-2.3:ltx-2.3-22b-distilled.safetensors", "checkpoints"),
            "ltx-2.3-22b-distilled-1.1": ("hf_file", "Lightricks/LTX-2.3:ltx-2.3-22b-distilled-1.1.safetensors", "checkpoints"),
            "ltx-2.3-22b-distilled-lora-384": ("hf_file", "Lightricks/LTX-2.3:ltx-2.3-22b-distilled-lora-384.safetensors", "loras"),
            "ltx-2.3-22b-distilled-lora-384-1.1": ("hf_file", "Lightricks/LTX-2.3:ltx-2.3-22b-distilled-lora-384-1.1.safetensors", "loras"),
            "ltx-2.3-spatial-upscaler-x1.5-1.0": ("hf_file", "Lightricks/LTX-2.3:ltx-2.3-spatial-upscaler-x1.5-1.0.safetensors", "upscale_models"),
            "ltx-2.3-spatial-upscaler-x2-1.1": ("hf_file", "Lightricks/LTX-2.3:ltx-2.3-spatial-upscaler-x2-1.1.safetensors", "upscale_models"),
            "ltx-2.3-temporal-upscaler-x2-1.0": ("hf_file", "Lightricks/LTX-2.3:ltx-2.3-temporal-upscaler-x2-1.0.safetensors", "upscale_models"),
        }

        for name, (kind, source, subdir) in expected.items():
            with self.subTest(name=name):
                self.assertIn(name, entries)
                self.assertEqual(entries[name]["kind"], kind)
                self.assertEqual(entries[name]["source"], source)
                self.assertEqual(entries[name]["subdir"], subdir)

    def test_manifest_repairs_known_broken_links(self):
        entries = manifest_entries(MANIFEST)
        expected_sources = {
            "sd15-base": "stable-diffusion-v1-5/stable-diffusion-v1-5:v1-5-pruned-emaonly.safetensors",
            "ragnarok-xl": "eniora/Juggernaut_XL_Ragnarok",
            "realvisxl-v5": "SG161222/RealVisXL_V5.0:RealVisXL_V5.0_fp16.safetensors",
            "pony-xl": "LyliaEngine/Pony_Diffusion_V6_XL:ponyDiffusionV6XL_v6StartWithThisOne.safetensors",
            "dreamshaper-xl": "Lykon/DreamShaper:DreamShaperXL1.0Alpha2_fixedVae_half_00001_.safetensors",
            "juggernaut-xl-v8": "RunDiffusion/Juggernaut-XL-v8:juggernautXL_v8Rundiffusion.safetensors",
            "juggernaut-xl-v9": "RunDiffusion/Juggernaut-XL-v9:Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors",
            "cyberrealistic-xl": "voxiliummusic/cyberrealistic_V4.0:cyberrealistic_v40.safetensors",
            "analog-madness-xl": "dwells/Analog_Madness_XL3:analogMadnessSDXL_xl3.safetensors",
            "opendalle-xl": "dataautogpt3/OpenDalleV1.1:OpenDalleV1.1.safetensors",
            "realistic-vision": "SG161222/Realistic_Vision_V5.1_noVAE:Realistic_Vision_V5.1_fp16-no-ema.safetensors",
            "realistic-vision-xl": "SG161222/Realistic_Vision_V6.0_B1_noVAE:Realistic_Vision_V6.0_NV_B1_fp16.safetensors",
            "epicrealism": "philz1337x/epicrealism:epicrealism_naturalSinRC1VAE.safetensors",
            "rev-animated": "danbrown/RevAnimated-v1-2-2:rev-animated-v1-2-2.safetensors",
            "realesrgan-4x": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
            "realesrgan-4x-anime": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth",
            "swinir-4x": "caidas/swin2SR-realworld-sr-x4-64-bsrgan-psnr:pytorch_model.bin",
            "esrgan-4x": "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth",
            "t5-xxl": "stabilityai/stable-diffusion-3-medium:text_encoders/t5xxl_fp8_e4m3fn.safetensors",
        }

        for name, source in expected_sources.items():
            with self.subTest(name=name):
                self.assertEqual(entries[name]["source"], source)

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
