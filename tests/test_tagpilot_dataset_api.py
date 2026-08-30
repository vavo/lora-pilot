import base64
import io
import tempfile
import unittest
import zipfile
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

    def test_tagpilot_load_pagination(self):
        dataset_dir = portal_app._DATASET_ROOT / "1_sample"
        dataset_dir.mkdir(parents=True)
        (dataset_dir / "a.jpg").write_bytes(b"1")
        (dataset_dir / "b.jpg").write_bytes(b"2")
        (dataset_dir / "c.txt").write_text("tag", encoding="utf-8")
        (dataset_dir / "d.txt").write_text("meta", encoding="utf-8")

        payload = portal_app.tagpilot_load("sample", offset=1, limit=2)
        payload_all = portal_app.tagpilot_load("sample", offset=0, limit=0)

        self.assertEqual(payload["name"], "1_sample")
        self.assertEqual([item["name"] for item in payload["files"]], ["b.jpg", "c.txt"])
        self.assertEqual(payload["offset"], 1)
        self.assertEqual(payload["limit"], 2)
        self.assertEqual(payload["returned"], 2)
        self.assertEqual(payload["total"], 4)

        self.assertEqual(payload_all["returned"], 4)
        self.assertEqual(payload_all["total"], 4)
        self.assertEqual(len(payload_all["files"]), 4)

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

    def test_upload_dataset_rejects_oversized_archive(self):
        original_limit = portal_app.DATASET_UPLOAD_MAX_BYTES
        try:
            portal_app.DATASET_UPLOAD_MAX_BYTES = 8
            payload = portal_app.UploadFile(file=io.BytesIO(b"x" * 16), filename="oversized.zip")
            with self.assertRaises(portal_app.HTTPException) as cm:
                portal_app.upload_dataset(payload)
            self.assertEqual(cm.exception.status_code, 413)
            self.assertIn("upload exceeds limit", cm.exception.detail)
        finally:
            portal_app.DATASET_UPLOAD_MAX_BYTES = original_limit

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

    def test_tagpilot_save_rejects_symlinked_dataset_directory(self):
        outside = Path(self.tmp.name) / "outside"
        outside.mkdir()
        portal_app._DATASET_ROOT.mkdir(parents=True)
        try:
            (portal_app._DATASET_ROOT / "1_escape").symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("symlink creation is not available")

        upload = portal_app.UploadFile(file=io.BytesIO(b"not a zip"), filename="dataset.zip")
        with self.assertRaises(portal_app.HTTPException) as cm:
            portal_app.tagpilot_save("escape", upload)

        self.assertEqual(cm.exception.status_code, 400)
        self.assertFalse((outside / "dataset.zip").exists())

    def test_tagpilot_save_rejects_in_root_symlink_alias(self):
        victim = portal_app._DATASET_ROOT / "1_victim"
        victim.mkdir(parents=True)
        (victim / "keep.txt").write_text("keep", encoding="utf-8")
        try:
            (portal_app._DATASET_ROOT / "1_alias").symlink_to(victim, target_is_directory=True)
        except OSError:
            self.skipTest("symlink creation is not available")

        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("replace.txt", "replace")
        archive.seek(0)
        with self.assertRaises(portal_app.HTTPException) as cm:
            portal_app.tagpilot_save(
                "alias",
                portal_app.UploadFile(file=archive, filename="alias.zip"),
            )

        self.assertEqual(cm.exception.status_code, 400)
        self.assertEqual((victim / "keep.txt").read_text(encoding="utf-8"), "keep")
        self.assertFalse((victim / "replace.txt").exists())

    def test_tagpilot_save_does_not_select_reserved_zip_store(self):
        zip_dir = portal_app._DATASET_ZIP_ROOT
        zip_dir.mkdir(parents=True)
        keep = zip_dir / "keep.zip"
        keep.write_bytes(b"keep")
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("new.txt", "new")
        archive.seek(0)

        portal_app.tagpilot_save(
            "ZIPs",
            portal_app.UploadFile(file=archive, filename="new.zip"),
        )

        self.assertEqual(keep.read_bytes(), b"keep")
        self.assertEqual((portal_app._DATASET_ROOT / "1_ZIPs" / "new.txt").read_text(), "new")

    def test_tagpilot_save_prefers_exact_dataset_name_over_canonical_collision(self):
        exact = portal_app._DATASET_ROOT / "1_a~"
        canonical = portal_app._DATASET_ROOT / "1_a"
        exact.mkdir(parents=True)
        canonical.mkdir()
        (exact / "exact.txt").write_text("exact", encoding="utf-8")
        (canonical / "canonical.txt").write_text("canonical", encoding="utf-8")
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("replacement.txt", "replacement")
        archive.seek(0)

        portal_app.tagpilot_save(
            "1_a~",
            portal_app.UploadFile(file=archive, filename="replacement.zip"),
        )

        self.assertFalse((exact / "exact.txt").exists())
        self.assertEqual((exact / "replacement.txt").read_text(), "replacement")
        self.assertEqual((canonical / "canonical.txt").read_text(), "canonical")

    def test_tagpilot_save_replaces_symlink_inserted_during_upload(self):
        victim = portal_app._DATASET_ROOT / "1_victim"
        victim.mkdir(parents=True)
        (victim / "keep.txt").write_text("keep", encoding="utf-8")
        alias = portal_app._DATASET_ROOT / "1_alias"
        original_stream = portal_app._stream_upload_to_path

        def stream_with_symlink(upload, destination, *, max_bytes):
            alias.symlink_to(victim, target_is_directory=True)
            return original_stream(upload, destination, max_bytes=max_bytes)

        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("replacement.txt", "replacement")
        archive.seek(0)
        portal_app._stream_upload_to_path = stream_with_symlink
        try:
            with self.assertRaises(portal_app.HTTPException) as cm:
                portal_app.tagpilot_save(
                    "alias",
                    portal_app.UploadFile(file=archive, filename="alias.zip"),
                )
        finally:
            portal_app._stream_upload_to_path = original_stream

        self.assertEqual(cm.exception.status_code, 400)
        self.assertEqual((victim / "keep.txt").read_text(), "keep")
        self.assertFalse((victim / "replacement.txt").exists())

    def test_tagpilot_save_replaces_existing_dataset(self):
        dataset_dir = portal_app._DATASET_ROOT / "1_sample"
        dataset_dir.mkdir(parents=True)
        (dataset_dir / "old.txt").write_text("old", encoding="utf-8")
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("new.txt", "new")
        archive.seek(0)

        payload = portal_app.tagpilot_save(
            "sample",
            portal_app.UploadFile(file=archive, filename="sample.zip"),
        )

        self.assertEqual(payload["status"], "saved")
        self.assertFalse((dataset_dir / "old.txt").exists())
        self.assertEqual((dataset_dir / "new.txt").read_text(encoding="utf-8"), "new")

    def test_tagpilot_save_creates_missing_dataset(self):
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("photo.txt", "tags")
        archive.seek(0)

        payload = portal_app.tagpilot_save(
            "new dataset",
            portal_app.UploadFile(file=archive, filename="new.zip"),
        )

        dataset_dir = portal_app._DATASET_ROOT / "1_new_dataset"
        self.assertEqual(payload["status"], "saved")
        self.assertEqual((dataset_dir / "photo.txt").read_text(encoding="utf-8"), "tags")

    def test_tagpilot_save_rejects_empty_archive(self):
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w"):
            pass
        archive.seek(0)

        with self.assertRaises(portal_app.HTTPException) as cm:
            portal_app.tagpilot_save(
                "empty",
                portal_app.UploadFile(file=archive, filename="empty.zip"),
            )

        self.assertEqual(cm.exception.status_code, 500)
        self.assertFalse((portal_app._DATASET_ROOT / "1_empty").exists())


if __name__ == "__main__":
    unittest.main()
