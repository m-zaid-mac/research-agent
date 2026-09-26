import boto3
from botocore.config import Config
from langchain_aws import ChatBedrock

REGION = "us-east-1"
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

# botocore's default read_timeout is 60s. The synthesize step sends four
# sub-questions' worth of search results and asks for up to 4096 tokens back,
# which routinely runs past that. The timeout isn't a Bedrock limit, it's the
# HTTP client giving up while the model is still generating.
BEDROCK_CONFIG = Config(
    connect_timeout=10,
    read_timeout=300,
    retries={"max_attempts": 3, "mode": "adaptive"},
)


def get_llm():
    client = boto3.client(
        "bedrock-runtime",
        region_name=REGION,
        config=BEDROCK_CONFIG,
    )
    return ChatBedrock(
        client=client,
        model_id=MODEL_ID,
        region_name=REGION,
        model_kwargs={"max_tokens": 4096},
    )
