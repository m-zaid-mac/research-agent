import boto3
from langchain_aws import ChatBedrock

def get_llm():
    return ChatBedrock(
        model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        region_name="us-east-1",
        model_kwargs={"max_tokens": 4096}
    )