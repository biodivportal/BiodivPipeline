import json
from pathlib import Path
import anthropic
import openai

CONFIG_DIR = Path(__file__).parent.parent / "config"
LLM_PROMPT_FILE = CONFIG_DIR / "llm_prompt.json"


def get_llm_prediction(
    api_key: str,
    llm_provider: str,
    llm_model: str,
    header: str,
    example_val: str,
    predictions: list[str],
    term_descriptions: dict[str, str],
) -> dict | None:
    if not api_key:
        return None

    provider = llm_provider.lower()

    if provider == "anthropic":
        try:
            client = anthropic.Anthropic(api_key=api_key)
        except Exception as e:
            print(f"Failed to initialize Anthropic client: {e}")
            return None
    elif provider == "openai":
        try:
            client = openai.OpenAI(api_key=api_key)
        except Exception as e:
            print(f"Failed to initialize OpenAI client: {e}")
            return None
    else:
        print(f"Unsupported LLM provider: {llm_provider}")
        return None

    preds_text = ""
    for idx, p in enumerate(predictions):
        desc = term_descriptions.get(p.lower(), "Keine Beschreibung verfügbar.")
        preds_text += f"{idx + 1}. {p}: {desc}\n"

    try:
        with open(LLM_PROMPT_FILE, "r", encoding="utf-8") as f:
            prompt_data = json.load(f)
            prompt_template = prompt_data.get("prompt_template", "")
    except Exception as e:
        print(f"Failed to load LLM prompt template: {e}")
        return None

    prompt = prompt_template.format(
        header=header, example_val=example_val, preds_text=preds_text
    )

    try:
        if provider == "anthropic":
            response = client.messages.create(
                model=llm_model,
                max_tokens=100,
                temperature=0.0,
                messages=[{"role": "user", "content": prompt}],
            )
            result_text = response.content[0].text
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
        elif provider == "openai":
            response = client.chat.completions.create(
                model=llm_model,
                max_tokens=100,
                temperature=0.0,
                messages=[{"role": "user", "content": prompt}],
            )
            result_text = response.choices[0].message.content
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens

        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0]
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0]

        result = json.loads(result_text.strip())
        return {
            "prediction": result.get("llm_prediction"),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }
    except Exception as e:
        print(f"Error calling LLM for header {header}: {e}")
        return None
