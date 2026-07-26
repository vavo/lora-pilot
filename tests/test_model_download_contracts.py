import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ModelDownloadContractTests(unittest.TestCase):
    def test_model_downloader_prefers_pinned_core_cli(self):
        source = (ROOT / "scripts/get-models.sh").read_text()
        core_hf = source.index('[[ -x "/opt/venvs/core/bin/hf" ]]')
        path_hf = source.index('command -v hf')
        self.assertLess(core_hf, path_hf)

    def test_model_pull_reports_downloader_output_on_failure(self):
        source = (ROOT / "apps/Portal/app.py").read_text()
        self.assertIn('output = "\\n".join(job.output_tail).strip()', source)
        self.assertIn('job.error = output[-2000:] if output else f"exit code {rc}"', source)

    def test_model_pull_progress_regex_matches_percentages(self):
        source = (ROOT / "apps/Portal/app.py").read_text()
        self.assertIn('re.compile(r"(?P<pct>\\d{1,3})%")', source)


if __name__ == "__main__":
    unittest.main()
