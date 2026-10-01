# Sharing CrisisMesh via Cloudflare Quick Tunnels

This document outlines how to spin up a public, end-to-end demo link for CrisisMesh without requiring a Cloudflare account or exposing manual port forwards, using Cloudflare Quick Tunnels (`cloudflared`).

---

## Prerequisites

1. **Install Cloudflare Tunnel CLI**:
   ```powershell
   winget install --id Cloudflare.cloudflared
   ```
   Verify installation:
   ```powershell
   cloudflared --version
   ```

2. **Dependencies**:
   - Python 3.10+ / FastAPI backend
   - Node.js 18+ / Next.js frontend

---

## One-Command Startup

To run the automated tunnel generation script on Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/share.ps1
```

### What `scripts/share.ps1` Does:

1. **Starts Backend Service**:
   - Sets environment variables: `CRISISMESH_DEMO_MODE=true`, `LLM_MODE=mock`.
   - Starts FastAPI on `http://0.0.0.0:8000`.
2. **Launches Backend Quick Tunnel**:
   - Spawns `cloudflared tunnel --url http://localhost:8000`.
   - Extracts backend public HTTPS URL (e.g., `https://*.trycloudflare.com`) and WSS endpoint (`wss://*/ws`).
3. **Builds & Launches Frontend Service**:
   - Bakes `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_WS_URL` into the Next.js production build (`npm run build`).
   - Runs `npm run start` on port `3000`.
4. **Launches Frontend Quick Tunnel**:
   - Spawns `cloudflared tunnel --url http://localhost:3000`.
   - Extracts public HTTPS URL.
5. **Configures CORS & Security Headers**:
   - Injects allowed CORS origins and CSP connect-src directives dynamically for both tunnels and WebSocket connections.
6. **Performs Health Checks**:
   - Verifies `GET /health`.
   - Verifies frontend HTTP accessibility.
   - Verifies `POST /auth/demo-login` and WebSocket connectivity.
7. **Prints Public Link & Maintains Session**:
   - Keeps tunnels and background processes alive until interrupted (`Ctrl+C`).

---

## Verification

To verify the public URL end-to-end with automated headless browser tests:

```powershell
python scripts/verify_public_share.py
```
