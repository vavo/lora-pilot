import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BootstrapManifestTests(unittest.TestCase):
    def test_bootstrap_refreshes_persistent_manifest_from_bundle(self):
        source = (ROOT / "scripts/bootstrap.sh").read_text()
        self.assertIn('MODEL_MANIFEST_SOURCE="${DEFAULT_MODELS_MANIFEST:-/opt/pilot/config/models.manifest.default}"', source)
        self.assertIn('MODEL_MANIFEST_TARGET="${MODELS_MANIFEST:-$WORKSPACE_ROOT/config/models.manifest}"', source)
        self.assertIn('MODEL_MANIFEST_HASH_FILE="$WORKSPACE_ROOT/config/.models.manifest.bundle.sha256"', source)
        self.assertIn('cp -f "$MODEL_MANIFEST_SOURCE" "$MODEL_MANIFEST_TARGET"', source)

    def test_bootstrap_preserves_custom_manifest_after_initial_migration(self):
        source = (ROOT / "scripts/bootstrap.sh").read_text()
        self.assertIn('Preserving customized model manifest:', source)
        self.assertNotIn(".pre-refresh.", source)
        self.assertNotIn('cp -a "$target_dir"', source)

    def test_bundled_trees_share_the_inventory_sync_helper(self):
        for name in ("bootstrap.sh", "tagpilot.sh"):
            source = (ROOT / "scripts" / name).read_text()
            self.assertIn("/opt/pilot/bundle-sync.py", source)
            self.assertNotIn("remove_stale_bundle_files", source)


if __name__ == "__main__":
    unittest.main()
