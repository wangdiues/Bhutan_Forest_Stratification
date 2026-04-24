# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of this project seriously. If you believe you have found a security vulnerability, please report it to us as described below.

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via email at your.email@university.edu with the following information:

1. Description of the vulnerability
2. Steps to reproduce the issue
3. Potential impact
4. Suggested fix (if any)

You should receive a response within 48 hours. If for some reason you do not, please follow up via email to ensure we received your original message.

After the initial reply to your report, we will send you a more detailed response indicating the next steps in handling your report. After the initial reply, we will keep you informed of the progress toward a fix and full announcement, and may ask for additional information or guidance.

## Security Best Practices

When contributing to this project, please follow these security best practices:

1. **Never commit sensitive data**: API keys, passwords, credentials, or personal data should never be committed to the repository
2. **Use environment variables**: Store sensitive configuration in environment variables or `.env` files (which should be gitignored)
3. **Keep dependencies updated**: Regularly update dependencies to patch known vulnerabilities
4. **Validate all inputs**: Ensure all user inputs and external data are validated before use
5. **Use secure random**: Use `secrets` module instead of `random` for security-critical randomness

## Known Limitations

- This pipeline processes local files only and does not expose network services
- No user authentication is implemented (local execution only)
- Environmental data files are read-only and not modified by the pipeline

## Dependency Security

We use Dependabot to automatically monitor and update vulnerable dependencies. Security patches are prioritized and released as soon as possible.
