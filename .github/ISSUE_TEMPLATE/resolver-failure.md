---
name: Dependency resolver failures / errors
about: Report when the pip dependency resolver fails
labels: ["K: UX", "K: crash", "C: new resolver", "C: dependency resolution"]
---

<!--
Please provide as much information as you can about your failure, so that we can understand the root cause.

Try if your issue has been fixed in the in-development version of pip. Use the following command to install pip from master:

    python -m pip install -U "pip @ https://github.com/pypa/pip/archive/master.zip"
-->

**What did you want to do?**
<!-- Include any inputs you gave to pip, for example:

* Package requirements: any CLI arguments and/or your requirements.txt file
* Already installed packages, outputted via `pip freeze`
-->

**Output**

```
Paste what pip outputted in a code block. https://github.github.com/gfm/#fenced-code-blocks
```

**Additional information**

<!--
It would be great if you could also include your dependency tree. For this you can use pipdeptree: https://pypi.org/project/pipdeptree/

For users installing packages from a private repository or local directory, please try your best to describe your setup. We'd like to understand how to reproduce the error locally, so would need (at a minimum) a description of the packages you are trying to install, and a list of dependencies for each package.
-->
