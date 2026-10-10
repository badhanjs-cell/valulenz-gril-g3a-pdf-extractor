# Cloud Run Production Migration

Canonical service:
- repository: `badhanjs-cell/valulenz-gril-g3a-pdf-extractor`
- branch: `main`
- Cloud Run service: `gril-g3a-pdf-extractor`
- region: `asia-south1`
- health: `GET /health`
- extraction: `POST /extract-regulatory-pdf`

Runtime configuration:
- non-secret: `SUPABASE_PROJECT_URL`, `MAX_PDF_BYTES`, `DOWNLOAD_TIMEOUT_SECONDS`
- Secret Manager: `SUPABASE_SECRET_KEY`, `PDF_EXTRACTOR_API_KEY`

The Cloud Build config updates an existing Cloud Run service and therefore preserves its environment-variable and Secret Manager bindings. Keep Railway live until Cloud Run health and one authenticated extraction request are verified.
