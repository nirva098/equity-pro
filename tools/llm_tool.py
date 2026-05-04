from core.config import LLM_PROVIDER, OPENAI_API_KEY, GEMINI_API_KEY, ANTHROPIC_API_KEY

def get_llm(temperature=0.3):
    """
    Factory function to instantiate the correct LangChain LLM based on LLM_PROVIDER.
    Supports: openai, gemini, anthropic.
    Returns None if the required API key for the selected provider is missing.
    """
    provider = str(LLM_PROVIDER).lower()

    if provider == "gemini":
        if not GEMINI_API_KEY:
            print("Warning: GEMINI_API_KEY not set. Skipping LLM generation.")
            return None
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model="gemini-2.5-flash", 
                temperature=temperature, 
                api_key=GEMINI_API_KEY,
                max_retries=3
            )
        except Exception as e:
            print(f"Failed to initialize Gemini LLM: {e}")
            return None

    elif provider == "anthropic":
        if not ANTHROPIC_API_KEY:
            print("Warning: ANTHROPIC_API_KEY not set. Skipping LLM generation.")
            return None
        try:
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(model="claude-3-haiku-20240307", temperature=temperature, api_key=ANTHROPIC_API_KEY)
        except Exception as e:
            print(f"Failed to initialize Anthropic LLM: {e}")
            return None

    else:
        # Default to OpenAI
        if not OPENAI_API_KEY:
            print("Warning: OPENAI_API_KEY not set. Skipping LLM generation.")
            return None
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model="gpt-4o-mini", temperature=temperature, api_key=OPENAI_API_KEY)
        except Exception as e:
            print(f"Failed to initialize OpenAI LLM: {e}")
            return None
