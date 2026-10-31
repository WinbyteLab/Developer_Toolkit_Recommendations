# План моделей и хранения на DGX Spark

> **Статус: план, не отчёт об установке.** По переданному владельцем preflight-выводу Spark — NVIDIA GB10, 128 ГБ по `MemTotal`, Ubuntu 24.04.5 LTS ARM64 и около 3,5 ТБ свободно. Docker daemon активен, но обычный пользователь не имеет доступа к socket; через `sudo` проверка версии сервера проходит. Агент не подключался к Spark, `/srv/ai` не проверялся. По решению владельца модели пока не устанавливаются.

Подробные сценарии: [Qwen3.8-27B runbook](../model/Qwen3.8-27B/README.md) и [ComfyUI + Z-Image-Turbo runbook](./comfyui-zimage.md).

## Какие модели планируем

### Первый этап

| Приоритет | Идентификатор | Назначение | Условия запуска |
|---|---|---|---|
| 1 | [`nvidia/Qwen3.8-27B-NVFP4`](https://huggingface.co/nvidia/Qwen3.8-27B-NVFP4) | Основная coding-модель и локальный API для Windows IDE | Использовать соответствующий официальный [рецепт vLLM для DGX Spark](https://build.nvidia.com/spark/vllm/intermediate). Сначала установить только её и проверить фактическую память, диск, готовность API и тестовый запрос. |
| 1a | [`z-lab/Qwen3.8-27B-DFlash2`](https://huggingface.co/z-lab/Qwen3.8-27B-DFlash2) | Вспомогательная draft-модель, требуемая некоторыми вариантами рецепта Qwen для speculative decoding | Загружать только если это предусмотрено выбранным NVIDIA-рецептом; учитывать в манифесте и расчёте места. |
| 2 | [`Comfy-Org/z_image_turbo`](https://huggingface.co/Comfy-Org/z_image_turbo) — BF16 baseline files | Генерация иллюстраций, фонов и концептов через ComfyUI | Только baseline bundle из трёх файлов, который использует NVIDIA setup script; устанавливать после проверки coding-модели и отдельного разрешения. `Tongyi-MAI/Z-Image-Turbo` — upstream-источник, не repo весов из этого recipe. Сверить файлы и каталог с [NVIDIA quick start](https://build.nvidia.com/spark/comfyui/image-gen-quick-start) и [отдельным runbook](./comfyui-zimage.md). |

### Позже, если появится конкретная потребность

Ниже — отложенные компоненты, не часть первоначальной установки. Для каждого сначала определить сценарий и точный checkpoint, проверить лицензию, выбрать совместимый runtime и описать end-to-end процедуру; до проверки на целевой среде не включать компонент в baseline и не скачивать.

| Идентификатор | Для чего | Решение |
|---|---|---|
| FLUX.2 Klein 4B | Редактирование изображений и работа с референсами | Опционально позже; не включать в первоначальный baseline. Сверить workflow с выбранной версией ComfyUI по [ComfyUI guide](https://docs.comfy.org/tutorials/flux/flux-2-klein) и выполнить сквозной тест на целевой среде; runtime и DGX Spark workflow пока не проверены. |
| [black-forest-labs/FLUX.2-klein-9B](https://huggingface.co/black-forest-labs/FLUX.2-klein-9B) | Генерация и редактирование изображений | Не включать в коммерческий/производственный baseline: точный checkpoint распространяется по [FLUX Non-Commercial License](https://huggingface.co/black-forest-labs/FLUX.2-klein-9B/blob/main/LICENSE.md). Рассматривать только для подходящего некоммерческого сценария, после проверки лицензии, выбора runtime/workflow и сквозного теста на целевой системе. |
| `Qwen/Qwen3-Embedding-0.6B` + `Qwen/Qwen3-Reranker-0.6B` | Поиск по большой локальной кодовой базе | Отложить до выбора retrieval-стека и end-to-end процедуры индексации, поиска и rerank на целевой среде. |
| `deepseek-ai/DeepSeek-OCR-2` | Извлечение текста и структуры из PDF/скриншотов | Отложить до появления конкретного OCR-сценария, выбора совместимого runtime и сквозной проверки на целевой среде. |

Модели, отмеченные «позже», **не входят в первоначальный план установки**. Веса могут храниться на SSD, но не следует рассчитывать на одновременную загрузку всех моделей в общую память Spark; запускать и проверять их нужно по одной.

## Структура `/srv/ai`

```text
/srv/ai/
├── apps/
│   ├── vllm/                  # проверенные launch-скрипты и конфигурации
│   └── comfyui/               # приложение и workflow, отдельно от весов
├── models/
│   ├── huggingface/hub/       # постоянное HF-хранилище моделей; layout управляется HF
│   ├── comfyui/               # модели ComfyUI; точный layout сверить с recipe
│   └── optional/              # отложенные embedding/OCR/прочие checkpoints
├── cache/
│   ├── vllm/                  # runtime cache (64-GB recipe)
│   ├── flashinfer/            # runtime cache (64-GB recipe)
│   ├── triton/                # runtime cache (64-GB recipe)
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
    /srv/ai/cache/vllm \
    /srv/ai/cache/flashinfer \
    /srv/ai/cache/triton \
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
export AI_ROOT=/srv/ai
export HF_HOME="$AI_ROOT/models/huggingface"
export HF_HUB_CACHE="$HF_HOME/hub"
export TORCH_HOME="$AI_ROOT/cache/torch"
export XDG_CACHE_HOME="$AI_ROOT/cache/xdg"
export TMPDIR="$AI_ROOT/tmp/downloads"
```

Проверить, что launch-скрипт и контейнер действительно получают эти переменные. Не скачивать одну модель одновременно в HF Hub и отдельный `--local-dir`: это может создать дубликат. Не менять параметры официального рецепта вслепую — сначала проверить, какой путь он использует.

## Правило учёта и установки

Для каждого checkpoint сохранить в `/srv/ai/manifests/` запись с полями `repo_id`, revision/commit, quantization/format, runtime, точным путём, размером, лицензией и датой загрузки. Устанавливать по одному: проверить диск и конфигурацию устройства → скачать → сверить файлы и место → запустить health-check и минимальный запрос → зафиксировать результат. До проверки на самом Spark список выше остаётся планом.
