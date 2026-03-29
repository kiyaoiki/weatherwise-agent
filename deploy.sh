#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
#  WeatherWise Agent — Google Cloud Run Deployment Script
# ══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

# ── Config (edit these or export before running) ──────────────────────────────
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-your-gcp-project-id}"
REGION="${GOOGLE_CLOUD_REGION:-us-central1}"
SERVICE_NAME="weatherwise-agent"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
GOOGLE_API_KEY="${GOOGLE_API_KEY:-}"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║        WeatherWise Agent — Cloud Run Deploy      ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "  Project : ${PROJECT_ID}"
echo "  Region  : ${REGION}"
echo "  Service : ${SERVICE_NAME}"
echo "  Image   : ${IMAGE_NAME}"
echo ""

if [[ -z "${GOOGLE_API_KEY}" ]]; then
  echo "❌  GOOGLE_API_KEY is not set. Export it first:"
  echo "    export GOOGLE_API_KEY=your-key"
  exit 1
fi

# ── 1. Authenticate & set project ─────────────────────────────────────────────
echo "▶ Step 1/5 — Authenticating with Google Cloud..."
gcloud config set project "${PROJECT_ID}"

# ── 2. Enable required APIs ────────────────────────────────────────────────────
echo "▶ Step 2/5 — Enabling Cloud APIs..."
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  containerregistry.googleapis.com \
  --quiet

# ── 3. Build & push Docker image ──────────────────────────────────────────────
echo "▶ Step 3/5 — Building Docker image via Cloud Build..."
gcloud builds submit \
  --tag "${IMAGE_NAME}" \
  --project "${PROJECT_ID}" \
  .

# ── 4. Deploy to Cloud Run ─────────────────────────────────────────────────────
echo "▶ Step 4/5 — Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE_NAME}" \
  --platform managed \
  --region "${REGION}" \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10 \
  --timeout 120 \
  --set-env-vars "GOOGLE_API_KEY=${GOOGLE_API_KEY}" \
  --quiet

# ── 5. Print service URL ───────────────────────────────────────────────────────
echo "▶ Step 5/5 — Fetching service URL..."
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
  --platform managed \
  --region "${REGION}" \
  --format "value(status.url)")

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║              ✅  Deployment Complete!            ║"
echo "╠══════════════════════════════════════════════════╣"
echo "║  URL: ${SERVICE_URL}"
echo "║"
echo "║  Test it:"
echo "║  curl -X POST ${SERVICE_URL}/api/weather \\"
echo "║    -H 'Content-Type: application/json' \\"
echo "║    -d '{\"city\":\"Bengaluru\"}'"
echo "╚══════════════════════════════════════════════════╝"
echo ""
