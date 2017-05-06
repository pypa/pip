Allow using repositories hosted on Amazon S3 buckets specified as
`pip --extra-index-url s3://s3.region.amazonaws.com/bucket-name/`. To
create a new repository upload your packages to an S3 bucket and grant
the `List` permission to the `Everyone` role. No need to enable static
website hosting, however it doesn't make a difference as long as the XML
listing is enabled. HTTPS is enforced for these URLs.
