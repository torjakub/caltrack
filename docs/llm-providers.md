# LLM providers

LLM features are entirely optional. With `LLM_PROVIDER=none` (the default), the app is 100% usable — manual entry, barcode lookup, and search all work standalone. Configuring a provider adds:

- **OCR nutrition label**: photograph a product's nutrition table to prefill a new food entry.
- **Meal review**: get feedback on a logged meal.
- **Daily/weekly analysis**: a narrated summary of nutrient gaps computed in code (the LLM never does the arithmetic — it explains a pre-computed report).

If a configured provider is unreachable or misconfigured, every LLM feature fails gracefully and the UI shows "LLM not configured" — nothing else breaks.

## Configuring a provider

Set `LLM_PROVIDER` in `.env` to one of:

### `none` (default)
No configuration needed. All LLM features are hidden/disabled in the UI.

### `anthropic`
```
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-5
```
Requires a model with vision support for the OCR feature.

### `openai`
```
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-...
```

### `ollama` (local, on your network)
Run Ollama on a machine with enough CPU/RAM/GPU to serve models at reasonable speed — **not** the Raspberry Pi running the server, which isn't powerful enough. A Mac mini or similar always-on machine on the same LAN works well; the server just needs network access to it.

```
LLM_PROVIDER=ollama
OLLAMA_HOST=http://<ollama-host-lan-ip>:11434
OLLAMA_TEXT_MODEL=<a text model you've pulled, e.g. llama3.1>
OLLAMA_VISION_MODEL=<a vision-capable model you've pulled, e.g. llava or qwen2-vl, for OCR>
```

If the Ollama host is unreachable when the server checks (`GET {OLLAMA_HOST}/api/tags`, short timeout), LLM features report unavailable — same as `none` — rather than hanging or erroring loudly.

## Adding another provider

Implement the `LLMProvider` interface in `server/app/llm/` (`provider_name`, `is_available()`, `ocr_nutrition_label()`, `analyze_meal()`, `analyze_period()`) and register it in `server/app/llm/factory.py`. See `server/app/llm/base.py` for the exact contract.
