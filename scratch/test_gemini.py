from dotenv import load_dotenv
load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI

for model_name in ["gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-pro"]:
    print(f"Testing {model_name}...")
    try:
        llm = ChatGoogleGenerativeAI(model=model_name, temperature=0.3)
        res = llm.invoke("Hello")
        print(f"Success with {model_name}: {res.content[:20]}")
        break
    except Exception as e:
        print(f"Failed with {model_name}: {e}")
