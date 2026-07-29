# Founder Adviser CPU Timeout Fix

The failed job ran for roughly 600 seconds, matching the configured balanced-profile Ollama timeout. The full grounded briefing prompt is too slow for the 8B model on CPU.

This repair:

- switches the Founder Adviser and chatbot to `qwen3:4b-instruct-2507-q4_K_M`;
- keeps `embeddinggemma` and RAG enabled;
- reduces the adviser context from 8192 to 4096 tokens;
- limits retrieved evidence to two compact chunks;
- reduces maximum generated output to 900 tokens;
- prewarms the model before restarting Django and Celery;
- preserves all failed jobs and generated records for audit;
- backs up `.env` before making changes.

Apply:

```bash
cd /home/ps/Project/startup-intelligence-platform
unzip -o ~/Downloads/founder-advisor-timeout-hotfix.zip -d .
chmod +x scripts/fix_founder_advisor_timeout.sh
./scripts/fix_founder_advisor_timeout.sh
```

Then hard-refresh `/advisor` and generate the briefing again.
