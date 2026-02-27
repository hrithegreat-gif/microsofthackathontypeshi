# config.py
from openai import AsyncAzureOpenAI
from azure.cosmos import CosmosClient
from azure.servicebus.aio import ServiceBusClient
from dotenv import load_dotenv
import os

load_dotenv()   # Reads your .env file

# ─── Azure OpenAI client ───────────────────────────────────────────────────────
openai_client = AsyncAzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION")
)

# ─── Cosmos DB client ──────────────────────────────────────────────────────────
cosmos_client = CosmosClient(
    os.getenv("COSMOS_ENDPOINT"),
    credential=os.getenv("COSMOS_KEY")
)
cosmos_db = cosmos_client.get_database_client(os.getenv("COSMOS_DB_NAME"))

# ─── Service Bus ───────────────────────────────────────────────────────────────
SB_CONN  = os.getenv("SERVICE_BUS_CONN_STR")
SB_QUEUE = os.getenv("SERVICE_BUS_QUEUE")

# ─── Model name constants ──────────────────────────────────────────────────────
# Use these everywhere instead of hardcoding strings
# If Azure renames a deployment, you only change it here
GPT4O = os.getenv("OPENAI_GPT4O_DEPLOYMENT")   # Most capable, most expensive
MINI  = os.getenv("OPENAI_MINI_DEPLOYMENT")    # Good for classification tasks
O1    = os.getenv("OPENAI_O1_DEPLOYMENT")      # Reasoning tasks, very expensive
PHI4  = os.getenv("OPENAI_PHI4_DEPLOYMENT")    # Cheapest, docs and formatting only