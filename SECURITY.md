# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 0.1.x   | Yes       |

We currently support the latest release. Older versions may not receive security updates.

## Reporting a Vulnerability

**Do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via [GitHub Security Advisories](https://github.com/Manideep3969/quantum-computing/security/advisories/new).

Please include:

- A description of the vulnerability
- Steps to reproduce or a proof-of-concept
- The version(s) affected
- Any potential impact

You should expect:

- An acknowledgment within 48 hours
- A preliminary assessment within 5 business days
- A resolution or mitigation plan within 30 days

We ask that you:

- Do not publicly disclose the vulnerability until a fix is released
- Give us reasonable time to address the issue before any disclosure
- Make a good faith effort to avoid privacy destruction and data loss

## Security Best Practices for Contributors

- **Never commit secrets, tokens, or API keys** to the repository
- The `.gitignore` excludes credential files (e.g., `ibm_quantum_token*`, `*_credentials*.json`)
- If you accidentally commit credentials, rotate them immediately and open an issue
- Use environment variables or secret managers for any required authentication tokens