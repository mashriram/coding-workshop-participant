#!/usr/bin/env bash
# Script: Backend Infrastructure Deployment
# Purpose: Deploy backend infrastructure for the coding workshop
# Usage: ./deploy-backend.sh [aws|local]
# Default: aws

set -e

# Usage helper
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    echo "Usage: $0 [aws|local]"
    echo "Deploy backend infrastructure for the coding workshop"
    echo ""
    echo "Arguments:"
    echo "  aws             Deploy to AWS (default)"
    echo "  local           Deploy to LocalStack for development"
    echo ""
    echo "Options:"
    echo "  -h, --help      Show this help message"
    echo ""
    echo "Requirements:"
    echo "  - terraform installed"
    echo "  - ENVIRONMENT.config file (auto-created for AWS)"
    echo ""
    echo "Examples:"
    echo "  $0              # Deploy to AWS"
    echo "  $0 aws          # Deploy to AWS"
    echo "  $0 local        # Deploy to LocalStack"
    exit 0
fi

echo "===================================="
echo "Coding Workshop - Backend Deployment"
echo "===================================="
echo ""

# Set up PATH and AWS region
export PATH="$HOME/.local/bin:$PATH"
export AWS_REGION=${AWS_REGION:-us-east-1}

# Verify required dependencies
terraform --version > /dev/null 2>&1 || { echo "ERROR: 'terraform' is missing. Aborting..."; exit 1; }

# Resolve script directory and project root paths
SCRIPT_DIR="$(cd "$(dirname "$0")" > /dev/null 2>&1 || exit 1; pwd -P)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." > /dev/null 2>&1 || exit 1; pwd -P)"

# Define configuration file paths
ENVIRONMENT_CONFIG="$PROJECT_ROOT/ENVIRONMENT.config"
INFRA_DIR="$PROJECT_ROOT/infra"
ENVIRONMENT=${1:-"aws"}

echo "INFO: Deploying infrastructure..."
echo "INFO: Environment - $ENVIRONMENT"

# Change to infrastructure directory
cd "$INFRA_DIR"

# AWS Deployment Configuration
if [ "$ENVIRONMENT" = "aws" ]; then
    echo "INFO: Using AWS deployment (terraform)..."

    # Setup participant if config is missing
    "$SCRIPT_DIR/setup-participant.sh"

    # Load participant-specific configuration if available
    if [ -f "$ENVIRONMENT_CONFIG" ]; then
        echo "INFO: Loading participant environment configuration..."
        source "$ENVIRONMENT_CONFIG"
    else
        echo "WARNING: $ENVIRONMENT_CONFIG is missing"
    fi
else
    # Local development configuration — override credentials for LocalStack
    export AWS_ENDPOINT_URL="http://127.0.0.1:4566"
    export AWS_ENDPOINT_URL_S3="http://127.0.0.1:4566"
    export AWS_SQS_PROTOCOL=query
    export AWS_ACCESS_KEY_ID=test
    export AWS_SECRET_ACCESS_KEY=test
    export AWS_REGION=us-east-1
    export AWS_DEFAULT_REGION=us-east-1
    unset AWS_SESSION_TOKEN

    # Ensure both possible tfstate bucket names exist for LocalStack
    for BUCKET_NAME in "coding-workshop-tfstate-${PARTICIPANT_ID:-abcd1234}" "coding-workshop-us-east-1-${PARTICIPANT_ID:-abcd1234}"; do
        if ! aws --endpoint-url=http://127.0.0.1:4566 s3 ls | grep -q "$BUCKET_NAME"; then
            aws --endpoint-url=http://127.0.0.1:4566 s3 mb "s3://$BUCKET_NAME"
        fi
    done
    # Wait for LocalStack to be ready (45 second sleep for stability)
    echo -n "INFO: Waiting for LocalStack (45s)..."
    sleep 45
    echo " ✓"
    READY=true
fi

# Initialize Terraform with backend configuration
if [ "$ENVIRONMENT" = "local" ]; then
    echo "INFO: Initializing with LocalStack backend configuration..."
    rm -rf .terraform .terraform.lock.hcl
    terraform init -reconfigure -upgrade -lock=false \
        -backend-config="bucket=coding-workshop-tfstate-${PARTICIPANT_ID:-abcd1234}" \
        -backend-config="region=${AWS_REGION:-us-east-1}" \
        -backend-config="endpoints={s3=\"http://127.0.0.1:4566\",sts=\"http://127.0.0.1:4566\",iam=\"http://127.0.0.1:4566\"}" \
        -backend-config="skip_credentials_validation=true" \
        -backend-config="skip_metadata_api_check=true" \
        -backend-config="skip_region_validation=true" \
        -backend-config="use_path_style=true"
elif [ -n "$PARTICIPANT_ID" ]; then
    echo "INFO: Using custom backend configuration..."
    rm -rf .terraform .terraform.lock.hcl
    terraform init -reconfigure -upgrade -backend-config="bucket=coding-workshop-tfstate-${PARTICIPANT_ID:-abcd1234}" -backend-config="region=${AWS_REGION:-us-east-1}"
else
    echo "WARNING: No backend.config found. Using default backend configuration."
    echo "INFO: For multi-participant workshops, run: ./bin/setup-participant.sh"
    rm -rf .terraform .terraform.lock.hcl
    terraform init -reconfigure -upgrade
fi

if [ "$ENVIRONMENT" != "local" ] && [ -n "$PARTICIPANT_ID" ]; then
    echo "INFO: Scrubbing orphaned monolithic modules from strict state tracking..."
    terraform state rm 'aws_sqs_queue.this' 'module.lambda' >/dev/null 2>&1 || true
fi

# Apply Terraform configuration automatically
terraform apply -auto-approve -lock=false
echo "INFO: Infrastructure deployment complete!"

# Display API endpoint
if [ -n "$API_BASE_URL" ]; then
    echo ""
    echo "API Base URL: $API_BASE_URL"
fi
if [ -n "$API_ENDPOINTS" ]; then
    echo ""
    echo "API Endpoints: $API_ENDPOINTS"
fi
