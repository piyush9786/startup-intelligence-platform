# Founder Adviser 8B compact hotfix

The logs show a 6,904-token prompt being truncated to 4,095 tokens and timing
out after seven minutes. The required Qdrant collections also return 404.

This repair switches to `qwen3:8b-q4_K_M`, disables thinking, compacts the
prompt while retaining the full immutable snapshot for integrity validation,
caps output at 512 tokens, uses a 4,096-token context, allows 20 minutes on
CPU, and temporarily disables the missing vector collections.
