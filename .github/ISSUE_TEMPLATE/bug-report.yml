name: Bug report
description: Something is not working correctly.
labels: "S: needs triage, type: bug"

body:
  - type: textarea
    attributes:
      label: Description
      description: >-
        A clear and concise description of what the bug is.
    validations:
      required: true

  - type: textarea
    attributes:
      label: Expected behavior
      description: >-
        A clear and concise description of what you expected to happen.

  - type: input
    attributes:
      label: pip version
    validations:
      required: true
  - type: input
    attributes:
      label: Python version
    validations:
      required: true
  - type: input
    attributes:
      label: OS
    validations:
      required: true

  - type: textarea
    attributes:
      label: How to Reproduce
      description: Please provide steps to reproduce this bug.
      value: |
        1. Get package from '...'
        2. Then run '...'
        3. An error occurs.
    validations:
      required: true

  - type: textarea
    attributes:
      label: Output
      description: >-
        Provide the output of the steps above, including the commands
        themselves and pip's output/traceback etc.
      render: sh-session

  - type: checkboxes
    attributes:
      label: Code of Conduct
      options:
        - label: >-
            I agree to follow the [PSF Code of Conduct](https://www.python.org/psf/conduct/).
          required: true
