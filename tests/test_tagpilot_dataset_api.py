import base64
import io
import tempfile
import unittest
from pathlib import Path

try:
    from apps.Portal import app as portal_app
except ModuleNotFoundError as exc:
    if exc.name == "fastapi":
        portal_app = None
    else:
        raise


class TagPilotDatasetApiTests(unittest.TestCase):
    def setUp(self):
        if portal_app is None:
            self.skipTest("FastAPI is not installed in this test environment")
        self.tmp = tempfile.TemporaryDirectory()
        self.old_workspace_root = portal_app.WORKSPACE_ROOT
        self.old_dataset_root = portal_app._DATASET_ROOT
        self.old_dataset_zip_root = portal_app._DATASET_ZIP_ROOT
        self.old_output_root = portal_app._OUTPUT_ROOT

        workspace = Path(self.tmp.name)
        portal_app.WORKSPACE_ROOT = workspace
        portal_app._DATASET_ROOT = workspace / "datasets"
        portal_app._DATASET_ZIP_ROOT = workspace / "datasets" / "ZIPs"
        portal_app._OUTPUT_ROOT = workspace / "outputs"

    def tearDown(self):
        portal_app.WORKSPACE_ROOT = self.old_workspace_root
        portal_app._DATASET_ROOT = self.old_dataset_root
        portal_app._DATASET_ZIP_ROOT = self.old_dataset_zip_root
        portal_app._OUTPUT_ROOT = self.old_output_root
        self.tmp.cleanup()

    def test_tagpilot_load_returns_images_and_tags(self):
        dataset_dir = portal_app._DATASET_ROOT / "1_sample"
        dataset_dir.mkdir(parents=True)
        image_bytes = b"\xff\xd8sample-image"
        (dataset_dir / "photo.jpg").write_bytes(image_bytes)
        (dataset_dir / "photo.txt").write_text("sample, tag", encoding="utf-8")

        payload = portal_app.tagpilot_load("sample")

        files = {item["name"]: item for item in payload["files"]}
        self.assertEqual(payload["name"], "1_sample")
        self.assertEqual(set(files), {"photo.jpg", "photo.txt"})
        self.assertEqual(files["photo.jpg"]["b64"], base64.b64encode(image_bytes).decode("utf-8"))
        self.assertEqual(base64.b64decode(files["photo.txt"]["b64"]).decode("utf-8"), "sample, tag")

    def test_tagpilot_load_resolves_exact_listed_dataset_name(self):
        dataset_dir = portal_app._DATASET_ROOT / "1_my dataset"
        dataset_dir.mkdir(parents=True)
        (dataset_dir / "photo.jpg").write_bytes(b"image")
        (dataset_dir / "photo.txt").write_text("exact folder", encoding="utf-8")

        payload = portal_app.tagpilot_load("1_my dataset")

        self.assertEqual(payload["name"], "1_my dataset")
        self.assertFalse((portal_app._DATASET_ROOT / "1_my_dataset").exists())

    def test_tagpilot_save_item_does_not_double_prefix_loaded_dataset(self):
        dataset_dir = portal_app._DATASET_ROOT / "1_sample"
        dataset_dir.mkdir(parents=True)
        upload = portal_app.UploadFile(file=io.BytesIO(b"image"), filename="photo.jpg")

        payload = portal_app.tagpilot_save_item(
            name="1_sample",
            file=upload,
            tags="saved, tag",
            reset=True,
            done=True,
        )

        self.assertEqual(Path(payload["path"]).name, "1_sample")
        self.assertTrue((dataset_dir / "photo.jpg").exists())
        self.assertEqual((dataset_dir / "photo.txt").read_text(encoding="utf-8"), "saved, tag")
        self.assertFalse((portal_app._DATASET_ROOT / "1_1_sample").exists())

    def test_dataset_file_iteration_skips_symlinks(self):
        dataset_dir = portal_app._DATASET_ROOT / "1_sample"
        dataset_dir.mkdir(parents=True)
        (dataset_dir / "photo.jpg").write_bytes(b"image")
        outside = Path(self.tmp.name) / "outside.txt"
        outside.write_text("outside", encoding="utf-8")

        try:
            (dataset_dir / "outside.txt").symlink_to(outside)
        except OSError:
            self.skipTest("symlink creation is not available")

        files = [p.name for p in portal_app._iter_dataset_files(dataset_dir)]

        self.assertEqual(files, ["photo.jpg"])

    def test_dataset_file_iteration_skips_symlinked_directories(self):
        dataset_dir = portal_app._DATASET_ROOT / "1_sample"
        dataset_dir.mkdir(parents=True)
        outside = Path(self.tmp.name) / "outside"
        outside.mkdir()
        (outside / "secret.jpg").write_bytes(b"outside")

        try:
            (dataset_dir / "linked").symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("symlink creation is not available")

        files = list(portal_app._iter_dataset_files(dataset_dir))

        self.assertEqual(files, [])


if __name__ == "__main__":
    unittest.main()
