export HF_HOME="$HOME/ai-models/models/hf-hub"
mkdir -p "$HF_HOME"
df -h "$HF_HOME"



hf download Qwen/Qwen3.8-27B
sudo docker pull nvcr.io/nvidia/vllm:26.10.pre1-py3
