export HF_HOME="$HOME/ai-models/models/hf-hub"

mkdir -p "$HF_HOME"

df -h "$HF_HOME"



----



hf download Qwen/Qwen3.8-27B

sudo docker pull nvcr.io/nvidia/vllm:26.10.pre1-py3



-----




sudo docker run --rm -it \
  --gpus all \
  --ipc host \
  --network host \
  --shm-size=16g \
  --ulimit memlock=-1 \
  --ulimit stack=67108864 \
  -v "$HF_HOME:/root/.cache/huggingface" \
  --entrypoint /bin/bash \
  nvcr.io/nvidia/vllm:26.10.pre1-py3



  ------



  vllm serve Qwen/Qwen3.8-27B \
  --host 127.0.0.1 \
  --port 8000 \
  --dtype bfloat16 \
  --max-model-len 8192 \
  --max-num-seqs 1 \
  --max-num-batched-tokens 4096 \
  --gpu-memory-utilization 0.60 \
  --reasoning-parser qwen3 \
  --tool-call-parser qwen3_xml \
  --enable-auto-tool-choice





Ошибка из-за переносов: без завершающего \ Bash воспринимает каждую строку как отдельную команду. Поэтому docker run получил только run без имени образа; контейнер не запустился.

Сначала проверьте, что веса модели действительно скачаны:

du -shL "$HOME/ai-models/models/hf-hub/hub/models--Qwen--Qwen3.8-27B/snapshots/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"


Если размер около 55 ГБ, запустите Docker-команду одной строкой:

sudo docker run --rm -it --gpus all --ipc host --network host --shm-size=16g --ulimit memlock=-1 --ulimit stack=67108864 -v "$HOME/ai-models/models/hf-hub:/root/.cache/huggingface" --entrypoint /bin/bash nvcr.io/nvidia/vllm:26.10.pre1-py3



Когда появится приглашение контейнера root@..., запустите внутри него:

vllm serve Qwen/Qwen3.8-27B --host 127.0.0.1 --port 8000 --dtype bfloat16 --max-model-len 8192 --max-num-seqs 1 --max-num-batched-tokens 4096 --gpu-memory-utilization 0.60 --reasoning-parser qwen3 --tool-call-parser qwen3_xml --enable-auto-tool-choice


Если проверка размера покажет почти 0, не запускайте контейнер — пришлите её вывод.
