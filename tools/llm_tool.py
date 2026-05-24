import time
from core.config import LLM_PROVIDER, OPENAI_API_KEY, GEMINI_API_KEY, ANTHROPIC_API_KEY


class _RateLimitRetryLLM:
    """
    Wraps a LangChain LLM with exponential-backoff retry on 429 RESOURCE_EXHAUSTED.
    This is critical for free-tier Gemini which has a limit of 20 RPD.
    """
    def __init__(self, llm, max_retries: int = 4, base_delay: float = 15.0):
        self._llm = llm
        self._max_retries = max_retries
        self._base_delay = base_delay

    def invoke(self, prompt: str):
        last_err = None
        for attempt in range(self._max_retries):
            try:
                return self._llm.invoke(prompt)
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    wait = self._base_delay * (2 ** attempt)
                    print(f"  [LLM] Rate limit hit (attempt {attempt + 1}/{self._max_retries}). "
                          f"Waiting {wait:.0f}s before retry...")
                    time.sleep(wait)
                    last_err = e
                else:
                    raise
        raise last_err


def get_llm(temperature=0.3):
    """
    Factory function to instantiate the correct LangChain LLM based on LLM_PROVIDER.
    Supports: openai, gemini, anthropic.
    Wraps the LLM with rate-limit retry logic (exponential backoff on 429).
    Returns None if the required API key for the selected provider is missing.
    """
    provider = str(LLM_PROVIDER).lower()

    if provider == "gemini":
        if not GEMINI_API_KEY:
            print("Warning: GEMINI_API_KEY not set. Skipping LLM generation.")
            return None
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            # Use gemini-2.0-flash as primary — it has a higher free-tier RPM/RPD quota
            # than gemini-2.5-flash (which is only 20 RPD on free tier)
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash",
                temperature=temperature,
                api_key=GEMINI_API_KEY,
                max_retries=2,
            )
            return _RateLimitRetryLLM(llm, max_retries=3, base_delay=20.0)
        except Exception as e:
            print(f"Failed to initialize Gemini LLM: {e}")
            return None

    elif provider == "anthropic":
        if not ANTHROPIC_API_KEY:
            print("Warning: ANTHROPIC_API_KEY not set. Skipping LLM generation.")
            return None
        try:
            from langchain_anthropic import ChatAnthropic
            llm = ChatAnthropic(model="claude-3-haiku-20240307", temperature=temperature, api_key=ANTHROPIC_API_KEY)
            return _RateLimitRetryLLM(llm, max_retries=3, base_delay=10.0)
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
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=temperature, api_key=OPENAI_API_KEY)
            return _RateLimitRetryLLM(llm, max_retries=3, base_delay=5.0)
        except Exception as e:
            print(f"Failed to initialize OpenAI LLM: {e}")
            return None
