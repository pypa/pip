Add extra headers option to enhance HTTP requests

Users can supply --extra-headers='{...}' option to pip commands that enhances the
PipSession object with custom headers.

This enables use of private PyPI servers that use token-based authentication.

Example:

```
pip install \
  --extra-headers='{"Authorization": "..."}' \
  --index-url https://secure.pypi.example.com/simple \
  --trusted-host secure.pypi.example.com \
  fizz==1.2.3
```
