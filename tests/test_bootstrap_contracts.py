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
        self.assertIn('cp -p "$MODEL_MANIFEST_TARGET" "$MODEL_MANIFEST_TARGET.pre-refresh.$(date +%s)"', source)

    def test_bundled_trees_use_hashes_and_remove_deleted_files(self):
        source = (ROOT / "scripts/bootstrap.sh").read_text()
        self.assertIn("bundle_tree_hash()", source)
        self.assertIn("remove_stale_bundle_files()", source)
        self.assertIn("sync_bundled_tree()", source)
        self.assertIn("tar cf - --exclude='.env' --exclude='data' --exclude='__pycache__'", source)
        self.assertIn('sync_bundled_tree "$TAGPILOT_SOURCE_DIR" "$TAGPILOT_APP_DIR"', source)

    def test_standalone_tagpilot_refreshes_workspace_copy(self):
        source = (ROOT / "scripts/tagpilot.sh").read_text()
        self.assertIn('.bundle-sync-sha', source)
        self.assertIn("tar cf - --exclude='__pycache__'", source)
        self.assertIn('find "${APP_DIR}" -type f', source)


if __name__ == "__main__":
    unittest.main()
