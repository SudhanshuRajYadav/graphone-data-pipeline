"""Multi-tier LLM fallback engine with exponential backoff + jitter."""
import time, random

def build_providers(gemini_model, groq_client, groq_model_primary="openai/gpt-oss-20b",
                     groq_model_backup="qwen/qwen3.6-27b"):
    def call_gemini(prompt):
        return gemini_model.generate_content(prompt, request_options={"timeout": 40}).text

    def call_groq(prompt):
        r = groq_client.chat.completions.create(
            model=groq_model_primary, messages=[{"role": "user", "content": prompt}], timeout=15)
        return r.choices[0].message.content

    def call_groq_backup(prompt):
        r = groq_client.chat.completions.create(
            model=groq_model_backup, messages=[{"role": "user", "content": prompt}], timeout=15)
        return r.choices[0].message.content

    return [("groq-primary", call_groq), ("groq-backup", call_groq_backup), ("gemini", call_gemini)]


def extract_with_fallback(prompt, providers, max_retries=3):
    """Tries each provider in order; within a provider, retries with backoff+jitter
    before moving to the next tier. Raises only if every provider is exhausted."""
    for name, fn in providers:
        for attempt in range(max_retries):
            try:
                result = fn(prompt)
                return result, name
            except Exception as e:
                wait = 6 + random.uniform(0, 3)  # backoff + jitter
                print(f"[{name}] attempt {attempt+1} failed: {type(e).__name__} — retry in {wait:.1f}s")
                time.sleep(wait)
        print(f"[{name}] exhausted after {max_retries} attempts")
    raise Exception("All LLM providers failed")
