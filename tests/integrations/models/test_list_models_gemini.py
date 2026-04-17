import google.generativeai as genai
from config import get_settings
from utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

api_key = settings.gemini_api_key

if not api_key:
    logger.error("❌ Error: API Key not found in environment variables.")
else:
    # 2. Configure the SDK
    genai.configure(api_key=api_key)

    logger.info("--- Available Models for Gemini 3 Series ---")
    try:
        # 3. List and filter models
        for m in genai.list_models():
            # We only care about models that can actually 'chat' (generateContent)
            if "generateContent" in m.supported_generation_methods:
                # Highlight Gemini 3 models
                if "gemini-3" in m.name:
                    logger.info(f"✅ FOUND: {m.name}")
                    logger.info(f"   > Display Name: {m.display_name}")
                    logger.info(f"   > Input Limit: {m.input_token_limit}")
                else:
                    logger.info(f" - {m.name}")
    except Exception as e:
        logger.error(f"❌ Failed to list models: {e}")
