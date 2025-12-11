# Security Guide

This document outlines the security measures implemented in DocsCopilot MCP servers.

## Security Features

### 1. Secure Credential Storage

- **Environment Variables**: All sensitive credentials (GitHub tokens, GitLab tokens) are loaded exclusively from environment variables
- **No File Storage**: Credentials are never loaded from configuration files, even if present
- **Exclusion from Serialization**: Credentials are excluded from model serialization to prevent accidental exposure
- **Logging Protection**: Credentials are automatically masked in log messages using a credential filter

**Best Practices:**
- Always use environment variables for tokens: `export GITHUB_TOKEN=your_token`
- Never commit tokens to configuration files or version control
- Use secrets management systems in production (Kubernetes secrets, AWS Secrets Manager, etc.)

### 2. Input Validation

All user inputs are validated and sanitized to prevent injection attacks:

#### Feature ID Validation
- Pattern: Alphanumeric characters, hyphens, underscores, and forward slashes only
- Maximum length: 200 characters
- Blocks dangerous patterns: `..`, null bytes, newlines, tabs

#### Path Validation
- All file paths are validated to prevent path traversal attacks
- Paths must be within the configured workspace root
- Blocks absolute paths outside workspace
- Prevents `..` sequences and null bytes

#### Branch Name Validation
- Pattern: Alphanumeric characters, hyphens, underscores, and forward slashes only
- Maximum length: 255 characters (Git limit)
- Blocks dangerous patterns: `..`, `@{`, `.lock` suffix
- Prevents names starting or ending with dots

#### Product Name Validation
- Pattern: Alphanumeric characters, hyphens, and underscores only
- Maximum length: 100 characters

#### Document Type Validation
- Only allows predefined document types from an allowlist
- Prevents arbitrary values that could lead to path manipulation

#### Git Command Injection Prevention
- All patterns used in git commands are sanitized
- Blocks command injection characters: `;`, `&`, `|`, `` ` ``, `$`, `(`, `)`, `<`, `>`, newlines
- Commit hashes are validated to be valid hex strings (7-40 characters)

### 3. Secure API Communication

- **HTTPS Only**: All API calls to GitHub and GitLab use HTTPS
- **Certificate Verification**: SSL certificate verification is enabled by default
- **Timeout Protection**: API requests have a 30-second timeout to prevent hanging requests
- **Retry Strategy**: Implements exponential backoff for transient failures

### 4. Git Command Security

- **Subprocess Isolation**: Git commands are executed via subprocess with proper isolation
- **Timeout Protection**: All git commands have a 30-second timeout
- **Input Sanitization**: All arguments passed to git commands are validated
- **Path Validation**: Repository paths are validated before executing git commands

### 5. Error Handling

- Security errors are logged with appropriate warning levels
- Error messages do not expose sensitive information
- Detailed error information is not leaked to clients

## Security Considerations

### Rate Limiting

MCP servers communicate via stdio (standard input/output), not HTTP. Rate limiting is typically handled at the MCP client level or infrastructure level (e.g., container orchestration).

### Dependencies

All dependencies are regularly reviewed for security vulnerabilities. Use `pip-audit` or similar tools to check for known vulnerabilities:

```bash
pip install pip-audit
pip-audit -r requirements.txt
```

### Container Security

When running in containers:
- Use non-root users when possible
- Mount secrets as volumes or use secrets management
- Keep base images updated
- Scan images for vulnerabilities

### Network Security

- MCP servers communicate via stdio, not network sockets
- If exposing via network (not recommended), use TLS/SSL
- Restrict network access using firewalls or network policies

## Reporting Security Issues

If you discover a security vulnerability, please report it privately:

1. **Do not** create a public GitHub issue
2. Contact the maintainers directly
3. Provide details about the vulnerability
4. Allow time for a fix before public disclosure

## Security Checklist

When deploying DocsCopilot:

- [ ] All tokens are set via environment variables
- [ ] Configuration files do not contain credentials
- [ ] Logs are reviewed for accidental credential exposure
- [ ] Dependencies are up-to-date and scanned for vulnerabilities
- [ ] Container images are scanned for vulnerabilities
- [ ] Network access is restricted if exposing services
- [ ] File permissions are set correctly (600 for config files)
- [ ] Secrets management system is used in production

## Security Best Practices

1. **Principle of Least Privilege**: Grant only necessary permissions to tokens
2. **Token Rotation**: Regularly rotate API tokens
3. **Audit Logging**: Monitor and audit access to sensitive operations
4. **Regular Updates**: Keep dependencies and base images updated
5. **Security Scanning**: Regularly scan for vulnerabilities
6. **Access Control**: Restrict who can access and modify configuration

## Compliance

This security implementation follows industry best practices:
- OWASP Top 10 prevention
- Input validation and sanitization
- Secure credential handling
- Defense in depth
