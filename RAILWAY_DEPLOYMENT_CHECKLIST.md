# Railway Deployment Checklist

## Exact names

| Item | Exact value |
|---|---|
| GitHub repository | `valulenz-gril-g3a-pdf-extractor` |
| Railway service | `gril-g3a-pdf-extractor` |
| Railway environment | `production` |
| Git branch | `main` |
| Root directory | Leave blank |
| Builder | `NIXPACKS` |
| Healthcheck | `/health` |
| Restart policy | `ON_FAILURE` |

## Variables

| Variable name | Exact value or source |
|---|---|
| `SUPABASE_PROJECT_URL` | `https://wmxbdirvlwuagouraobr.supabase.co` |
| `SUPABASE_SECRET_KEY` | Current Supabase `sb_secret_*` key |
| `PDF_EXTRACTOR_API_KEY` | New long random private secret |
| `MAX_PDF_BYTES` | `104857600` |
| `DOWNLOAD_TIMEOUT_SECONDS` | `120` |

Do not create `PORT`; Railway provides it.

## Networking

Generate one public domain after deployment is healthy.

Use:

```text
https://YOUR-DOMAIN.up.railway.app/extract-regulatory-pdf
```

in the Make module named:

```text
Extract Regulatory PDF — Railway G3A
```
