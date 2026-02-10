# Security Audit Report

**Project:** Marketing Automation / Blog AI Platform
**Date:** 2026-02-10
**Auditor:** Claude Opus 4.6 (Automated Security Audit)
**Scope:** Full codebase review (backend, frontend, infrastructure, database)
**Branch:** develop (commit 8e162b8)

---

## Executive Summary

This security audit of the Marketing Automation / Blog AI platform identified **4 Critical**, **7 High**, **8 Medium**, and **6 Low** severity vulnerabilities across the codebase.

The most urgent finding is the **exposure of live production secrets** (API keys, database credentials, encryption keys, and webhook secrets) in plaintext within local `.env` files that, while not committed to Git, are present on disk and could be leaked through backup, developer machine compromise, or accidental inclusion. A closely related critical finding is the **DEBUG mode JWT bypass** mechanism that completely disables authentication signature verification when the `DEBUG` environment variable is set to `true`.

Additional critical issues include **unauthenticated API endpoints** that allow arbitrary image generation consuming cloud resources, and a **Server-Side Request Forgery (SSRF) vector** in the WordPress connection URL endpoint that can be abused to probe internal network services.

The platform has solid foundations in many areas -- Clerk JWT verification with JWKS rotation, AES-256-GCM credential encryption, Stripe webhook signature verification, and path traversal prevention on image serving. However, several gaps in rate limiting, input validation, CORS configuration, and data access controls require immediate attention before or shortly after production deployment.

**Risk Score: HIGH** -- Immediate remediation of Critical and High items is recommended before continued public exposure.

---

## Critical Vulnerabilities

### CRIT-01: Live Production Secrets Exposed in Local `.env` Files

- **Location:** `/home/als0028/study/shintairiku/marketing-automation/backend/.env` (lines 1-100+), `/home/als0028/study/shintairiku/marketing-automation/frontend/.env.local` (lines 1-40+)
- **Description:** Both `backend/.env` and `frontend/.env.local` contain plaintext production/test secrets including:
  - OpenAI API key (`sk-proj-HryhRJdP...`)
  - Supabase service role key (full JWT with `service_role` claim)
  - Supabase database password (`4NFiXju7HQzYwCfR`)
  - Stripe secret key (`sk_test_51RBxQo...`)
  - Stripe webhook secret (multiple instances)
  - Clerk secret key (`sk_test_23X1pk...`)
  - Google AI API key (`AIzaSyAuQBm8...`)
  - Anthropic API key (`sk-ant-api03-16b5hc...`)
  - Notion API key (`ntn_Ex755093...`)
  - WandB API key (`e6a4460ed7...`)
  - Credential encryption key (`Hy1SVRBanr...`)
  - Google OAuth client secret (`GOCSPX-JU0XEEvV9...`)

  While `.env` is listed in `.gitignore` and is not tracked in Git, the files exist on the local filesystem. If a developer's machine is compromised, if these files are accidentally included in a Docker image, or if they are backed up to an unencrypted location, all of these secrets are exposed. The Supabase service role key is particularly dangerous as it bypasses all Row Level Security policies.

- **Impact:** Complete compromise of all connected services. An attacker with these keys could: access and modify all database records (bypassing RLS), make unlimited AI API calls at the project's expense, access Stripe billing data and manipulate subscriptions, impersonate any user via Clerk, read/write to Google Cloud Storage, and decrypt WordPress credentials.

- **Remediation Checklist:**
  - [ ] **Immediately rotate all secrets** listed above in their respective service dashboards (OpenAI, Supabase, Stripe, Clerk, Google Cloud, Anthropic, Notion, WandB)
  - [ ] Use a secrets manager (Google Secret Manager, since the platform is deployed on Cloud Run) instead of `.env` files for production deployments
  - [ ] Add `backend/.env` and `frontend/.env.local` to a pre-commit hook that prevents accidental commits of files containing secret patterns
  - [ ] In Docker builds, inject secrets via Cloud Run environment variables or Secret Manager volume mounts -- never copy `.env` files into images
  - [ ] Remove the `SUPABASE_DB_PASSWORD` from frontend `.env.local` entirely -- the frontend should never have direct database access
  - [ ] Ensure `.env.example` files contain only placeholder values (already the case, but verify regularly)

- **References:** [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html), CWE-798

---

### CRIT-02: DEBUG Mode Completely Disables JWT Signature Verification

- **Location:** `/home/als0028/study/shintairiku/marketing-automation/backend/app/common/auth.py` (lines 139-153)
- **Description:** When the environment variable `DEBUG=true` is set, the `verify_clerk_token()` function skips all JWT signature verification:

  ```python
  # backend/app/common/auth.py lines 139-153
  if DEBUG_MODE:
      logger.warning("⚠️ [AUTH] DEBUG MODE: Skipping JWT signature verification!")
      logger.warning("⚠️ [AUTH] This is insecure and should NOT be used in production!")
      try:
          decoded = jwt.decode(token, options={"verify_signature": False})
          return decoded
      except jwt.InvalidTokenError as e:
          raise HTTPException(status_code=401, detail=f"Invalid token format: {e}")
  ```

  This means any attacker can craft a JWT with an arbitrary `sub` claim (user ID) and access any endpoint as any user. The `DEBUG` variable is controlled by environment configuration and defaults to `false`, but there is no runtime safeguard preventing it from being accidentally enabled in production. Additionally, the current `backend/.env` has `ENABLE_DEBUG_CONSOLE=true` and `OPENAI_AGENTS_TRACE_INCLUDE_SENSITIVE_DATA=true`, indicating a pattern of debug features being left enabled.

  A separate function `validate_token_without_signature()` (line 318) also exists with no signature verification, though it appears to be for testing only.

- **Impact:** If `DEBUG=true` is ever set in production (accidentally or through environment variable injection), **all API authentication is completely bypassed**. An attacker could impersonate any user, access admin endpoints, modify data, and perform billing operations.

- **Remediation Checklist:**
  - [ ] **Remove the DEBUG mode bypass entirely** from `verify_clerk_token()`. Production code should never have a "skip authentication" switch
  - [ ] If a debug mode is absolutely needed for local development, implement it as a compile-time flag or a separate development-only auth module that is not included in production builds
  - [ ] Remove the `validate_token_without_signature()` function or gate it behind `if __name__ == "__main__"` for CLI testing only
  - [ ] Add a startup check in `main.py` that logs a CRITICAL error and exits if `DEBUG=true` is detected alongside production-like configuration (e.g., non-localhost `SUPABASE_URL`)
  - [ ] Set `DEBUG=false` explicitly in Cloud Run environment configuration and document that it must never be set to `true` in production

  ```python
  # Recommended: Remove debug bypass entirely
  def verify_clerk_token(token: str) -> dict:
      try:
          jwk_client = _get_jwk_client()
          signing_key = jwk_client.get_signing_key(token)
          decoded = jwt.decode(
              token,
              signing_key.key,
              algorithms=["RS256"],
              options={
                  "verify_signature": True,
                  "verify_exp": True,
                  "verify_iat": True,
                  "require": ["exp", "iat", "sub"],
              }
          )
          return decoded
      except jwt.ExpiredSignatureError:
          raise HTTPException(status_code=401, detail="Token has expired")
      except jwt.InvalidTokenError as e:
          raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
      except PyJWKClientError:
          raise HTTPException(status_code=503, detail="Authentication service temporarily unavailable")
  ```

- **References:** CWE-287 (Improper Authentication), CWE-489 (Active Debug Code)

---

### CRIT-03: Unauthenticated Endpoints Exposing Expensive Operations

- **Location:** `/home/als0028/study/shintairiku/marketing-automation/backend/app/domains/image_generation/endpoints.py`
- **Description:** Two endpoints in the image generation module lack authentication:

  1. **`GET /images/test-config`** (line 67) -- Exposes internal Google Cloud configuration including project ID, credential status, and client type. No authentication required.

  2. **`POST /images/generate-from-placeholder`** (line 258) -- Triggers Vertex AI image generation (Imagen-4) without any authentication. Any anonymous user can call this endpoint to generate images, consuming Google Cloud resources at the project's expense.

  ```python
  # Line 258-276 -- No Depends(get_current_user_id_from_token) parameter
  @router.post("/generate-from-placeholder", response_model=ImageGenerationResponse)
  async def generate_image_from_placeholder(request: GenerateImageFromPlaceholderRequest):
      """画像プレースホルダーの情報から画像を生成する"""
      try:
          result = await image_generation_service.generate_image_from_placeholder(
              placeholder_id=request.placeholder_id,
              description_jp=request.description_jp,
              prompt_en=request.prompt_en,
              additional_context=request.additional_context
          )
          ...
  ```

  Since the backend is publicly accessible on Cloud Run, these endpoints are accessible to anyone on the internet.

- **Impact:**
  - Financial: Unlimited Vertex AI image generation costs charged to the project's GCP billing account
  - Information disclosure: The `test-config` endpoint reveals infrastructure details useful for further attacks
  - Resource exhaustion: Repeated calls could exhaust GCP quotas, causing denial of service for legitimate users

- **Remediation Checklist:**
  - [ ] Add `current_user_id: str = Depends(get_current_user_id_from_token)` to `generate_image_from_placeholder`
  - [ ] Either remove `test-config` entirely or protect it with `admin_email: str = Depends(get_admin_user_email_from_token)`
  - [ ] Audit all other endpoints to verify they require authentication (search for `async def` without `Depends(get_current_user_id_from_token)` or `Depends(get_admin_user_email_from_token)`)

- **References:** CWE-306 (Missing Authentication for Critical Function), OWASP API2:2023 Broken Authentication

---

### CRIT-04: Server-Side Request Forgery (SSRF) via WordPress Connection URL

- **Location:** `/home/als0028/study/shintairiku/marketing-automation/backend/app/domains/blog/endpoints.py` (lines 476-580)
- **Description:** The `POST /blog/connect/wordpress/url` endpoint accepts an arbitrary URL from the user, parses it, and makes an HTTP POST request to the derived `register_endpoint` from the server side:

  ```python
  # Line 519-534
  register_endpoint = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

  async with httpx.AsyncClient(timeout=30.0) as client:
      register_response = await client.post(
          register_endpoint,
          json={
              "registration_code": registration_code,
              "saas_identifier": "BlogAI",
          },
      )
  ```

  There is no validation that the URL points to an actual WordPress site or an external host. An attacker can supply URLs like:
  - `http://169.254.169.254/computeMetadata/v1/?code=x` -- GCP metadata service
  - `http://localhost:8000/admin/users?code=x` -- Internal backend API
  - `http://10.0.0.1/internal-service?code=x` -- Internal network services

  On Cloud Run, the GCP metadata server at `169.254.169.254` is accessible and could leak service account tokens, project configuration, and other sensitive metadata.

- **Impact:** An attacker could:
  - Read GCP metadata including service account access tokens
  - Probe internal network services not exposed to the internet
  - Potentially access other Cloud Run services in the same VPC
  - Use the server as a proxy for port scanning internal infrastructure

- **Remediation Checklist:**
  - [ ] Implement URL validation that rejects internal/private IP addresses and metadata endpoints:
    ```python
    import ipaddress
    from urllib.parse import urlparse

    BLOCKED_HOSTS = {'169.254.169.254', 'metadata.google.internal', 'localhost', '127.0.0.1'}

    def validate_external_url(url: str) -> bool:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return False
        if hostname in BLOCKED_HOSTS:
            return False
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                return False
        except ValueError:
            pass  # hostname is a domain name, not an IP
        if parsed.scheme not in ('http', 'https'):
            return False
        return True
    ```
  - [ ] Apply the same validation to the `GET /blog/connect/wordpress` redirect endpoint (line 201) which passes `mcp_endpoint` and `register_endpoint` to the frontend
  - [ ] Apply the same validation to the `POST /blog/connect/wordpress` (site register) endpoint and `POST /blog/sites/register` endpoint
  - [ ] Consider restricting the WordPress connection URL to HTTPS-only schemes

- **References:** CWE-918 (SSRF), OWASP API8:2023 Security Misconfiguration

---

## High Vulnerabilities

### HIGH-01: API Proxy Has No Path Restriction -- Open Relay Risk

- **Location:** `/home/als0028/study/shintairiku/marketing-automation/frontend/src/app/api/proxy/[...path]/route.ts`, `/home/als0028/study/shintairiku/marketing-automation/frontend/next.config.js` (rewrite rules)
- **Description:** The API proxy at `/api/proxy/[...path]` forwards any request to `NEXT_PUBLIC_API_BASE_URL` with no path restrictions. While it correctly forwards the Authorization header, it does not validate or restrict which backend paths can be accessed. Combined with the `next.config.js` rewrite rule, this creates two proxy layers:

  ```javascript
  // next.config.js
  async rewrites() {
    return [{
      source: '/api/proxy/:path*',
      destination: `${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'}/:path*`,
    }];
  }
  ```

  The proxy also sets overly permissive CORS headers:
  ```typescript
  // route.ts OPTIONS handler
  headers: {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  }
  ```

  If `NEXT_PUBLIC_API_BASE_URL` is ever changed to an internal service URL, the proxy becomes a full SSRF relay. Additionally, the `Access-Control-Allow-Origin: '*'` on the proxy allows any website to make cross-origin requests through it.

- **Impact:** Any website can make cross-origin requests to the backend API via this proxy. If the backend URL is misconfigured, the proxy could be used to access internal services.

- **Remediation Checklist:**
  - [ ] Implement an allowlist of permitted path prefixes in the proxy (e.g., `/articles/`, `/blog/`, `/organizations/`, `/companies/`, `/images/`, `/usage/`, `/admin/`, `/style-templates/`)
  - [ ] Remove `Access-Control-Allow-Origin: '*'` from the proxy responses; use the specific frontend origin instead
  - [ ] Remove the OPTIONS handler that returns `*` for all CORS headers
  - [ ] Consider removing the dual proxy setup (Next.js rewrite + route handler) and using only one mechanism

- **References:** CWE-441 (Unintended Proxy or Intermediary), OWASP API8:2023

---

### HIGH-02: No Rate Limiting on Expensive AI Operations

- **Location:** Backend endpoints: `/blog/generation/start`, `/articles/generation/start`, `/images/generate`, `/images/generate-and-link`, `/articles/ai-content-generation`, `/blog/ai-questions`
- **Description:** There is no rate limiting on any API endpoint. AI generation operations (LLM calls, image generation) are expensive and can be triggered repeatedly by authenticated users. While the usage limit system tracks article generation counts, there is:
  - No per-minute/per-hour rate limit on any endpoint
  - No rate limit on `/blog/ai-questions` which triggers LLM calls
  - No rate limit on image generation endpoints
  - No rate limit on the `/articles/ai-content-generation` endpoint
  - No rate limit on login/auth attempts
  - No rate limit on the API proxy

  The backend FastAPI application has no rate-limiting middleware. Cloud Run can auto-scale, but this means costs scale with abuse rather than being capped.

- **Impact:** An authenticated user (or attacker with a valid token) could:
  - Generate thousands of dollars in AI API costs in minutes
  - Exhaust API quotas for OpenAI, Google Cloud, Anthropic, etc.
  - Cause denial of service for other users by consuming all available Cloud Run instances
  - Brute-force the admin authentication by trying many tokens

- **Remediation Checklist:**
  - [ ] Add a rate-limiting middleware to FastAPI (e.g., `slowapi` or a custom middleware using Redis/Memorystore):
    ```python
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter

    @router.post("/generation/start")
    @limiter.limit("10/minute")
    async def start_generation(request: Request, ...):
        ...
    ```
  - [ ] Implement per-user rate limits (using the authenticated user ID as the key) for expensive operations
  - [ ] Set Cloud Run maximum instance limits to cap auto-scaling costs
  - [ ] Add rate limiting to the Next.js API routes for subscription/webhook endpoints
  - [ ] Consider implementing request cost budgets per user per time window

- **References:** CWE-770 (Allocation of Resources Without Limits), OWASP API4:2023 Unrestricted Resource Consumption

---

### HIGH-03: Backend Uses Supabase Service Role Key for All Operations -- RLS Bypassed

- **Location:** `/home/als0028/study/shintairiku/marketing-automation/backend/app/common/database.py` (line 12-13)
- **Description:** The backend creates a single global Supabase client using the `service_role` key:

  ```python
  def create_supabase_client() -> Client:
      supabase_client = create_client(
          settings.supabase_url,
          settings.supabase_service_role_key  # Bypasses all RLS
      )
      return supabase_client
  ```

  The `service_role` key has full access to all tables, bypassing all Row Level Security (RLS) policies. While migration `20260130000003_fix_org_clerk_compat.sql` acknowledges this by removing many RLS policies (since they relied on `auth.uid()` which is `NULL` when using service_role), this means the backend application code is solely responsible for access control. Any bug in user ID filtering in queries allows cross-user data access.

  For example, if a developer forgets to add `.eq("user_id", current_user_id)` to a query, all users' data would be returned. The codebase already has one authenticated endpoint (`POST /images/generate-from-placeholder`) that lacks user scoping entirely.

- **Impact:** A single missing `.eq("user_id", ...)` filter in any query exposes data across all users. There is no defense-in-depth layer at the database level.

- **Remediation Checklist:**
  - [ ] For user-facing queries, create a request-scoped Supabase client that uses a custom JWT with the user's ID, so RLS policies can function as a second layer of defense
  - [ ] Re-enable RLS policies on critical tables (articles, company_info, style_guide_templates, wordpress_sites) with service-role-aware policies that still filter by user_id
  - [ ] Audit all Supabase queries to ensure they include proper user_id filtering
  - [ ] Add integration tests that verify cross-user data isolation for each endpoint

- **References:** CWE-284 (Improper Access Control), CWE-862 (Missing Authorization)

---

### HIGH-04: JWT Token Does Not Validate `iss` (Issuer) or `aud` (Audience) Claims

- **Location:** `/home/als0028/study/shintairiku/marketing-automation/backend/app/common/auth.py` (lines 159-168)
- **Description:** The JWT verification checks `exp`, `iat`, and `sub` claims, but does not validate `iss` (issuer) or `aud` (audience):

  ```python
  decoded = jwt.decode(
      token,
      signing_key.key,
      algorithms=["RS256"],
      options={
          "verify_signature": True,
          "verify_exp": True,
          "verify_iat": True,
          "require": ["exp", "iat", "sub"],
      }
      # Missing: issuer= and audience= parameters
  )
  ```

  Without `iss` and `aud` validation, a JWT issued by a different Clerk application (sharing the same JWKS endpoint or a key collision scenario) could be accepted. While the RS256 signature verification with JWKS mitigates most token forgery attacks, the lack of audience validation is a deviation from JWT security best practices.

- **Impact:** In a multi-tenant Clerk environment or if Clerk keys are shared across applications, tokens from other applications could potentially be accepted. This is a defense-in-depth concern.

- **Remediation Checklist:**
  - [ ] Add `issuer` and `audience` validation to the `jwt.decode()` call:
    ```python
    decoded = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        issuer=f"https://{clerk_frontend_api}",
        audience="your-clerk-app-id",  # or use azp claim
        options={
            "verify_signature": True,
            "verify_exp": True,
            "verify_iat": True,
            "verify_iss": True,
            "verify_aud": True,
            "require": ["exp", "iat", "sub"],
        }
    )
    ```

- **References:** CWE-287, [RFC 7519 Section 4.1](https://tools.ietf.org/html/rfc7519#section-4.1)

---

### HIGH-05: Sensitive Data Tracing Enabled in Production Configuration

- **Location:** `/home/als0028/study/shintairiku/marketing-automation/backend/.env` (line 34), `/home/als0028/study/shintairiku/marketing-automation/backend/app/core/config.py` (line 111)
- **Description:** The backend `.env` file sets `OPENAI_AGENTS_TRACE_INCLUDE_SENSITIVE_DATA=true`, which causes the OpenAI Agents SDK to include full model inputs and outputs (including user content, article text, and potentially PII) in tracing data sent to OpenAI's servers:

  ```
  # backend/.env
  OPENAI_AGENTS_TRACE_INCLUDE_SENSITIVE_DATA=true
  ```

  Additionally, `ENABLE_DEBUG_CONSOLE=true` is set, though its effect depends on how it is consumed.

- **Impact:** User-generated content, business data, and potentially PII are sent to OpenAI's tracing servers. This may violate data protection regulations (GDPR, APPI) and user privacy expectations.

- **Remediation Checklist:**
  - [ ] Set `OPENAI_AGENTS_TRACE_INCLUDE_SENSITIVE_DATA=false` in production `.env`
  - [ ] Remove `ENABLE_DEBUG_CONSOLE=true` from production configuration
  - [ ] Ensure the default value in `config.py` remains `false` (already the case)
  - [ ] Document that sensitive data tracing should only be enabled in isolated development environments

- **References:** CWE-532 (Insertion of Sensitive Information into Log File), GDPR Article 5(1)(c) (Data Minimization)

---

### HIGH-06: CORS Configuration Allows Any Origin in Production

- **Location:** `/home/als0028/study/shintairiku/marketing-automation/backend/main.py` (lines 25-33)
- **Description:** The CORS middleware reads allowed origins from the `ALLOWED_ORIGINS` environment variable. While the default is `http://localhost:3000`, the configuration allows all HTTP methods and **all headers** (`allow_headers=["*"]`):

  ```python
  allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
  app.add_middleware(
      CORSMiddleware,
      allow_origins=allowed_origins,
      allow_credentials=True,
      allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
      allow_headers=["*"],  # Too permissive
  )
  ```

  Combined with `allow_credentials=True`, if the `ALLOWED_ORIGINS` is ever set to include `*` (or a broad wildcard), it would allow any website to make authenticated cross-origin requests to the backend, enabling CSRF-like attacks.

  The API proxy (`frontend/src/app/api/proxy/[...path]/route.ts`) also returns `Access-Control-Allow-Origin: *` in its responses.

- **Impact:** If CORS origins are misconfigured, any malicious website could make authenticated API calls on behalf of logged-in users.

- **Remediation Checklist:**
  - [ ] Restrict `allow_headers` to only the headers actually used: `["Content-Type", "Authorization", "Accept"]`
  - [ ] Add validation at startup that rejects `*` as an allowed origin when `allow_credentials=True`
  - [ ] Remove `Access-Control-Allow-Origin: *` from the API proxy response headers
  - [ ] Ensure the production `ALLOWED_ORIGINS` contains only the exact production frontend domain

- **References:** CWE-942 (Permissive Cross-domain Policy), OWASP CORS Misconfiguration

---

### HIGH-07: Potential SQL Injection via Supabase `.or_()` with User-Controlled Input

- **Location:** `/home/als0028/study/shintairiku/marketing-automation/backend/app/domains/image_generation/endpoints.py` (line 434)
- **Description:** The Supabase PostgREST `.or_()` method is called with an f-string that includes user-controlled input (`request.image_url`) directly:

  ```python
  image_result = supabase.table("images").select("*").eq("user_id", current_user_id).or_(
      f"gcs_url.eq.{request.image_url},file_path.like.%{request.image_url.split('/')[-1]}"
  ).execute()
  ```

  The `request.image_url` value is inserted directly into the PostgREST filter string without sanitization. While PostgREST filter syntax is not standard SQL and has limited injection surface compared to raw SQL, specially crafted URLs containing PostgREST filter operators (e.g., `,`, `.eq.`, `.or.`) could manipulate the query logic to bypass the `user_id` filter or access other users' data.

  Similarly, in `flow_service.py` (line 211):
  ```python
  query = query.or_(f"user_id.eq.{user_id},is_template.eq.true")
  ```
  While `user_id` comes from the authenticated token (trusted), this pattern sets a dangerous precedent.

- **Impact:** An attacker could craft a malicious `image_url` that manipulates the PostgREST filter, potentially accessing or modifying images belonging to other users.

- **Remediation Checklist:**
  - [ ] Use parameterized PostgREST filters instead of f-strings. Break the query into chained filter calls:
    ```python
    # Instead of .or_(f"gcs_url.eq.{request.image_url},...")
    # Use separate queries or validated input:
    filename = os.path.basename(urlparse(request.image_url).path)
    # Validate filename contains only safe characters
    if not re.match(r'^[\w.-]+$', filename):
        raise HTTPException(status_code=400, detail="Invalid image URL")

    images_by_url = supabase.table("images").select("*") \
        .eq("user_id", current_user_id) \
        .eq("gcs_url", request.image_url) \
        .execute()
    ```
  - [ ] Audit all `.or_()` usages with user-controlled input across the codebase
  - [ ] Sanitize/validate `request.image_url` before using it in any query

- **References:** CWE-89 (SQL Injection), CWE-943 (Improper Neutralization of Special Elements in Data Query Logic)

---

## Medium Vulnerabilities

### MED-01: Stored XSS via AI-Generated Content Rendered with `dangerouslySetInnerHTML`

- **Location:** Multiple frontend files (22+ instances):
  - `/home/als0028/study/shintairiku/marketing-automation/frontend/src/features/tools/seo/manage/list/display/indexPage.tsx` (line 473)
  - `/home/als0028/study/shintairiku/marketing-automation/frontend/src/features/tools/seo/generate/new-article/component/ContentGeneration.tsx` (line 159)
  - `/home/als0028/study/shintairiku/marketing-automation/frontend/src/features/tools/seo/generate/edit-article/EditArticlePage.tsx` (lines 1515, 1521, 2037, 2046, 2271)
  - Multiple other SEO article display components

- **Description:** AI-generated article content is rendered using React's `dangerouslySetInnerHTML` without sanitization:
  ```tsx
  dangerouslySetInnerHTML={{ __html: selectedArticle.content }}
  ```
  While the content is AI-generated (reducing the likelihood of malicious scripts), several attack vectors exist:
  1. AI prompt injection could cause the LLM to generate HTML with embedded `<script>` tags
  2. User-editable article content (via the rich text editor) could contain malicious HTML
  3. Content imported from external sources (SERP scraping, reference URLs) could contain XSS payloads

  The backend does have a `sanitize_dom` function (`backend/app/domains/seo_article/endpoints.py`), but it is not consistently applied before storage or rendering.

- **Impact:** Stored XSS could execute JavaScript in other users' browsers when viewing shared articles, potentially stealing session tokens or performing actions on their behalf.

- **Remediation Checklist:**
  - [ ] Implement a client-side HTML sanitization library (e.g., `dompurify`) for all `dangerouslySetInnerHTML` usages:
    ```tsx
    import DOMPurify from 'dompurify';

    <div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(article.content) }} />
    ```
  - [ ] Ensure the backend `sanitize_dom()` function is applied to all content before storing in the database
  - [ ] Add Content Security Policy (CSP) headers to prevent inline script execution (see MED-04)

- **References:** CWE-79 (Cross-site Scripting), OWASP XSS Prevention Cheat Sheet

---

### MED-02: No File Type Validation on Image Uploads

- **Location:** `/home/als0028/study/shintairiku/marketing-automation/backend/app/domains/blog/endpoints.py` (upload-image endpoint), `/home/als0028/study/shintairiku/marketing-automation/backend/app/domains/image_generation/endpoints.py` (upload endpoint)
- **Description:** Image upload endpoints accept files and process them with Pillow for WebP conversion, but do not validate:
  1. File MIME type against an allowlist
  2. File extension against an allowlist
  3. File size before reading into memory
  4. That the file is actually a valid image (though Pillow's `Image.open()` would fail on non-images)

  The `image_utils.py` WebP conversion function does call `Image.open()` which provides some implicit validation, but malformed image files can trigger Pillow vulnerabilities (e.g., decompression bombs).

- **Impact:** Potential denial of service via decompression bombs (huge images that consume excessive memory during processing), or exploitation of Pillow vulnerabilities with specially crafted image files.

- **Remediation Checklist:**
  - [ ] Add file size limits before processing (e.g., max 10MB):
    ```python
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 10MB)")
    ```
  - [ ] Validate file extension and MIME type against an allowlist (`['image/jpeg', 'image/png', 'image/gif', 'image/webp']`)
  - [ ] Set `Image.MAX_IMAGE_PIXELS` to prevent decompression bombs:
    ```python
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = 25_000_000  # ~5000x5000
    ```

- **References:** CWE-434 (Unrestricted Upload of File with Dangerous Type), CWE-400 (Uncontrolled Resource Consumption)

---

### MED-03: Secrets Baked into Docker Build Layer (Frontend)

- **Location:** `/home/als0028/study/shintairiku/marketing-automation/frontend/Dockerfile` (lines 25-31), `/home/als0028/study/shintairiku/marketing-automation/docker-compose.yml` (lines 39-42)
- **Description:** The frontend Dockerfile passes `STRIPE_SECRET_KEY` and `SUPABASE_SERVICE_ROLE_KEY` as build arguments for the production build:

  ```dockerfile
  ARG STRIPE_SECRET_KEY
  ARG SUPABASE_SERVICE_ROLE_KEY
  ENV STRIPE_SECRET_KEY=${STRIPE_SECRET_KEY}
  ENV SUPABASE_SERVICE_ROLE_KEY=${SUPABASE_SERVICE_ROLE_KEY}
  ```

  Build arguments are stored in the Docker image's layer history and can be extracted using `docker history --no-trunc`. Additionally, `ENV` makes them available as environment variables in the running container's `/proc/1/environ`.

  The `docker-compose.yml` also passes these secrets as build args.

- **Impact:** Anyone with access to the Docker image (e.g., from a container registry) can extract these secrets from the image layers.

- **Remediation Checklist:**
  - [ ] Use multi-stage builds where secrets are only available during the build stage and not copied to the production image:
    ```dockerfile
    FROM deps AS builder
    # Use --mount=type=secret for build-time secrets
    RUN --mount=type=secret,id=stripe_key \
        STRIPE_SECRET_KEY=$(cat /run/secrets/stripe_key) bun run build
    ```
  - [ ] Inject runtime secrets via environment variables at container start time (Cloud Run environment variables), not at build time
  - [ ] Remove `STRIPE_SECRET_KEY` and `SUPABASE_SERVICE_ROLE_KEY` from the Dockerfile `ARG` and `ENV` directives
  - [ ] Use `.dockerignore` to exclude `.env.local` from the build context

- **References:** CWE-312 (Cleartext Storage of Sensitive Information), Docker Security Best Practices

---

### MED-04: Missing Security Headers

- **Location:** `/home/als0028/study/shintairiku/marketing-automation/frontend/next.config.js`, `/home/als0028/study/shintairiku/marketing-automation/backend/main.py`
- **Description:** Neither the Next.js frontend nor the FastAPI backend sets standard security headers:
  - `Content-Security-Policy` (CSP) -- prevents XSS
  - `X-Content-Type-Options: nosniff` -- prevents MIME sniffing
  - `X-Frame-Options: DENY` or `SAMEORIGIN` -- prevents clickjacking
  - `Strict-Transport-Security` (HSTS) -- enforces HTTPS
  - `Referrer-Policy` -- controls referrer information leakage
  - `Permissions-Policy` -- restricts browser features

- **Impact:** Missing CSP allows XSS attacks to execute arbitrary scripts. Missing X-Frame-Options allows clickjacking. Missing HSTS allows downgrade attacks.

- **Remediation Checklist:**
  - [ ] Add security headers to `next.config.js`:
    ```javascript
    async headers() {
      return [{
        source: '/(.*)',
        headers: [
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
          { key: 'Strict-Transport-Security', value: 'max-age=31536000; includeSubDomains' },
        ],
      }];
    }
    ```
  - [ ] Add CSP headers (start with report-only mode to avoid breaking functionality)
  - [ ] Add `X-Content-Type-Options: nosniff` to FastAPI middleware

- **References:** OWASP Secure Headers Project, CWE-693 (Protection Mechanism Failure)

---

### MED-05: Unpinned Dependencies Allow Supply Chain Attacks

- **Location:** `/home/als0028/study/shintairiku/marketing-automation/backend/pyproject.toml` (lines 7-31)
- **Description:** All backend Python dependencies are specified without version constraints:

  ```toml
  dependencies = [
      "fastapi",
      "uvicorn[standard]",
      "openai",
      "openai-agents",
      "supabase",
      "pillow",
      "numpy",
      "httpx",
      # ... all without version pins
  ]
  ```

  While `uv.lock` provides reproducible builds (when used correctly), the `pyproject.toml` without version constraints means:
  1. A `uv sync` without `--frozen` could pull in a compromised newer version
  2. If `uv.lock` is regenerated, any dependency could be updated to a malicious version
  3. No CI step verifies dependency integrity

  The frontend `package.json` uses caret versions (`^`), which is better but still allows minor/patch updates.

- **Impact:** A supply chain attack on any dependency could inject malicious code into the application.

- **Remediation Checklist:**
  - [ ] Add minimum version constraints to `pyproject.toml` (e.g., `"fastapi>=0.128.0"`)
  - [ ] Always use `uv sync --frozen` in CI/CD and production builds
  - [ ] Add a dependency audit step to the CI pipeline (e.g., `pip-audit` for Python, `bun audit` for JavaScript)
  - [ ] Consider using a tool like `safety` or `pip-audit` in the CI workflow
  - [ ] Add Dependabot or Renovate bot for automated dependency update PRs with review

- **References:** CWE-1104 (Use of Unmaintained Third-Party Components), OWASP Supply Chain Security

---

### MED-06: No CI/CD Security Scanning

- **Location:** `/home/als0028/study/shintairiku/marketing-automation/.github/workflows/backend-docker-build.yml`
- **Description:** The only CI/CD pipeline is a Docker build test. There is no:
  - Static Application Security Testing (SAST)
  - Dependency vulnerability scanning
  - Secret detection in commits
  - Container image scanning
  - Frontend security testing
  - Linting for security issues (e.g., `bandit` for Python, `eslint-plugin-security` for JS)

- **Impact:** Security regressions and known vulnerability introductions go undetected until manual review.

- **Remediation Checklist:**
  - [ ] Add `pip-audit` or `safety check` to the CI pipeline for Python dependency scanning
  - [ ] Add `trivy` or `snyk container` for Docker image scanning
  - [ ] Add `bandit` for Python SAST
  - [ ] Add `gitleaks` or `trufflehog` for secret detection in commits
  - [ ] Add `eslint-plugin-security` to the frontend ESLint configuration
  - [ ] Run `bun audit` in the frontend CI step

- **References:** OWASP DevSecOps Guidelines, CWE-1395

---

### MED-07: Error Responses Leak Internal Details

- **Location:** `/home/als0028/study/shintairiku/marketing-automation/backend/app/core/exceptions.py` (lines 39-48, 54-56), `/home/als0028/study/shintairiku/marketing-automation/backend/app/common/auth.py` (line 188)
- **Description:** Several error handlers include exception details in the response body:

  ```python
  # exceptions.py line 41
  detail = f"Agent processing error: {type(exc).__name__} - {str(exc)}"

  # exceptions.py line 55
  content={"detail": f"An unexpected internal server error occurred: {type(exc).__name__}"},

  # auth.py line 188
  raise HTTPException(status_code=500, detail=f"Authentication error: {e}")
  ```

  These expose internal exception class names and error messages that could reveal implementation details (library versions, file paths, database schema information) to attackers.

- **Impact:** Information disclosure that aids attackers in crafting targeted exploits.

- **Remediation Checklist:**
  - [ ] Return generic error messages in production:
    ```python
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {type(exc).__name__} - {str(exc)}")
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred"},
        )
    ```
  - [ ] Only include detailed error information when `DEBUG=true` (but fix CRIT-02 first)
  - [ ] Log full exception details server-side but return only sanitized messages to clients

- **References:** CWE-209 (Generation of Error Message Containing Sensitive Information)

---

### MED-08: Invitation Token Security Weaknesses

- **Location:** `/home/als0028/study/shintairiku/marketing-automation/backend/app/domains/organization/service.py`
- **Description:** Organization invitation tokens are used to accept or decline invitations. While invitations have an `expires_at` field, the invitation flow uses email-based matching which has several concerns:
  1. Invitation tokens are passed as query parameters in URLs, which can be logged in browser history and server logs
  2. There is no brute-force protection on the invitation response endpoint (`POST /organizations/invitations/respond`)
  3. The invitation acceptance only checks the token value, not a cryptographic binding to the invited user's identity

- **Impact:** An attacker who obtains or guesses an invitation token could join an organization, gaining access to the organization's WordPress sites, article generation quota, and shared data.

- **Remediation Checklist:**
  - [ ] Ensure invitation tokens are cryptographically random with sufficient entropy (at least 256 bits)
  - [ ] Add rate limiting on the invitation response endpoint
  - [ ] Verify that the accepting user's email matches the invited email
  - [ ] Consider using HMAC-signed invitation tokens to prevent tampering

- **References:** CWE-640 (Weak Password Recovery Mechanism for Forgotten Password), OWASP Session Management

---

## Low Vulnerabilities

### LOW-01: Excessive Logging of Authentication Details

- **Location:** `/home/als0028/study/shintairiku/marketing-automation/backend/app/common/auth.py` (lines 173-176), `/home/als0028/study/shintairiku/marketing-automation/backend/app/common/admin_auth.py` (lines 137-139)
- **Description:** Successful authentication logs include JWT claim details:
  ```python
  logger.info(f"🔒 [AUTH] JWT claims: iss={decoded.get('iss')}, azp={decoded.get('azp')}, exp={decoded.get('exp')}")
  logger.info(f"🔒 [AUTH] Decoded JWT token keys: {list(decoded_token.keys())}")
  ```
  In high-traffic production, this generates excessive log volume and may include sensitive JWT metadata.

- **Remediation Checklist:**
  - [ ] Reduce authentication success logging to DEBUG level
  - [ ] Remove logging of JWT claim details in production
  - [ ] Only log authentication failures at INFO/WARNING level

- **References:** CWE-532, OWASP Logging Cheat Sheet

---

### LOW-02: Hardcoded Absolute Path in Configuration

- **Location:** `/home/als0028/study/shintairiku/marketing-automation/backend/app/core/config.py` (line 132)
- **Description:** The Pydantic settings configuration includes a hardcoded absolute path:
  ```python
  model_config = SettingsConfigDict(
      env_file=[
          '.env',
          Path(__file__).parent.parent.parent / '.env',
          '/home/als0028/study/shintairiku/marketing-automation/backend/.env'  # Hardcoded
      ],
  ```
  This path is developer-specific and would not work in other environments.

- **Remediation Checklist:**
  - [ ] Remove the hardcoded absolute path from the `env_file` list
  - [ ] Use only relative paths for `.env` file discovery

- **References:** CWE-668 (Exposure of Resource to Wrong Sphere)

---

### LOW-03: Docker Container Runs as Root (Backend)

- **Location:** `/home/als0028/study/shintairiku/marketing-automation/backend/Dockerfile`
- **Description:** The backend Dockerfile does not specify a non-root user. The application runs as `root` inside the container, which means any code execution vulnerability could lead to container escape or host compromise.

  The frontend production Dockerfile correctly uses `USER node` (line 65).

- **Remediation Checklist:**
  - [ ] Add a non-root user to the backend Dockerfile:
    ```dockerfile
    RUN adduser --disabled-password --gecos '' appuser
    USER appuser
    ```
  - [ ] Ensure the image storage path is writable by the non-root user

- **References:** CWE-250 (Execution with Unnecessary Privileges), Docker Security Best Practices

---

### LOW-04: OpenAI API Key Partially Logged at Startup

- **Location:** `/home/als0028/study/shintairiku/marketing-automation/backend/app/core/config.py` (line 174)
- **Description:** The OpenAI API key's first 8 characters are logged at startup:
  ```python
  print(f"OpenAI API キーを設定しました: {settings.openai_api_key[:8]}...")
  ```
  While only a prefix, this information could be useful for targeted attacks on OpenAI's API key format.

- **Remediation Checklist:**
  - [ ] Remove API key prefix logging or replace with a masked indicator: `print("OpenAI API key configured: [set]")`

- **References:** CWE-532 (Insertion of Sensitive Information into Log File)

---

### LOW-05: GCS Service Account JSON File Referenced by Name in `.gitignore`

- **Location:** `/home/als0028/study/shintairiku/marketing-automation/.gitignore` (lines 47-49)
- **Description:** The `.gitignore` file lists specific service account filenames:
  ```
  marketing-automation-461305-f94de589a90c.json
  marketing-automation-461305-d3821e14ba9f.json
  backend/marketing-automation-461305-f4cb0b7367b7.json
  ```
  This reveals the GCP project name (`marketing-automation-461305`) and confirms that service account JSON files are used locally. A more robust approach would use a pattern-based exclusion.

- **Remediation Checklist:**
  - [ ] Replace specific filenames with a pattern: `*-service-account*.json` or `*.json` in the project root
  - [ ] Consider using a nested `.gitignore` in the backend directory for sensitive file patterns

- **References:** CWE-200 (Exposure of Sensitive Information)

---

### LOW-06: Health Check Endpoint Exposes Version Information

- **Location:** `/home/als0028/study/shintairiku/marketing-automation/backend/main.py` (lines 52-54)
- **Description:** The health check endpoint returns the application version:
  ```python
  @app.get("/health")
  async def health_check():
      return {"status": "healthy", "message": "API is running", "version": "2.0.0"}
  ```

- **Remediation Checklist:**
  - [ ] Remove the `version` field from the health check response, or make it configurable
  - [ ] Health checks should return minimal information (just `{"status": "ok"}`)

- **References:** CWE-200 (Exposure of Sensitive Information)

---

## General Security Recommendations

- [ ] **Implement a Web Application Firewall (WAF):** Deploy Google Cloud Armor or Cloudflare in front of the Cloud Run services to filter malicious traffic, apply geo-blocking if the service is Japan-only, and rate-limit requests at the edge
- [ ] **Enable Cloud Run authentication:** Consider requiring IAM-based authentication for the backend Cloud Run service, with the frontend acting as the sole authenticated caller via a service account. This eliminates direct public access to the backend API
- [ ] **Implement Content Security Policy (CSP):** Add CSP headers to prevent inline script execution, mitigating stored XSS risks from AI-generated content
- [ ] **Add request ID tracking:** Generate a unique request ID for each API call and include it in logs and error responses for correlation and debugging without exposing internal details
- [ ] **Implement an API gateway:** Use an API gateway (e.g., Google Cloud API Gateway or Apigee) in front of the backend to centralize authentication, rate limiting, and request validation
- [ ] **Regular secret rotation:** Establish a process for rotating API keys and credentials quarterly, with automated rotation where possible (e.g., Stripe webhook secrets)
- [ ] **Add CSRF protection:** While Clerk handles auth tokens via headers (not cookies), the Stripe webhook and Clerk webhook endpoints should verify that requests originate from expected sources (already done via signature verification, but add IP allowlisting as an additional layer)

---

## Security Posture Improvement Plan

### Immediate (Week 1)
1. Rotate all exposed secrets (CRIT-01)
2. Remove DEBUG mode authentication bypass (CRIT-02)
3. Add authentication to unauthenticated endpoints (CRIT-03)
4. Implement SSRF protection on WordPress URL endpoint (CRIT-04)

### Short-term (Weeks 2-4)
5. Add rate limiting to expensive operations (HIGH-02)
6. Fix CORS configuration (HIGH-06)
7. Fix PostgREST injection vulnerability (HIGH-07)
8. Add JWT issuer/audience validation (HIGH-04)
9. Disable sensitive data tracing in production (HIGH-05)
10. Add security headers (MED-04)

### Medium-term (Months 2-3)
11. Implement HTML sanitization for AI-generated content (MED-01)
12. Add file upload validation (MED-02)
13. Fix Docker secret handling (MED-03)
14. Add CI/CD security scanning (MED-06)
15. Pin dependency versions (MED-05)
16. Implement request-scoped Supabase clients with RLS (HIGH-03)
17. Add path restrictions to API proxy (HIGH-01)

### Ongoing
18. Regular dependency updates and vulnerability scanning
19. Periodic security audits
20. Security awareness training for developers
21. Incident response planning and documentation

---

*Report generated by Claude Opus 4.6 security audit. This report should be reviewed by a human security professional before implementing remediation steps. Some findings may require additional investigation in the production environment.*
