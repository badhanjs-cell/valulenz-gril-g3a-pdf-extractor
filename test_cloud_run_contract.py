import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent

class CloudRunContractTests(unittest.TestCase):
    def test_dockerfile_cloud_run_contract(self):
        text = (ROOT / "Dockerfile").read_text()
        self.assertIn("python:3.12-slim", text)
        self.assertIn("PORT=8080", text)
        self.assertIn("EXPOSE 8080", text)
        self.assertIn("USER app", text)
        self.assertIn("uvicorn main:app", text)
        self.assertIn("--host 0.0.0.0", text)
        self.assertIn("${PORT:-8080}", text)

    def test_secret_files_are_excluded(self):
        text = (ROOT / ".dockerignore").read_text()
        self.assertIn(".env", text)
        self.assertIn(".git/", text)

    def test_cloud_build_targets_canonical_service(self):
        text = (ROOT / "cloudbuild.yaml").read_text()
        self.assertIn("_SERVICE_NAME: gril-g3a-pdf-extractor", text)
        self.assertIn("_DEPLOY_REGION: asia-south1", text)

    def test_health_and_extraction_routes_exist(self):
        text = (ROOT / "main.py").read_text()
        self.assertIn('@app.get("/health")', text)
        self.assertIn('@app.post("/extract-regulatory-pdf")', text)
        self.assertIn('alias="X-Extractor-Key"', text)

if __name__ == "__main__":
    unittest.main()
