import unittest
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TrainPilotFrontendTests(unittest.TestCase):
    def test_trainpilot_preflights_sdxl_tokenizer(self):
        text = (ROOT / "apps/TrainPilot/trainpilot.sh").read_text(encoding="utf-8")
        self.assertIn("ensure_sdxl_tokenizer()", text)
        self.assertIn('local_files_only=True', text)
        self.assertIn("from huggingface_hub import hf_hub_download", text)
        self.assertIn('cache_dir=os.environ["TRANSFORMERS_CACHE"]', text)
        self.assertNotIn('hf_bin="/opt/venvs/core/bin/hf"', text)
        self.assertIn("openai/clip-vit-large-patch14", text)

    def test_tokenizer_download_is_visible_to_offline_validation(self):
        import os
        import subprocess
        import sys

        text = (ROOT / "apps/TrainPilot/trainpilot.sh").read_text(encoding="utf-8")
        preflight = text.split("ensure_sdxl_tokenizer() {", 1)[1].split("\n}\n", 1)[0]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "huggingface_hub.py").write_text('''
import os
from pathlib import Path
def hf_hub_download(repo_id, filename, cache_dir=None):
    cache = Path(cache_dir or (Path(os.environ["HF_HOME"]) / "hub"))
    cache.mkdir(parents=True, exist_ok=True)
    (cache / filename).write_text("cached")
''')
            (root / "transformers.py").write_text('''
import os
from pathlib import Path
class CLIPTokenizer:
    @classmethod
    def from_pretrained(cls, name, local_files_only):
        assert local_files_only
        cache = Path(os.environ["TRANSFORMERS_CACHE"])
        for filename in ("vocab.json", "merges.txt", "tokenizer_config.json"):
            if not (cache / filename).is_file():
                raise OSError("Tokenizer missing from Transformers cache")
''')
            env = dict(os.environ, PYTHONPATH=str(root), PYTHON_BIN=sys.executable,
                       HF_HOME=str(root / "hf-home"), TRANSFORMERS_CACHE=str(root / "transformers-cache"))
            result = subprocess.run(["bash", "-c", "set -eu\ndie(){ echo \"$*\"; exit 1; }\n"
                                     + "ensure_sdxl_tokenizer() {" + preflight
                                     + "\n}\nensure_sdxl_tokenizer\nensure_sdxl_tokenizer"],
                                    env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout.count("downloading tokenizer files"), 1)

    def test_sdxl_profiles_keep_vae_in_full_precision(self):
        import os
        import subprocess
        import sys
        import tomllib

        script = (ROOT / "apps/TrainPilot/trainpilot.sh").read_text(encoding="utf-8")
        overrides = script.split("      # precision override\n", 1)[1].split("      # Force PyTorch SDPA", 1)[0]
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "effective.toml"
            for precision in ("fp16", "bf16"):
                with self.subTest(precision=precision):
                    config.write_text('no_half_vae = false\n')
                    subprocess.run(["bash", "-c", 'set -eu\nsource "$1"\nCOPIED_TOML="$2"\nprecision="$3"\n'
                                    + overrides, "bash", str(ROOT / "apps/TrainPilot/helpers.sh"), str(config), precision],
                                   env=dict(os.environ, PYTHON_BIN=sys.executable, SCRIPT_DIR=str(ROOT / "apps/TrainPilot")),
                                   cwd=ROOT / "apps/TrainPilot", check=True)
                    settings = tomllib.loads(config.read_text())
                    self.assertTrue(settings["no_half_vae"])
                    self.assertEqual(settings["mixed_precision"], precision)

    def test_move_loras_moves_only_current_run_artifacts(self):
        try:
            from apps.Portal import app as portal_app
        except ModuleNotFoundError as exc:
            if exc.name == "fastapi":
                self.skipTest("FastAPI is not installed in this test environment")
            raise

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            output_dir = workspace / "outputs" / "run"
            output_dir.mkdir(parents=True)
            new_lora = output_dir / "run000001.safetensors"
            new_lora.write_bytes(b"lora")
            existing_lora = output_dir / "previous.safetensors"
            existing_lora.write_bytes(b"existing")
            existing_stat = existing_lora.stat()
            old_state = (
                portal_app.MODELS_DIR,
                portal_app._OUTPUT_ROOT,
                portal_app._tp_output_dir,
                portal_app._tp_run_id,
                portal_app._tp_exit_code,
                portal_app._tp_output_baseline,
                portal_app._tp_moved_run_id,
            )
            try:
                portal_app.MODELS_DIR = workspace / "models"
                portal_app._OUTPUT_ROOT = workspace / "outputs"
                portal_app._tp_output_dir = output_dir
                portal_app._tp_run_id = "current-run"
                portal_app._tp_exit_code = 0
                portal_app._tp_output_baseline = {
                    existing_lora.name: (existing_stat.st_size, existing_stat.st_mtime_ns)
                }
                portal_app._tp_moved_run_id = None

                result = portal_app.trainpilot_move_loras(
                    portal_app.TrainPilotMoveRequest(run_id="current-run")
                )

                self.assertEqual(result["files"], ["run000001.safetensors"])
                self.assertFalse(new_lora.exists())
                self.assertTrue(existing_lora.exists())
                self.assertTrue((portal_app.MODELS_DIR / "loras" / new_lora.name).exists())
            finally:
                (
                    portal_app.MODELS_DIR,
                    portal_app._OUTPUT_ROOT,
                    portal_app._tp_output_dir,
                    portal_app._tp_run_id,
                    portal_app._tp_exit_code,
                    portal_app._tp_output_baseline,
                    portal_app._tp_moved_run_id,
                ) = old_state


class TrainPilotResultBehaviorTests(unittest.TestCase):
    def test_result_states_escape_filenames_and_show_library_copy(self):
        import shutil
        import subprocess
        if not shutil.which('node'):
            self.skipTest('Node.js is required')
        script = r'''
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const nodes = new Map();
function node() { return {dataset:{}, children:[], textContent:'', append(child) {this.children.push(child)}, replaceChildren() {this.children=[]}}; }
const get = id => {if (!nodes.has(id)) nodes.set(id,node()); return nodes.get(id)};
let rejectMove = true, calls = [];
const context = {
  window: {addEventListener() {}, loadSection(section) {calls.push(section)}},
  document: {getElementById:get, createElement:node},
  formatBytes: value => `${value} B`,
  fetchJson: async (url, options) => {
    calls.push([url, JSON.parse(options.body)]);
    if (rejectMove) throw new Error('destination conflict');
    return {files:['safe.safetensors'], destination:'/workspace/models/loras'};
  },
};
vm.createContext(context);
vm.runInContext(fs.readFileSync('apps/Portal/static/js/trainpilot.js','utf8'), context);
(async () => {
  const data = {run_id:'current',running:false,exit_code:0,run:{dataset:'1_example',profile:'regular'},
    output_dir:'/workspace/outputs/example',lora_destination:'/workspace/models/loras',move_available:true,
    artifacts:[{name:'<img onerror=bad>.safetensors',size_bytes:24}]};
  context.renderTpResult({...data,running:true});
  assert.equal(get('tp-result').hidden,true);
  context.renderTpResult({...data,exit_code:1});
  assert.equal(get('tp-result').hidden,true);
  context.renderTpResult({...data,run:{stopped:true}});
  assert.equal(get('tp-result').hidden,true);
  context.renderTpResult({...data,run_id:null});
  assert.equal(get('tp-result').hidden,true);
  context.renderTpResult(data);
  assert.equal(get('tp-result').hidden,false);
  assert.equal(get('tp-result-files').children[0].children[0].textContent,'<img onerror=bad>.safetensors');
  assert.equal(get('tp-move-loras').disabled,false);
  context.renderTpResult({...data, moved:true});
  assert.equal(get('tp-move-loras').textContent,'Moved to LoRA library');
  assert.equal(get('tp-copy-loras').disabled,true);
  assert.equal(get('tp-move-loras').disabled,true);
  assert.equal(get('tp-result-path').textContent,'/workspace/models/loras');
  vm.runInContext('tpDismissedRunId = "current"',context);
  context.renderTpResult(data);
  assert.equal(get('tp-result').hidden,true);
})().catch(error => { console.error(error); process.exitCode=1; });
'''
        subprocess.run(['node', '-e', script], cwd=ROOT, check=True)


if __name__ == "__main__":
    unittest.main()
