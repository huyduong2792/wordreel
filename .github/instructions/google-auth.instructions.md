---
applyTo: "**/auth/**"
description: "Google OAuth implementation guide for WordReel"
---

# Google Authentication - WordReel

> **Purpose**: This document explains how Google OAuth authentication works in the WordReel project.

---

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Authentication Flow](#authentication-flow)
4. [File Reference](#file-reference)
5. [Configuration](#configuration)
6. [How It Works Step-by-Step](#how-it-works-step-by-step)
7. [Token Management](#token-management)
8. [Customization](#customization)
9. [Troubleshooting](#troubleshooting)

---

## Overview

WordReel uses **Supabase Auth** with **Google OAuth 2.0** for social login. This approach provides:

- ✅ Secure OAuth 2.0 implementation
- ✅ Automatic token refresh
- ✅ Session management
- ✅ No need to store Google credentials on our backend
- ✅ Supabase handles token exchange securely

### Tech Stack
| Component | Technology |
|-----------|------------|
| OAuth Provider | Google OAuth 2.0 |
| Auth Backend | Supabase Auth |
| Frontend Client | @supabase/supabase-js |
| Token Storage | localStorage + Supabase session |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        GOOGLE AUTH ARCHITECTURE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐                                                           │
│  │   Frontend   │                                                           │
│  │  (React/     │                                                           │
│  │   Astro)     │                                                           │
│  └──────┬───────┘                                                           │
│         │                                                                    │
│         │ 1. User clicks "Continue with Google"                             │
│         │    signInWithGoogle() called                                      │
│         ▼                                                                    │
│  ┌──────────────┐                                                           │
│  │   Supabase   │  2. Redirects to Google OAuth                             │
│  │   Auth       │     with client_id & redirect_uri                         │
│  └──────┬───────┘     (redirect_uri = supabase.co/auth/v1/callback)         │
│         │                                                                    │
│         ▼                                                                    │
│  ┌──────────────┐                                                           │
│  │   Google     │  3. User sees Google consent screen                       │
│  │   OAuth      │     "Continue to kmtcis...supabase.co"                    │
│  │   Server     │     (This shows Supabase URL, not your domain)            │
│  └──────┬───────┘                                                           │
│         │                                                                    │
│         │ 4. User approves, Google sends auth code                          │
│         ▼                                                                    │
│  ┌──────────────┐                                                           │
│  │   Supabase   │  5. Exchanges code for tokens                             │
│  │   Auth       │     Creates/updates user in auth.users                    │
│  │   Callback   │     Sets session cookies                                  │
│  └──────┬───────┘                                                           │
│         │                                                                    │
│         │ 6. Redirects to your app's callback URL                           │
│         │    /auth/callback?code=xxx                                        │
│         ▼                                                                    │
│  ┌──────────────┐                                                           │
│  │   Frontend   │  7. callback.astro extracts session                       │
│  │   /auth/     │     Stores token in localStorage                          │
│  │   callback   │     Redirects to home                                     │
│  └──────┬───────┘                                                           │
│         │                                                                    │
│         │ 8. AuthContext detects session change                             │
│         │    Updates user state                                             │
│         ▼                                                                    │
│  ┌──────────────┐                                                           │
│  │   User is    │  9. User is now logged in                                 │
│  │   Logged In  │     Token used for API calls                              │
│  └──────────────┘                                                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Authentication Flow

### Login Flow (Sequence Diagram)

```
┌──────┐     ┌──────────┐     ┌──────────┐     ┌────────┐     ┌─────────┐
│ User │     │ Frontend │     │ Supabase │     │ Google │     │ Backend │
└──┬───┘     └────┬─────┘     └────┬─────┘     └───┬────┘     └────┬────┘
   │              │                │               │               │
   │ Click Google │                │               │               │
   │ Login Button │                │               │               │
   │─────────────>│                │               │               │
   │              │                │               │               │
   │              │ signInWithOAuth│               │               │
   │              │ (provider:     │               │               │
   │              │  'google')     │               │               │
   │              │───────────────>│               │               │
   │              │                │               │               │
   │              │    Redirect to Google          │               │
   │<─────────────────────────────────────────────>│               │
   │              │                │               │               │
   │    Google Consent Screen      │               │               │
   │    "Continue to supabase.co"  │               │               │
   │─────────────────────────────────────────────>│               │
   │              │                │               │               │
   │              │                │  Auth Code    │               │
   │              │                │<──────────────│               │
   │              │                │               │               │
   │              │                │ Exchange Code │               │
   │              │                │ for Tokens    │               │
   │              │                │──────────────>│               │
   │              │                │               │               │
   │              │                │ Access Token  │               │
   │              │                │ + User Info   │               │
   │              │                │<──────────────│               │
   │              │                │               │               │
   │    Redirect to /auth/callback │               │               │
   │<─────────────────────────────│               │               │
   │              │                │               │               │
   │              │ Get Session    │               │               │
   │              │───────────────>│               │               │
   │              │                │               │               │
   │              │ Session +      │               │               │
   │              │ Access Token   │               │               │
   │              │<───────────────│               │               │
   │              │                │               │               │
   │              │ Store in       │               │               │
   │              │ localStorage   │               │               │
   │              │                │               │               │
   │ Redirect to  │                │               │               │
   │ Home (/)     │                │               │               │
   │<─────────────│                │               │               │
   │              │                │               │               │
   │              │                │               │    API Call   │
   │              │                │               │    with Token │
   │              │────────────────────────────────────────────────>│
   │              │                │               │               │
```

### Logout Flow

```
┌──────┐     ┌──────────┐     ┌──────────┐
│ User │     │ Frontend │     │ Supabase │
└──┬───┘     └────┬─────┘     └────┬─────┘
   │              │                │
   │ Click Logout │                │
   │─────────────>│                │
   │              │                │
   │              │ signOut()      │
   │              │───────────────>│
   │              │                │
   │              │   Session      │
   │              │   Invalidated  │
   │              │<───────────────│
   │              │                │
   │              │ Clear          │
   │              │ localStorage   │
   │              │                │
   │              │ Update         │
   │              │ AuthContext    │
   │              │ (user = null)  │
   │              │                │
   │ UI Updates   │                │
   │ (Show Login) │                │
   │<─────────────│                │
```

---

## File Reference

### Frontend Files

| File | Purpose |
|------|---------|
| `web/src/lib/supabase.ts` | Supabase client initialization and OAuth helper functions |
| `web/src/pages/auth/callback.astro` | Handles OAuth redirect, extracts session, stores token |
| `web/src/components/auth/GoogleLoginButton.tsx` | Google login button component |
| `web/src/components/auth/AuthContext.tsx` | Auth state management, session listener |
| `web/src/components/auth/AuthModal.tsx` | Login modal with Google button |
| `web/src/components/auth/UserMenu.tsx` | User dropdown with logout button |
| `web/.env` | Environment variables (Supabase URL, Anon Key) |

### Backend Files

| File | Purpose |
|------|---------|
| `backend/auth/utils.py` | JWT verification using Supabase |
| `backend/database/supabase_client.py` | Supabase client for backend |

---

## Configuration

### 1. Google Cloud Console Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select a project
3. Navigate to **APIs & Services** → **Credentials**
4. Create **OAuth 2.0 Client ID** (Web application)
5. Add Authorized Redirect URI:
   ```
   https://kmtcisddqekkrzurxvih.supabase.co/auth/v1/callback
   ```
6. Copy **Client ID** and **Client Secret**

### 2. Supabase Dashboard Setup

1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Select your project
3. Navigate to **Authentication** → **Providers**
4. Enable **Google**
5. Paste Client ID and Client Secret from Google
6. Save

### 3. Frontend Environment Variables

Create `web/.env`:

```bash
# Supabase Configuration (public keys - safe for frontend)
PUBLIC_SUPABASE_URL=https://kmtcisddqekkrzurxvih.supabase.co
PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Backend API URL
PUBLIC_API_URL=http://localhost:8000/api/v1
```

### 4. Backend Environment Variables

In `backend/.env`:

```bash
# Supabase Configuration
SUPABASE_URL=https://kmtcisddqekkrzurxvih.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  # anon key
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  # service role key
SUPABASE_JWT_SECRET=jIkgNq/Bs7jGBxGeh+CPgyL2nzpLxOureyYXZR0YqYM...
```

---

## How It Works Step-by-Step

### Step 1: User Clicks "Continue with Google"

**File**: `web/src/components/auth/GoogleLoginButton.tsx`

```typescript
const handleClick = async () => {
    setIsLoading(true);
    try {
        await signInWithGoogle();
        // Redirect happens automatically via Supabase
    } catch (error) {
        // Handle error
    }
};
```

### Step 2: Supabase Initiates OAuth

**File**: `web/src/lib/supabase.ts`

```typescript
export async function signInWithGoogle() {
    const { data, error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
            redirectTo: `${window.location.origin}/auth/callback`,
            queryParams: {
                access_type: 'offline',
                prompt: 'consent',
            },
        },
    });
    // Browser redirects to Google
}
```

**What happens**:
- Supabase generates OAuth URL with your Google Client ID
- Browser redirects to `accounts.google.com`
- User sees "Continue to kmtcisddqekkrzurxvih.supabase.co"

### Step 3: Google Consent & Redirect

After user approves:
1. Google sends authorization code to Supabase callback
2. Supabase exchanges code for access token + user info
3. Supabase creates/updates user in `auth.users` table
4. Supabase redirects to your `redirectTo` URL

### Step 4: Handle Callback

**File**: `web/src/pages/auth/callback.astro`

```javascript
async function handleCallback() {
    // Get session from Supabase (they handle the token exchange)
    const { data: { session }, error } = await supabase.auth.getSession();

    if (session) {
        // Store access token for API calls
        localStorage.setItem('wordreel_token', session.access_token);
        
        // Store user info
        localStorage.setItem('wordreel_user', JSON.stringify({
            id: session.user.id,
            email: session.user.email,
            username: session.user.user_metadata?.full_name,
            avatar_url: session.user.user_metadata?.avatar_url,
        }));

        // Redirect to home
        window.location.href = '/';
    }
}
```

### Step 5: AuthContext Updates

**File**: `web/src/components/auth/AuthContext.tsx`

```typescript
// Listen for auth state changes
const { data: { subscription } } = supabase.auth.onAuthStateChange(
    async (event, session) => {
        if (event === 'SIGNED_IN' && session?.user) {
            // Update user state
            setUser(userData);
            localStorage.setItem('wordreel_user', JSON.stringify(userData));
            localStorage.setItem('wordreel_token', session.access_token);
        } else if (event === 'SIGNED_OUT') {
            setUser(null);
            localStorage.removeItem('wordreel_user');
            localStorage.removeItem('wordreel_token');
        }
    }
);
```

### Step 6: Backend Token Verification

**File**: `backend/auth/utils.py`

```python
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    
    # Verify with Supabase - works for both email/password AND OAuth tokens
    supabase = get_supabase()
    user_response = supabase.auth.get_user(token)
    
    if not user_response or not user_response.user:
        raise credentials_exception
        
    return user_response.user
```

---

## Token Management

### Token Generation Flow with Google OAuth

When you login with Google, there are **two sets of tokens** from different providers:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TOKEN GENERATION FLOW                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. User clicks "Login with Google"                                          │
│                    │                                                         │
│                    ▼                                                         │
│  2. Redirect to Google ──────────────────────────────────────┐               │
│                                                              │               │
│                                                              ▼               │
│  3. Google authenticates user ─────► Google issues tokens                    │
│     (password/2FA)                   • Google Access Token   │               │
│                                      • Google Refresh Token  │               │
│                                              │                               │
│                                              ▼                               │
│  4. Google redirects back to Supabase with authorization code                │
│                                              │                               │
│                                              ▼                               │
│  5. Supabase exchanges code ──────► Supabase issues tokens                   │
│     with Google                      • Supabase Access Token │ ◄── YOU USE   │
│                                      • Supabase Refresh Token│     THESE     │
│                                              │                               │
│                                              ▼                               │
│  6. Supabase redirects to your app with Supabase tokens                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Two Different Token Sets

| Token Set | Generated By | Purpose | Your App Sees? |
|-----------|--------------|---------|----------------|
| **Google Tokens** | Google OAuth servers | Supabase uses internally to verify identity & get user info | ❌ No |
| **Supabase Tokens** | Supabase Auth servers | Your app uses for API authentication | ✅ Yes |

#### What Your App Receives

```typescript
// After Google login, you get SUPABASE tokens (not Google tokens)
const { data: { session } } = await supabase.auth.getSession();

session.access_token   // ← Generated by SUPABASE (JWT, ~1 hour)
session.refresh_token  // ← Generated by SUPABASE (~7 days)
session.user           // ← User info (originally from Google, stored by Supabase)
```

#### Where Google Tokens Go

Google tokens stay **inside Supabase** - your app never sees them:

| Google Token | Stored In | Used For |
|--------------|-----------|----------|
| Access Token | Supabase servers | Fetch user profile from Google |
| Refresh Token | Supabase servers | Refresh Google access if needed |

#### Summary

| Question | Answer |
|----------|--------|
| Who generates the JWT your app uses? | **Supabase** |
| Who verifies user identity? | **Google** (via OAuth) |
| Who stores the session? | **Supabase** |
| What does your backend verify? | **Supabase JWT** (not Google's) |

```python
# Backend (auth/utils.py) verifies Supabase JWT
user_response = supabase.auth.get_user(token)  # Supabase validates its own JWT
```

> **Key Insight**: Google is the **identity provider** (proves who you are), but Supabase is the **token issuer** (creates the JWT your app actually uses).

### Token Storage

| Storage | Content | Purpose |
|---------|---------|---------|
| `localStorage['wordreel_token']` | JWT access token | API Authorization header |
| `localStorage['wordreel_user']` | User object (JSON) | Display user info in UI |
| Supabase Session | Full session | Token refresh, session management |

### Token Refresh

Supabase handles token refresh automatically via `onAuthStateChange`:

```typescript
supabase.auth.onAuthStateChange((event, session) => {
    if (event === 'TOKEN_REFRESHED' && session) {
        // Update stored token
        localStorage.setItem('wordreel_token', session.access_token);
    }
});
```

### Token Lifecycle

| Event | Duration | Action |
|-------|----------|--------|
| Initial Token | 1 hour | Issued on login |
| Refresh Token | 7 days | Used to get new access token |
| Token Refresh | Automatic | Supabase refreshes before expiry |
| Logout | Immediate | All tokens invalidated |

---

## Customization

### Custom Domain (Hide Supabase URL)

By default, Google shows "Continue to kmtcisddqekkrzurxvih.supabase.co". To customize:

1. **Supabase Pro Plan Required**
2. Go to Supabase Dashboard → **Settings** → **Custom Domains**
3. Add your domain (e.g., `auth.wordreel.com`)
4. Configure DNS:
   ```
   CNAME auth.wordreel.com → kmtcisddqekkrzurxvih.supabase.co
   ```
5. Update Google OAuth redirect URI:
   ```
   https://auth.wordreel.com/auth/v1/callback
   ```

After setup, Google will show: "Continue to auth.wordreel.com"

### Add More OAuth Providers

To add GitHub, Facebook, etc.:

1. Enable provider in Supabase Dashboard
2. Create OAuth app on provider's platform
3. Add button in `AuthModal.tsx`:

```typescript
import { signInWithGitHub } from '../../lib/supabase';

<button onClick={signInWithGitHub}>
    Continue with GitHub
</button>
```

4. Add function in `supabase.ts`:

```typescript
export async function signInWithGitHub() {
    return supabase.auth.signInWithOAuth({
        provider: 'github',
        options: {
            redirectTo: `${window.location.origin}/auth/callback`,
        },
    });
}
```

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| "Redirect URI mismatch" | Google OAuth config wrong | Add correct URI in Google Console |
| "Invalid client_id" | Wrong Supabase config | Check Client ID in Supabase |
| Token not persisting | localStorage issue | Check browser console for errors |
| "User not found" | Token invalid/expired | Clear localStorage, re-login |
| CORS errors | Backend config | Check CORS_ORIGINS in backend/.env |

### Debug Steps

1. **Check Browser Console** for errors
2. **Check Network Tab** for failed requests
3. **Verify localStorage**:
   ```javascript
   console.log(localStorage.getItem('wordreel_token'));
   console.log(localStorage.getItem('wordreel_user'));
   ```
4. **Check Supabase Logs**: Dashboard → Logs → Auth

### Test Authentication

```bash
# Test token with backend API
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8000/api/v1/posts/feed
```

---

## Security Considerations

1. **Never expose Service Key** - Only use Anon Key in frontend
2. **JWT Secret** - Only used in backend for local verification
3. **HTTPS** - Always use HTTPS in production
4. **Token Storage** - localStorage is vulnerable to XSS; consider httpOnly cookies for production
5. **CORS** - Restrict to your domains only

---

## Related Documentation

- [Supabase Auth Docs](https://supabase.com/docs/guides/auth)
- [Google OAuth 2.0](https://developers.google.com/identity/protocols/oauth2)
- [JWT.io](https://jwt.io/) - Debug JWT tokens
