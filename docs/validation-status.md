# Матрица проверки и статус реализации

Последняя ревизия документации: 2026-11-01. Эта страница отделяет просмотр документации и статическую проверку скриптов от установки на реальном оборудовании.

## Переданный владельцем снимок среды

Следующие данные скопированы владельцем из терминала; агент не подключался к устройству и не запускал эти команды самостоятельно. Идентификаторы хоста и пользователя намеренно не публикуются.

- GPU: NVIDIA GB10; `nvidia-smi --query-gpu=memory.total` вернул `N/A`.
- Unified memory: `MemTotal` 127,598,416 kB, `free -h` показал 121 GiB — система соответствует 128-ГБ конфигурации.
- ОС и архитектура: Ubuntu 24.04.5 LTS, Linux ARM64.
- Хранилище: около 3.5 TB свободно на системном NVMe-разделе; `/srv` и `$HOME` находятся на том же filesystem.
- Docker Engine 29.6.2: daemon активен; обычный пользователь не имеет доступа к `/var/run/docker.sock`, `sudo docker info` работает. Изменение групп пользователя не выполнялось.
- Владелец попросил пока **не скачивать и не запускать модели**. Поэтому нет результатов старта vLLM, ComfyUI, API-запросов или генерации изображения.

Для следующего этапа нужно отдельно выбрать способ доступа к Docker: запуск административных Docker-команд через `sudo` либо осознанное добавление пользователя в группу `docker` (это даёт привилегии уровня root). В этой ревизии ни один способ установки не применялся.

## Текущий статус

| Сценарий | Проверено по официальной документации | Локальная статическая проверка | Установлено/проверено на DGX Spark пользователя | Статус |
|---|---|---|---|---|
| Qwen3.8-27B NVFP4, Spark 64 ГБ | Есть отдельный vLLM recipe.[20][65] | Pinned launch script прошёл `bash -n` | На устройстве владельца не запускалось | Справочный вариант; аппаратно не проверен |
| Qwen3.8-27B NVFP4 + DFlash2, Spark 128 ГБ | Есть отдельный 128-ГБ launch recipe и точные checkpoint ID.[20][66][68] | Pinned launch script прошёл `bash -n`; локальный revision-patch проверен на pinned 64/128-ГБ vendor scripts.[66][77][78] Exact NGC image CLI support ещё pending.[88][89] | Владелец сообщил 128 ГБ, но запретил загрузку/запуск; Docker доступен через `sudo` | Источники и статическая проверка пройдены; аппаратная проверка ожидает |
| ComfyUI + Z-Image-Turbo BF16 bundle | Закреплённый NVIDIA setup script использует точные BF16-файлы из `Comfy-Org/z_image_turbo`.[67][79][93] | Локальная копия фиксирует Hub revision и заменяет три `wget -nc` на возобновляемые `wget -c`; преобразование прошло `bash -n`. Pinned workflow JSON указывает те же три baseline-файла. HEAD-запрос к pinned BF16 URL вернул `Accept-Ranges: bytes`; тело весов не скачивалось.[67][79][93] | Владелец не разрешил загрузку/генерацию; на Spark не запускалось | Источники, скрипт и workflow статически проверены; аппаратная валидация ожидает |
| Z-Image INT8 / NVFP4 variants | Репозиторий модели содержит отдельные файлы; pinned workflow snapshot включает отдельную INT8/FP8-пару и не содержит NVFP4 template.[72][94][102] | Пара INT8 статически сверена с workflow; memory/performance на GB10 не измерялись, pairing для NVFP4 не подтверждён.[79][94][102] | Нет | Только отдельные варианты; совместимость с устройством не подтверждена |
| `Tongyi-MAI/Z-Image-Turbo` upstream | Apache-2.0 upstream-модель; не repackaged BF16-файлы из NVIDIA setup.[25][86] | В target recipe не используется | Не скачивалась/не проверялась | Только справочная модель |
| FLUX.2-klein-4B Base / Distilled | ComfyUI guide описывает отдельные workflow для вариантов; Apache-2.0.[26][74][80] | Spark-specific launcher отсутствует | Нет | Опционально позже: runtime/workflow и сквозной тест редактирования на GB10 не выполнены |
| FLUX.2-klein-9B | Gated FLUX Non-Commercial License; BFL указывает non-commercial/non-production условия.[75][81][87] | Spark-specific launcher отсутствует | Нет | Опционально позже; не входит в коммерческий baseline; runtime/workflow и сквозная проверка не выполнены; не установлена |
| Qwen3-Embedding-0.6B | Проверены metadata модели Apache-2.0; retrieval recipe не выбран.[30][82] | Runtime/индекс не интегрированы | Нет | Опционально позже: runtime и индекс не выбраны; сквозной поиск не проверен, модель не установлена |
| Qwen3-Reranker-0.6B | Проверены metadata модели Apache-2.0; задача отдельного ranking.[31][83] | Ranking endpoint не создан | Нет | Опционально позже: runtime ранжирования и сквозной retrieval-процесс не проверены; модель не установлена |
| DeepSeek-OCR-2 | Apache-2.0, 3B BF16; пример model card не является Spark recipe.[33][84] | Совместимость CUDA/Transformers с target не проверена | Нет | Опционально позже: OCR runtime и сквозная OCR-процедура не проверены; модель не установлена |
| Android assets и тесты | Официальные инструкции Android Studio, .NET testing и asset tooling учтены.[34][40][41] | Конкретный app-проект здесь не собран | Нет app-проекта для end-to-end теста | Рекомендации, не integration-tested |
| Windows/Android SDK и CLI build | Учтены Windows App SDK, Android Studio и Android build command-line docs.[44][47][62] | PowerShell/Gradle/.NET команды предназначены для Windows; сборки не запускались ни на Windows, ни на Spark | Нет app-проекта для end-to-end теста | Рекомендации; интеграционное тестирование не выполнялось |

Команды `bash -n` проверяют только синтаксис shell-файлов; они не доказывают, что Docker image загрузится, веса скачаются, модель поместится в доступную память или сервис запустится на конкретном Spark.

## Приёмочные проверки для владельца Spark

До установки запишите обезличенный вывод:

```bash
cat /etc/os-release
nvidia-smi
free -h
df -h "$HOME"
docker version
python3 --version
git --version
```

Не публикуйте токены Hugging Face/NGC, SSH-ключи, пароли или персональные данные вместе с логами.

Для каждой конфигурации, которую нужно объявить проверенной:

- [ ] Зафиксированы модель устройства, память, DGX OS, драйвер и свободное место.
- [ ] Скачаны заявленные container/model revisions; записаны результаты и свободное место после загрузки.
- [ ] vLLM готов; `/health` возвращает успех; `/v1/models` возвращает ожидаемую модель.
- [ ] Отправлен реальный запрос и сохранён обезличенный результат.
- [ ] Модель остановлена и повторно запущена; проверено освобождение памяти и повторное использование кеша.
- [ ] Для ComfyUI открывается интерфейс через локальный SSH-туннель; выполнен Z-Image workflow и сохранён пример результата.
- [ ] Записаны peak memory, время загрузки и генерации, ошибки и ограничения.
- [ ] Лицензии конкретных checkpoint и зависимостей просмотрены перед коммерческим использованием.

## Важно о воспроизводимости

Qwen 128-ГБ runbook теперь фиксирует target/draft revisions в командах загрузки и launch config.[66][77][78]

Поддержка revision-полей в точном 128-ГБ NGC image требует проверки его CLI; этот image не запускался.[88][89]

ComfyUI runbook патчит локальную копию setup script на pinned Hub snapshot; преобразование прошло `bash -n`, а BF16/INT8 workflow pairing статически сверены.[67][79][93]

Загрузки весов, запуск моделей, API-запросы и генерация на Spark не выполнялись по решению владельца; аппаратная валидация остаётся **BLOCKED / NOT RUN**.

## Sources

[20] https://build.nvidia.com/spark/vllm/intermediate
[25] https://huggingface.co/Tongyi-MAI/Z-Image-Turbo
[26] https://docs.comfy.org/tutorials/flux/flux-2-klein
[30] https://huggingface.co/Qwen/Qwen3-Embedding-0.6B
[31] https://huggingface.co/Qwen/Qwen3-Reranker-0.6B
[33] https://huggingface.co/deepseek-ai/DeepSeek-OCR-2
[34] https://developer.android.com/studio/write/image-asset-studio
[40] https://developer.android.com/studio/test
[41] https://learn.microsoft.com/en-us/dotnet/core/testing
[44] https://learn.microsoft.com/en-us/windows/apps/windows-app-sdk
[47] https://developer.android.com/studio
[62] https://developer.android.com/build/building-cmdline
[65] https://raw.githubusercontent.com/NVIDIA/dgx-spark-playbooks/30883150541743d580c9c347700c6ac99fc396d2/nvidia/playbook-vllm/assets/sync-vllm-spark-64gb-qwen38-27b.sh
[66] https://raw.githubusercontent.com/NVIDIA/dgx-spark-playbooks/30883150541743d580c9c347700c6ac99fc396d2/nvidia/playbook-vllm/assets/sync-vllm-spark-128gb-qwen38-27b.sh
[67] https://raw.githubusercontent.com/NVIDIA/dgx-spark-playbooks/30883150541743d580c9c347700c6ac99fc396d2/nvidia/playbook-comfyui/assets/setup.sh
[68] https://huggingface.co/z-lab/Qwen3.8-27B-DFlash2
[72] https://huggingface.co/Comfy-Org/z_image_turbo
[74] https://huggingface.co/black-forest-labs/FLUX.2-klein-4B
[75] https://huggingface.co/black-forest-labs/FLUX.2-klein-9B
[77] https://huggingface.co/api/models/nvidia/Qwen3.8-27B-NVFP4?blobs=true
[78] https://huggingface.co/api/models/z-lab/Qwen3.8-27B-DFlash2?blobs=true
[79] https://huggingface.co/api/models/Comfy-Org/z_image_turbo?blobs=true
[80] https://huggingface.co/api/models/black-forest-labs/FLUX.2-klein-4B?blobs=true
[81] https://huggingface.co/api/models/black-forest-labs/FLUX.2-klein-9B?blobs=true
[82] https://huggingface.co/api/models/Qwen/Qwen3-Embedding-0.6B?blobs=true
[83] https://huggingface.co/api/models/Qwen/Qwen3-Reranker-0.6B?blobs=true
[84] https://huggingface.co/api/models/deepseek-ai/DeepSeek-OCR-2?blobs=true
[86] https://huggingface.co/api/models/Tongyi-MAI/Z-Image-Turbo?blobs=true
[87] https://huggingface.co/black-forest-labs/FLUX.2-klein-9B/blob/main/LICENSE.md
[88] https://docs.vllm.ai/en/v0.28.0/api/vllm/config/speculative
[89] https://docs.vllm.ai/en/v0.28.0/cli/serve
[93] https://raw.githubusercontent.com/Comfy-Org/workflow_templates/c067929d7e9cc0f3fd15be348fa1a1d85da15946/templates/image_z_image_turbo.json
[94] https://raw.githubusercontent.com/Comfy-Org/workflow_templates/c067929d7e9cc0f3fd15be348fa1a1d85da15946/templates/image_z_image_turbo_int8.json
[102] https://github.com/Comfy-Org/workflow_templates/tree/c067929d7e9cc0f3fd15be348fa1a1d85da15946/templates
