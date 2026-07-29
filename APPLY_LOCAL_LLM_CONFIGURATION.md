# Local LLM configuration

This patch configures the project for the current Docker Desktop allocation:

- 16 CPUs available to Docker Desktop
- 24.3 GB RAM available to Docker Desktop
- CPU inference because the NVIDIA container runtime is not currently available
- `qwen3:8b-q4_K_M` for the advisor and chatbot
- 8192-token context
- one parallel request
- up to two loaded models so the generation and embedding models can coexist
- `embeddinggemma` for Qdrant/RAG compatibility
- 12 CPU and 12 GB hard limit for the Ollama container

## Apply

```bash
cd /home/ps/Project/startup-intelligence-platform
unzip -o ~/Downloads/local-llm-cpu-configuration-hotfix.zip -d .
chmod +x scripts/configure_local_llm.sh scripts/llm_status.sh
./scripts/configure_local_llm.sh
```

The first run downloads approximately 5.2 GB for the generation model and about
622 MB for the embedding model. It then performs a real structured-output test
through the Django provider.

For a faster, lower-quality profile:

```bash
./scripts/configure_local_llm.sh --fast
```

Do not use the project's `--gpu` option until the NVIDIA Container Toolkit is
installed and `docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04
nvidia-smi` succeeds.
