import json
import shutil
import subprocess
import unittest
from pathlib import Path
from apps.Portal.services import model_install

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("node"), "Node.js is required for catalog metadata checks")
class ModelCatalogTests(unittest.TestCase):
    def catalog(self):
        script = """
const fs = require('fs'), vm = require('vm');
const context = {window:{}};
vm.createContext(context);
vm.runInContext(fs.readFileSync('apps/Portal/static/js/model-catalog.js','utf8'),context);
const entries = fs.readFileSync('config/models.manifest','utf8').split('\\n')
  .filter(line=>line && !line.startsWith('#')).map(line=>{
    const [name,kind,source,subdir]=line.split('|');
    return {name,kind,source,subdir,category:/xl/i.test(name)?'SDXL':'OTHERS'};
  });
console.log(JSON.stringify({families:context.window.modelFamilies,
  assignments:entries.map(m=>[m.name,context.window.modelFamilyFor(m).id])}));
"""
        return json.loads(subprocess.check_output(["node", "-e", script], cwd=ROOT, text=True))

    def test_every_entry_has_a_family_and_special_cases_do_not_collide(self):
        data = self.catalog()
        known = {family["id"] for family in data["families"]}
        assignments = dict(data["assignments"])
        self.assertTrue(all(family in known for family in assignments.values()))
        self.assertEqual(assignments["realistic-vision-v6-sd15"], "sd15")
        self.assertEqual(assignments["pid-flux2-1024-to-4096-mxfp8"], "pixeldit")
        self.assertEqual(assignments["ltx-2.5-gemma4-e2b-bf16"], "ltx25")
        self.assertEqual(assignments["controlnet-canny"], "components")

    def test_setup_checklists_match_bundled_workflows(self):
        for workflow in model_install.catalog():
            filename, catalog_files = workflow["id"] + ".json", workflow["files"]
            refs = {}

            def visit(value):
                if isinstance(value, dict):
                    if all(key in value for key in ("name", "url", "directory")):
                        refs[value["name"]] = {key: value[key] for key in ("name", "url", "directory")}
                    for child in value.values():
                        visit(child)
                elif isinstance(value, list):
                    for child in value:
                        visit(child)

            visit(json.loads((ROOT / "config/comfy-workflows" / filename).read_text()))
            actual = {entry["name"]: {key: entry[key] for key in ("name", "url", "directory")} for entry in catalog_files}
            self.assertEqual(actual, refs)
            optional = [entry["name"] for entry in catalog_files if entry["optional"]]
            self.assertEqual(optional, ["gemma4_e2b_it_int8_convrot.safetensors"] if "ltx" in filename else [])
