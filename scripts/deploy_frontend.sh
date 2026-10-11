#!/usr/bin/env bash
# Writes frontend/config.js from the stack outputs, uploads the site, invalidates CloudFront.
# Usage: scripts/deploy_frontend.sh [stack-name]   (default: saansalert)
set -euo pipefail
STACK="${1:-saansalert}"
out() { aws cloudformation describe-stacks --stack-name "$STACK" \
        --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }
API="$(out ApiUrl)"; BUCKET="$(out SiteBucketName)"; DIST="$(out DistributionId)"
printf 'window.CONFIG = { API_URL: "%s" };\n' "$API" > frontend/config.js
aws s3 sync frontend/ "s3://$BUCKET/" --delete
aws cloudfront create-invalidation --distribution-id "$DIST" --paths "/*" >/dev/null
echo "Site: $(out SiteUrl)"
