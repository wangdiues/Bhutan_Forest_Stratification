name: 🐛 Bug Report
description: File a bug report
title: "[Bug]: "
labels: ["bug", "triage"]
assignees:
  - your-username
body:
  - type: markdown
    attributes:
      value: |
        Thanks for taking the time to fill out this bug report!

  - type: textarea
    id: description
    attributes:
      label: Describe the bug
      description: A clear and concise description of what the bug is.
      placeholder: Tell us what you see!
    validations:
      required: true

  - type: textarea
    id: reproduce
    attributes:
      label: To Reproduce
      description: Steps to reproduce the behavior
      placeholder: |
        1. Run command '...'
        2. With module '...'
        3. See error
    validations:
      required: true

  - type: textarea
    id: expected
    attributes:
      label: Expected behavior
      description: A clear and concise description of what you expected to happen.
    validations:
      required: true

  - type: textarea
    id: actual
    attributes:
      label: Actual behavior
      description: What actually happened? Include error messages and tracebacks.
      placeholder: Paste error messages here
    validations:
      required: true

  - type: input
    id: system
    attributes:
      label: System Information
      description: |
        Run: `python -c "import sys; print(f'{sys.platform} - Python {sys.version}')" `
      placeholder: e.g., win32 - Python 3.12.3
    validations:
      required: true

  - type: input
    id: version
    attributes:
      label: Package Version
      description: What version of the package are you running?
      placeholder: e.g., 1.0.0
    validations:
      required: true

  - type: dropdown
    id: modules
    attributes:
      label: Affected Modules
      description: Which module(s) are affected?
      multiple: true
      options:
        - 00_data_inspection
        - 01_data_cleaning
        - 01b_qc_after_cleaning
        - 02_env_extraction
        - 02b_qc_after_env_extraction
        - 03_alpha_diversity
        - 04_beta_diversity
        - 05_cca_ordination
        - 06_indicator_species
        - 07_co_occurrence
        - 08_evi_spatial_analysis
        - 09_sci_index
        - 10_spatial_mapping
        - 11_reporting

  - type: textarea
    id: logs
    attributes:
      label: Relevant Log Output
      description: Please copy and paste any relevant log output.
      render: shell
    validations:
      required: false

  - type: textarea
    id: context
    attributes:
      label: Additional Context
      description: Add any other context about the problem here.
    validations:
      required: false

  - type: checkboxes
    id: terms
    attributes:
      label: Code of Conduct
      description: By submitting this issue, you agree to follow our [Code of Conduct](CODE_OF_CONDUCT.md)
      options:
        - label: I agree to follow the Code of Conduct
          required: true
