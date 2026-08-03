# Valulenz GRIL G3A PDF Extractor

Production Railway microservice for the GRIL G3A PDF text-extraction route.

## Exact nomenclature

Use these exact names:

- GitHub repository: `valulenz-gril-g3a-pdf-extractor`
- Railway service: `gril-g3a-pdf-extractor`
- Railway environment: `production`
- GitHub branch: `main`
- Make module: `Extract Regulatory PDF — Railway G3A`
- API header: `X-Extractor-Key`
- Health endpoint: `GET /health`
- Extraction endpoint: `POST /extract-regulatory-pdf`

## Railway variables

Create these variables exactly:

```text
SUPABASE_PROJECT_URL=https://wmxbdirvlwuagouraobr.supabase.co
SUPABASE_SECRET_KEY=sb_secret_REPLACE_ME
PDF_EXTRACTOR_API_KEY=REPLACE_WITH_LONG_RANDOM_SECRET
MAX_PDF_BYTES=104857600
DOWNLOAD_TIMEOUT_SECONDS=120
```

Railway creates `PORT` automatically. Do not add it manually.

## Deployment

1. Create the GitHub repository `valulenz-gril-g3a-pdf-extractor`.
2. Upload all files from this folder to the root of the repository.
3. In the existing Railway project, create a service from this GitHub repository.
4. Name the service `gril-g3a-pdf-extractor`.
5. Select branch `main`.
6. Leave Root Directory blank.
7. Add the five variables above.
8. Generate a public Railway domain.
9. Verify `GET https://YOUR-DOMAIN/health`.

Expected health response:

```json
{
  "success": true,
  "status": "healthy",
  "configured": true,
  "version": "VALULENZ-G3A-PDF-EXTRACTOR-v1.0.0",
  "engine": "PyMuPDF",
  "ocr_enabled": false
}
```

## Make endpoint

```text
https://YOUR-DOMAIN/extract-regulatory-pdf
```

Headers:

```text
X-Extractor-Key: same value as PDF_EXTRACTOR_API_KEY
Content-Type: application/json
```
