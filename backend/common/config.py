"""API keys: env var for local runs, SSM Parameter Store (SecureString) on AWS."""
import os

_cache = {}


def _secret(env_name, ssm_env_name):
    value = os.getenv(env_name)
    if value:
        return value
    path = os.getenv(ssm_env_name)
    if not path:
        raise RuntimeError(f"Set {env_name} (local) or {ssm_env_name} (AWS)")
    if path not in _cache:
        import boto3
        resp = boto3.client("ssm").get_parameter(Name=path, WithDecryption=True)
        _cache[path] = resp["Parameter"]["Value"]
    return _cache[path]


def owm_key():
    return _secret("OPENWEATHER_API_KEY", "OWM_KEY_PARAM")


def openaq_key():
    return _secret("OPENAQ_API_KEY", "OPENAQ_KEY_PARAM")
