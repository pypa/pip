Add CLI options for enhancing requests with HTTP headers

-H, --header <key:val>      HTTP header to include in all requests. This option
                            can be used multiple times. Conflicts with
                            --extra-index-url.

Example:

```
pip install \
  --index-url http://pypi.index/simple/ \
  --trusted-host pypi.index \
  -H 'X-Spam: ~*~ SPAM ~*~' \
  requests
```
