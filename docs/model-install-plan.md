# План моделей и хранения на DGX Spark

> **Статус: план, не отчёт об установке.** SSH-сервис Spark доступен по сети, но удалённая авторизация пока не прошла. Конфигурацию памяти, свободное место и содержимое диска на устройстве не проверяли; наличие `/srv/ai` также не подтверждено, папку мы не создавали.

## Какие модели планируем

### Первый этап

| Приоритет | Идентификатор | Назначение | Условия запуска |
|---|---|---|---|
| 1 | [`nvidia/Qwen3.8-27B-NVFP4`](https://huggingface.co/nvidia/Qwen3.8-27B-NVFP4) | Основная coding-модель и локальный API для Windows IDE | Использовать соответствующий официальный [рецепт vLLM для DGX Spark](https://build.nvidia.com/spark/vllm/intermediate). Сначала установить только её и проверить фактическую память, диск, готовность API и тестовый запрос. |
| 1a | [`z-lab/Qwen3.8-27B-DFlash2`](https://huggingface.co/z-lab/Qwen3.8-27B-DFlash2) | Вспомогательная draft-модель, требуемая некоторыми вариантами рецепта Qwen для speculative decoding | Загружать только если это предусмотрено выбранным NVIDIA-рецептом; учитывать в манифесте и расчёте места. |
| 2 | [`Tongyi-MAI/Z-Image-Turbo`](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo) | Генерация иллюстраций, фонов и концептов через ComfyUI | Устанавливать после проверки coding-модели. Сверить версии и каталог моделей с [NVIDIA quick start для ComfyUI на Spark](https://build.nvidia.com/spark/comfyui/image-gen-quick-start). |

### Позже, если появится конкретная потребность

| Идентификатор | Для чего | Решение |
|---|---|---|
| FLUX.2 Klein 4B | Редактирование изображений и работа с референсами | Не включать в первый запуск; сначала подтвердить совместимость workflow с выбранной версией ComfyUI по [руководству ComfyUI](https://docs.comfy.org/tutorials/flux/flux-2-klein). |
| `Qwen/Qwen3-Embedding-0.6B` + `Qwen/Qwen3-Reranker-0.6B` | Поиск по большой локальной кодовой базе | Отложить до выбора и проверки отдельного retrieval-стека. |
| `deepseek-ai/DeepSeek-OCR-2` | Извлечение текста и структуры из PDF/скриншотов | Отложить до появления OCR-сценария и проверки runtime. |

Модели, отмеченные «позже», **не входят в первоначальный план установки**. Веса могут храниться на SSD, но не следует рассчитывать на одновременную загрузку всех моделей в общую память Spark; запускать и проверять их нужно по одной.

## Структура `/srv/ai`

```text
/srv/ai/
├── apps/
│   ├── vllm/                  # проверенные launch-скрипты и конфигурации
│   └── comfyui/               # приложение и workflow, отдельно от весов
├── models/
│   ├── huggingface/hub/       # управляемое хранилище HF-моделей
│   ├── comfyui/               # модели ComfyUI; точный layout сверить с recipe
│   └── optional/              # отложенные embedding/OCR/прочие checkpoints
├── cache/
│   ├── huggingface/           # метаданные/служебный кэш HF
│   ├── torch/
│   ├── xdg/
│   └── runtime/
├── tmp/
│   └── downloads/             # временные и незавершённые загрузки
├── logs/                      # журналы сервисов
└── manifests/                 # ID, revision, формат, размер, лицензия и дата
```

Hugging Face Hub управляет содержимым `models/huggingface/hub`: не переименовывать и не удалять его файлы вручную. Это постоянное хранилище весов, а не временный кэш для массовой очистки. Перед настройкой ComfyUI сверить каталог загрузки с NVIDIA setup script и направить его в `models/comfyui`, не оставляя вторую копию в каталоге приложения. Удалять содержимое `tmp/downloads` можно только после завершения загрузчиков и проверки, что там нет нужных файлов.

## Создание каталогов на Spark

Перед созданием проверить свободное место и отсутствие существующего каталога. Если `/srv/ai` уже есть, сначала изучить его содержимое — не менять владельца рекурсивно и не очищать его автоматически.

```bash
df -h /srv
if [ -e /srv/ai ]; then
  printf '%s\n' '/srv/ai уже существует — сначала проверьте содержимое и владельца.'
else
  sudo install -d -m 0755 -o "$(id -un)" -g "$(id -gn)" \
    /srv/ai/apps/vllm \
    /srv/ai/apps/comfyui \
    /srv/ai/models/huggingface/hub \
    /srv/ai/models/comfyui \
    /srv/ai/models/optional \
    /srv/ai/cache/huggingface \
    /srv/ai/cache/torch \
    /srv/ai/cache/xdg \
    /srv/ai/cache/runtime \
    /srv/ai/tmp/downloads \
    /srv/ai/logs \
    /srv/ai/manifests
fi
```

Для процессов Hugging Face задать постоянные пути в окружении самого сервиса до его запуска, затем проверить их фактическое значение:

```bash
export HF_HOME=/srv/ai/cache/huggingface
export HF_HUB_CACHE=/srv/ai/models/huggingface/hub
export TORCH_HOME=/srv/ai/cache/torch
export XDG_CACHE_HOME=/srv/ai/cache/xdg
export TMPDIR=/srv/ai/tmp/downloads
```

Проверить, что launch-скрипт и контейнер действительно получают эти переменные. Не скачивать одну модель одновременно в HF Hub и отдельный `--local-dir`: это может создать дубликат. Не менять параметры официального рецепта вслепую — сначала проверить, какой путь он использует.

## Правило учёта и установки

Для каждого checkpoint сохранить в `/srv/ai/manifests/` запись с полями `repo_id`, revision/commit, quantization/format, runtime, точным путём, размером, лицензией и датой загрузки. Устанавливать по одному: проверить диск и конфигурацию устройства → скачать → сверить файлы и место → запустить health-check и минимальный запрос → зафиксировать результат. До проверки на самом Spark список выше остаётся планом.
