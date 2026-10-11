"""One SNS topic per area; email subscriptions carry a filter policy on profile + language."""
import json
import os


def _sns():
    import boto3
    return boto3.client("sns")


def topic_name(area_id):
    return f"{os.environ.get('TOPIC_PREFIX', 'saansalert')}-{area_id}"


def ensure_topic(area_id):
    return _sns().create_topic(Name=topic_name(area_id))["TopicArn"]   # idempotent


def subscribe(email, area_id, profile, lang):
    sns = _sns()
    arn = ensure_topic(area_id)
    sns.subscribe(TopicArn=arn, Protocol="email", Endpoint=email, ReturnSubscriptionArn=True,
                  Attributes={"FilterPolicy": json.dumps({"profile": [profile], "lang": [lang]}),
                              "FilterPolicyScope": "MessageAttributes"})


def publish_all(area_id, messages):
    sns = _sns()
    arn = ensure_topic(area_id)
    for m in messages:
        sns.publish(TopicArn=arn, Subject=m["subject"], Message=m["body"], MessageAttributes={
            "profile": {"DataType": "String", "StringValue": m["profile"]},
            "lang": {"DataType": "String", "StringValue": m["lang"]}})
