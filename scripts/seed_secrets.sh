#!/usr/bin/env bash
# One-time: store API keys as SecureString parameters. Reads keys from your .env, never prints them.
set -euo pipefail
set -a; source .env; set +a
aws ssm put-parameter --name /saansalert/openweather_key --type SecureString --overwrite --value "$OPENWEATHER_API_KEY" >/dev/null
aws ssm put-parameter --name /saansalert/openaq_key      --type SecureString --overwrite --value "$OPENAQ_API_KEY" >/dev/null
echo "Stored /saansalert/openweather_key and /saansalert/openaq_key"
