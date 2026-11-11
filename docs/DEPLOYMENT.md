# Deploying AAROH

## What you need to provide

| Item | Needed for | Where it goes |
|---|---|---|
| A Linux server with Docker (any VPS: Hetzner, DigitalOcean, Lightsail, Oracle free tier; 1 vCPU / 1-2 GB RAM is enough) | Hosting | SSH access |
| A domain or subdomain pointing at the server (A record) | HTTPS, Android app | `.env` → `DOMAIN` |
| `SECRET_KEY`, `ENCRYPTION_KEY`, `POSTGRES_PASSWORD` | Security | `backend/.env`, `.env` |
| An LLM API key (optional): Anthropic, OpenAI, Groq, OpenRouter, or a local Ollama | Aaroh AI | `backend/.env` or per user in Settings → AI |
| A GitHub repository (optional) | CI and building the APK with GitHub Actions | push this folder |

## 0. Free hosting (Render + Neon, no server to manage)

Costs nothing. You need a GitHub login, a free [Neon](https://neon.tech) account (database) and a free [Render](https://render.com) account (app). Both let you sign up with GitHub.

1. **Database:** in Neon, create a project (region: Singapore or Mumbai if offered). Copy the connection string from the dashboard (it starts with `postgresql://` and ends with `?sslmode=require`).
2. **App:** open https://render.com/deploy?repo=https://github.com/tejaspatil2295/Aaroh. Render reads `render.yaml` and asks for `DATABASE_URL`: paste the Neon string, then click **Deploy**. The first build takes about 5-10 minutes.
3. Open the address Render shows (`https://aaroh-xxxx.onrender.com`) and register your own account. A demo account `demo@aaroh.app` / `Aaroh@2026` is created too; set `SEED_DEMO=false` in Render to skip it.

What the free tier means in practice:
- The app sleeps after 15 minutes without visits; the next visit takes about a minute to wake it.
- Neon's free database holds 0.5 GB, which is years of personal data. Journal photos are stored in the database on this setup (`UPLOAD_STORAGE=database`) because free Render instances have no permanent disk.
- Every push to `main` redeploys automatically.

This uses the root `Dockerfile`, which builds the web app and serves it from the API, so web and API share one HTTPS address.

## 1. Server (Docker Compose)

```bash
git clone <your-repo> aaroh && cd aaroh
cp .env.example .env                 # set POSTGRES_PASSWORD and DOMAIN
cp backend/.env.example backend/.env # set SECRET_KEY, ENCRYPTION_KEY, CORS_ORIGINS, AI_* (optional)
python3 -c "import secrets;print(secrets.token_urlsafe(64))"   # run twice for the two keys

docker compose --profile https up -d --build     # db, api, web, backup + Caddy with automatic HTTPS
docker compose exec api python -m app.seed       # optional: demo account demo@aaroh.app / Aaroh@2026
```

- Without a domain (local or LAN testing): `docker compose up -d --build`, then open `http://localhost:8080`. Set `COOKIE_SECURE=false` in `backend/.env` for plain HTTP.
- `CORS_ORIGINS` must include your web origin (`https://your-domain`) and the Android origins `https://localhost,capacitor://localhost`.
- Database migrations run automatically when the `api` container starts (`alembic upgrade head`).
- Backups: daily gzip'd dumps in `./backups` (14 days). Restore:
  `gunzip -c backups/aaroh-<stamp>.sql.gz | docker compose exec -T db psql -U aaroh aaroh`
- Updating: `git pull && docker compose --profile https up -d --build`.

## 2. Android APK

The Android app is the same React build packaged with Capacitor. It needs to know your server address; you can also type it on the login screen.

### Option A: GitHub Actions (no local Android tooling)

1. Push this folder to a GitHub repository.
2. Repository → Settings → Variables → add `AAROH_API_URL = https://your-domain`.
3. Actions → **CI** → *Run workflow* (or push a commit). The `android-apk` job uploads **aaroh-apk** as an artifact containing `app-debug.apk`.
4. Optional signed release build: add secrets `ANDROID_KEYSTORE_BASE64`, `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`, `ANDROID_KEY_PASSWORD`. Create a keystore with
   `keytool -genkey -v -keystore aaroh.keystore -alias aaroh -keyalg RSA -keysize 2048 -validity 10000` and `base64 -w0 aaroh.keystore`.

### Option B: locally

Requirements: Node 22, JDK 21, Android SDK (Android Studio installs it).

```bash
cd web
npm ci
VITE_API_URL=https://your-domain npm run build
npx cap sync android
cd android && ./gradlew assembleDebug
# APK: web/android/app/build/outputs/apk/debug/app-debug.apk
```

Install on the phone: copy the APK over and open it (allow "Install unknown apps"), or `adb install app-debug.apk`.

The Android WebView blocks plain-HTTP API calls from the app's HTTPS origin, so the server must be on HTTPS. For LAN testing without a certificate, a tunnel such as `cloudflared tunnel --url http://localhost:8080` gives a temporary HTTPS address.

## 3. Web app

Served by the `web` container (nginx) together with `/api`. It is a responsive PWA-style site and works on phone browsers too.

## 4. AI provider

Server-wide (all users): set in `backend/.env`

```
AI_PROVIDER=anthropic          # or openai_compatible
ANTHROPIC_API_KEY=sk-ant-...
AI_MODEL=claude-opus-5-5       # optional
```

For OpenAI-compatible providers set `AI_BASE_URL` (e.g. `https://api.openai.com/v1`, `https://api.groq.com/openai/v1`, `http://host.docker.internal:11434/v1` for Ollama) and `OPENAI_API_KEY`.

Per user: Settings → AI provider lets each user paste their own key; it is stored encrypted and never returned by the API.

Without any key the app runs in **offline mode**: summaries are rule-based and labelled as such.
