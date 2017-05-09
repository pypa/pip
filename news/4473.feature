Add `--retry-status <HTTP code>` to allow specifying custom HTTP status codes to retry on.
This is useful for AWS S3 or Cloudflare, which at times return codes other than 503 for
intermittent failures.
