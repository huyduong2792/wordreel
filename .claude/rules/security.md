---
name: security
scope: global
priority: critical
---

# Security Requirements

## Never Expose Credentials
- Never commit `.env`, `.env.local`, `credentials.json`, or similar files
- Use environment variables, never hardcode secrets
- Before committing, run: `git diff --staged --name-only | grep -E "\.env|credentials|secret"`

## Input Sanitization
Sanitize ALL user input to prevent XSS:
```tsx
// React: Let React escape by default, avoid dangerouslySetInnerHTML
<div>{userContent}</div>  // Safe - auto-escaped
<div dangerouslySetInnerHTML={{ __html: raw }} />  // DANGEROUS - avoid

// Python: Use Pydantic validation, never pass raw user input to SQL
```

## Rate Limiting
All write endpoints MUST have rate limiting:
- Auth endpoints: 5 requests/minute per IP
- Post creation: 10 requests/minute per user
- Comments: 30 requests/minute per user

## RLS Policy Enforcement
- Always use the regular Supabase client (respects RLS)
- Admin client only for admin endpoints
- Test that users can only access their own data

## Token Storage
- Store tokens in httpOnly cookies or secure storage
- Never store tokens in localStorage (XSS vulnerable)
- Refresh tokens expire in 7 days, access tokens in 1 hour

## SQL Injection Prevention
- Always use parameterized queries via Supabase client
- Never concatenate user input into SQL strings
- Use Pydantic validation for all inputs

## Authentication
- Verify JWT on every protected endpoint
- Check token expiration
- Validate user permissions before sensitive operations
