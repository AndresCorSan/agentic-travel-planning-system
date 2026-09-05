import os
from langchain_openrouter import ChatOpenRouter

# Providers that offer the best balance between speed and cost for MiMo-V2.5
# Xiaomi is preferred over NovitaAI because it is cheaper
MIMO_PROVIDER = {
    "order": ["xiaomi", "novita"],
    "allow_fallbacks": False,
}

# Normal LLM
llm = ChatOpenRouter(
    model="xiaomi/mimo-v2.5",
    api_key=os.environ["OPENROUTER_API_KEY"],
    openrouter_provider=MIMO_PROVIDER,
)

# Low-effort LLM for faster and cheaper responses
low_reasoning_llm = ChatOpenRouter(
    model="xiaomi/mimo-v2.5",
    api_key=os.environ["OPENROUTER_API_KEY"],
    openrouter_provider=MIMO_PROVIDER,
    reasoning={
        "effort": "minimal",
    },
)

# Lightweight LLM for simple tasks
light_llm = ChatOpenRouter(
    model="google/gemma-3-12b-it",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

# These are faster and cheaper options, but they are usually blocked in OpenRouter 
# because they have a higher demand. As a fallback, we use MiMo-V2.5 with minimal reasoning.
# subagent_llm = ChatOpenAI(
#     model="inclusionai/ling-3.0-flash",
#     # model="mistralai/mistral-small-3.2-24b-instruct",
#     # model="google/gemma-3-27b-it",
#     base_url="https://openrouter.ai/api/v1",
#     api_key=os.getenv("OPENROUTER_API_KEY"),
# )
subagent_llm = low_reasoning_llm