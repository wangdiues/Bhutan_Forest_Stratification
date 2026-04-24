name: ✨ Feature Request
description: Suggest an idea for this project
title: "[Feature]: "
labels: ["enhancement", "triage"]
body:
  - type: markdown
    attributes:
      value: |
        Thanks for suggesting a feature! Please fill out the form below.

  - type: textarea
    id: problem
    attributes:
      label: Is your feature request related to a problem?
      description: A clear and concise description of what the problem is.
      placeholder: I'm always frustrated when [...]
    validations:
      required: true

  - type: textarea
    id: solution
    attributes:
      label: Describe the solution you'd like
      description: A clear and concise description of what you want to happen.
    validations:
      required: true

  - type: textarea
    id: alternatives
    attributes:
      label: Describe alternatives you've considered
      description: A clear and concise description of any alternative solutions or features you've considered.
    validations:
      required: false

  - type: dropdown
    id: impact
    attributes:
      label: Impact
      description: How would you rate the impact of this feature?
      options:
        - Low (nice to have)
        - Medium (would improve workflow)
        - High (blocks important work)
        - Critical (required for core functionality)
    validations:
      required: true

  - type: textarea
    id: context
    attributes:
      label: Additional Context
      description: Add any other context, mockups, or screenshots about the feature request.
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
