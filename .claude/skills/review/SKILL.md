---
name: review
description: Run security and code quality review
disable-model-invocation: true
---

# Code Review

Run a security and code quality review using the security-reviewer agent.

**Usage:**
```
/review
```

This invokes the `security-reviewer` agent which will:
- Scan for SQL injection vulnerabilities
- Check for XSS vulnerabilities
- Look for hardcoded secrets or credentials
- Verify authentication/authorization patterns
- Check input sanitization
- Report findings with file:line references

**What to review:**
- All modified files since last commit
- New API endpoints
- Authentication flows
- Database queries
- User input handling

**Notes:**
- The security-reviewer agent uses read-only tools
- Review the report and address high/critical findings before merging
