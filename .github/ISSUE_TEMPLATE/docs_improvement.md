name: 📝 Documentation Improvement
description: Suggest improvements to documentation
title: "[Docs]: "
labels: ["documentation", "triage"]
body:
  - type: markdown
    attributes:
      value: |
        Thanks for helping improve our documentation!

  - type: dropdown
    id: doc-type
    attributes:
      label: Type of Documentation
      description: What type of documentation needs improvement?
      multiple: true
      options:
        - README.md
        - API documentation
        - Tutorials/Examples
        - Installation guide
        - Contributing guide
        - Code comments/docstrings
        - Other (describe below)

  - type: textarea
    id: current
    attributes:
      label: Current State
      description: What is currently missing or unclear?
    validations:
      required: true

  - type: textarea
    id: improvement
    attributes:
      label: Proposed Improvement
      description: Describe your suggested improvement.
    validations:
      required: true

  - type: textarea
    id: context
    attributes:
      label: Additional Context
      description: Add any other context or mockups.
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
