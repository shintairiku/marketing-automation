# Agent-20: Environment Variables and Secrets Security Report

**Status**: Completed
**Date**: 2026-02-04
**Findings Summary**: Critical:0, High:3, Medium:4, Low:3

---

## Investigated Files

- `backend/.env.example` (93 lines)
- `frontend/.env.example` (27 lines)
- `.env.example` (root, 20 lines)
- `backend/app/core/config.py` (202 lines)
- `frontend/next.config.js` (25 lines)
- `backend/app/domains/blog/services/crypto_service.py` (134 lines)

---

## Findings

### [HIGH] ENV-001: Sample API Key Format Exposed in .env.example

- **File**: `backend/.env.example`
- **Lines**: 5, 8, 34-35, 38-39
- **Issue**: The .env.example file contains API key prefixes that reveal the actual format:
  ```
  OPENAI_API_KEY=sk-proj-...
  GEMINI_API_KEY=AIzaSy...
  CLERK_SECRET_KEY=sk_live_...
  SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
  ```
- **Impact**:
  - Developers may copy real keys directly into this file and accidentally commit them
  - JWT prefix (eyJ) is valid Base64 that can be detected by secret scanning tools or grep attacks
  - Shows attackers the expected key format for social engineering
- **Remediation**: Change placeholders to generic format like `your-openai-api-key-here`

### [HIGH] ENV-002: Production API Key Format (sk_live_, pk_live_) in .env.example

- **File**: `backend/.env.example`
- **Lines**: 38-39
- **Issue**: Clerk credentials use production format `sk_live_...` and `pk_live_...`
  ```
  CLERK_SECRET_KEY=sk_live_...
  CLERK_PUBLISHABLE_KEY=pk_live_...
  ```
- **Impact**: Encourages developers to use production keys in development environments
- **Remediation**:
  - Change to `sk_test_xxx` / `pk_test_xxx` format
  - Add comment: "Use sk_live_/pk_live_ in production environment"

### [HIGH] ENV-003: CREDENTIAL_ENCRYPTION_KEY Generation and Requirements Undocumented

- **File**: `backend/.env.example` (NOT PRESENT)
- **File**: `backend/app/domains/blog/services/crypto_service.py:31-51`
- **Issue**: The encryption key for WordPress credentials is not documented in .env.example
- **Code Reference**:
  ```python
  key_b64 = encryption_key or settings.credential_encryption_key
  if not key_b64:
      raise ValueError(
          "暗号化キーが設定されていません。"
          "CREDENTIAL_ENCRYPTION_KEY環境変数を設定してください。"
      )
  ```
- **Impact**:
  - Developers may use weak keys
  - ValueError occurs at first use, not at application startup (delayed error)
  - Requirement for 32-byte Base64-encoded key is unclear
- **Remediation**:
  1. Add `CREDENTIAL_ENCRYPTION_KEY=` to .env.example
  2. Document key generation method:
     ```bash
     python -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"
     ```
  3. Add key existence check at application startup in config.py

### [MEDIUM] ENV-004: Localhost Fallback May Be Active in Production

- **Files**: Multiple frontend API routes (15+ locations)
  - `frontend/src/lib/api.ts:1`
  - `frontend/src/app/api/subscription/portal/route.ts:46`
  - `frontend/src/app/api/subscription/checkout/route.ts:68`
  - `frontend/src/app/(admin)/admin/users/page.tsx:102`
  - And many more...
- **Issue**: Fallback pattern `process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8080'`
- **Impact**:
  - Production deployment with missing env var will attempt localhost connections
  - Stripe callback URLs defaulting to localhost will break payment flow
  - Potential SSRF vector when localhost URLs are passed to external services
- **Remediation**:
  - Add build-time validation for required environment variables
  - Remove fallbacks and throw explicit errors when env vars are missing

### [MEDIUM] ENV-005: OPENAI_AGENTS_TRACE_INCLUDE_SENSITIVE_DATA Set to True

- **File**: `backend/.env.example:17`
- **Issue**: Sensitive data tracing enabled by default
  ```
  OPENAI_AGENTS_TRACE_INCLUDE_SENSITIVE_DATA=true
  ```
- **Impact**: User input data and model outputs may be logged and sent to OpenAI servers for tracing
- **Remediation**: Change default to `false`. Production should ALWAYS be `false`

### [MEDIUM] ENV-006: GCP Service Account JSON Stored Directly in Environment Variable

- **File**: `backend/.env.example:44`
- **File**: `backend/app/core/config.py:73-74`
- **Issue**: Full service account JSON is stored as environment variable
  ```
  GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account","project_id":"your-project-id",...}'
  ```
- **Impact**:
  - Environment variables can be exposed via `ps` command or process memory dumps
  - JSON contains private key, so exposure has severe impact
  - Violates principle of least privilege for credential access
- **Remediation**:
  1. Use `GOOGLE_APPLICATION_CREDENTIALS` (file path) standard approach
  2. Use Workload Identity Federation for Cloud Run deployments
  3. Recommend existing `GOOGLE_SERVICE_ACCOUNT_JSON_FILE` path option

### [MEDIUM] ENV-007: Incomplete .gitignore for Backend .env Files

- **File**: `.gitignore`
- **Current Content**:
  ```
  .env*.local
  .env
  .env.test
  next-env.d.ts
  ```
- **Issue**:
  - `backend/.env` is not explicitly excluded (relies on Git behavior for subdirectories)
  - Files like `backend/.env.production` could be accidentally committed
- **Remediation**:
  ```gitignore
  # All .env files across directories
  **/.env
  **/.env.*
  !**/.env.example
  ```

### [LOW] ENV-008: DEBUG=false Default but No Production Environment Check

- **File**: `backend/.env.example:93`
- **File**: `backend/app/core/config.py:58`
- **Issue**: DEBUG flag controls authentication bypass (see AUTH-001), but there's no dual check with ENVIRONMENT=production
- **Impact**: Production environment can still have DEBUG=true set
- **Remediation**: Add check in config.py to throw error if `ENVIRONMENT == "production" and DEBUG == True`

### [LOW] ENV-009: NEXT_PUBLIC_ Prefix Usage is Correct

- **Files**: `frontend/.env.example`, `frontend/src/` (entire directory)
- **Finding**: NEXT_PUBLIC_ prefix is correctly used only for client-safe values:
  - `NEXT_PUBLIC_SUPABASE_URL` - Safe (public URL)
  - `NEXT_PUBLIC_SUPABASE_ANON_KEY` - Safe (designed for client use)
  - `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` - Safe (designed for client use)
  - `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` - Safe (designed for client use)
  - `NEXT_PUBLIC_API_BASE_URL` - Safe (public URL)
- Secret keys (`STRIPE_SECRET_KEY`, `CLERK_SECRET_KEY`, `SUPABASE_SERVICE_ROLE_KEY`) do NOT use NEXT_PUBLIC_ prefix
- **Status**: No issue - correctly implemented

### [LOW] ENV-010: Encryption Implementation (crypto_service.py) is Secure

- **File**: `backend/app/domains/blog/services/crypto_service.py`
- **Finding**: Implementation follows security best practices:
  - Uses AES-256-GCM (authenticated encryption, industry standard)
  - Generates 12-byte random nonce for each encryption (NIST recommended)
  - Validates key length (32 bytes required)
  - Uses `cryptography` library (well-maintained, audited implementation)
  - Proper nonce + ciphertext concatenation
- **Status**: Implementation is secure. Only needs documentation for key management

---

## Positive Security Practices Observed

1. **NEXT_PUBLIC_ prefix correctly used** - Secrets are server-side only
2. **Supabase Service Role Key** - Only used in server-side API routes
3. **AES-256-GCM encryption** - WordPress credentials properly encrypted at rest
4. **Basic .gitignore protection** - .env files excluded (though incomplete)
5. **Clerk/Stripe secret keys** - Only accessed in server-side API routes
6. **cryptography library** - Uses established, audited crypto implementation

---

## Recommended Fixes (Priority Order)

### High Priority
1. **ENV-001**: Change .env.example API key placeholders to generic format (e.g., `your-api-key-here`)
2. **ENV-002**: Change Clerk credentials to `sk_test_/pk_test_` format with documentation
3. **ENV-003**: Document CREDENTIAL_ENCRYPTION_KEY requirements and add to .env.example

### Medium Priority
4. **ENV-004**: Add build-time validation for required environment variables in production
5. **ENV-005**: Change `OPENAI_AGENTS_TRACE_INCLUDE_SENSITIVE_DATA` default to `false`
6. **ENV-006**: Migrate to file-based GCP credentials or Workload Identity Federation
7. **ENV-007**: Strengthen .gitignore with `**/.env*` and `!**/.env.example`

### Low Priority
8. **ENV-008**: Add runtime check to prevent DEBUG=true in production environment

---

## Cross-References with Other Findings

- **AUTH-001 (Agent-01)**: ENV-008 is related - DEBUG mode enables JWT bypass
- **PROXY-001 (Agent-07)**: ENV-004 localhost fallback exacerbates proxy security issues
- **IMG-002 (Agent-06)**: Missing env validation affects all API routes

---

## Files to Update

1. `backend/.env.example` - Update placeholders, add CREDENTIAL_ENCRYPTION_KEY
2. `frontend/.env.example` - Add comments about required variables
3. `.gitignore` - Add `**/.env*` pattern
4. `backend/app/core/config.py` - Add DEBUG + ENVIRONMENT check
5. `frontend/next.config.js` - Remove localhost fallback or add production validation
