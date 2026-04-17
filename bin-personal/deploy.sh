#!/usr/bin/env bash
set -e

echo "================================================="
echo "🚀 Personal Direct AWS Deployment Pipeline"
echo "================================================="

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
INFRA_DIR="$ROOT_DIR/infra-personal"
FRONTEND_DIR="$ROOT_DIR/frontend"

# 1. Build Backend Package
echo "INFO: Packaging FastAPI Serverless Backend..."
cd "$BACKEND_DIR"
rm -rf .package "$INFRA_DIR/backend.zip"
mkdir -p .package

# Leverage manylinux boundaries to ensure AWS Lambda natively parses psycopg and core compiled binaries
echo "INFO: Fetching dependencies (this might take a moment)..."
pip install -r requirements.txt -t .package/ --platform manylinux2014_x86_64 --only-binary=:all: >/dev/null 2>&1 || pip install -r requirements.txt -t .package/ >/dev/null 2>&1

echo "INFO: Bundling function code natively..."
# Using explicit copy mapping to preserve structure ignoring .venv
cp -r *.py auth-service employees-service reviews-service goals-service competencies-service training-service development-service analytics-service .package/

cd .package
zip -q -r "$INFRA_DIR/backend.zip" .
cd ..
rm -rf .package
echo "INFO: Backend packaged successfully at $INFRA_DIR/backend.zip"

# 2. Deploy Infrastructure
echo ""
echo "INFO: Initializing and Applying Terraform natively into your mapped AWS account..."
cd "$INFRA_DIR"
terraform init
terraform apply -auto-approve

# 3. Extract Outputs dynamically
API_URL=$(terraform output -raw api_url | tr -d '\r\n ' | sed 's/\/$//')
CLOUDFRONT_DOMAIN=$(terraform output -raw cloudfront_domain | tr -d '\r\n ')
S3_BUCKET=$(terraform output -raw s3_bucket | tr -d '\r\n ')
DB_ADDRESS=$(terraform output -raw db_address | tr -d '\r\n ')

echo ""
echo "================================================="
echo "✅ Backend Infrastructure Deployed!"
echo "📡 API URL: $API_URL"
echo "🌐 CloudFront Domain: https://$CLOUDFRONT_DOMAIN"
echo "🗄️ PostgreSQL Master Address: $DB_ADDRESS"
echo "================================================="

# 4. Build and Deploy Frontend
echo ""
echo "INFO: Compiling React Frontend with deployed API routing..."
cd "$FRONTEND_DIR"

# Ensure environment is injected securely for Vite static generation
echo "VITE_API_URL=$API_URL" > .env.production
echo "VITE_API_URL=$API_URL" > .env.local

npm install
npm run build

echo "INFO: Syncing static React compilation securely to S3 bucket ($S3_BUCKET)..."
# Using an aggressive sync with deletion to ensure no stale artifacts are served
aws s3 rm "s3://$S3_BUCKET/" --recursive >/dev/null
aws s3 sync dist/ "s3://$S3_BUCKET/" >/dev/null

echo ""
echo "================================================="
echo "🎉 DEPLOYMENT COMPLETELY FINISHED!"
echo "Access your live platform here: https://$CLOUDFRONT_DOMAIN"
echo "================================================="
