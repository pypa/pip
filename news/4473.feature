pip now retries on more HTTP status codes, for intermittent failures.

Previously, it only retried on the standard 503. Now, it also retries on 500
(transient failures on AWS S3), 520 and 527 (transient failures on Cloudflare).
