from questly.ai.client import OpenRouterGenerationClient
from questly.config import get_settings
from questly.core.generation.schemas import GenerationRequest

settings = get_settings()

client = OpenRouterGenerationClient(
    api_key=settings.openrouter_api_key, model="google/gemma-4-31b-it:free"
)

try:
    req = GenerationRequest(prompt="create a two sum python problem in thai")
    res = client.generate(req)
    print("Success:", res.draft.title)
except Exception:
    import traceback

    traceback.print_exc()
