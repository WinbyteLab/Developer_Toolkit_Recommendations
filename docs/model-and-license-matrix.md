# Техническая матрица моделей, runtime и лицензий

**Снимок Hugging Face Hub: 2026-10-31.** SHA и размеры ниже — metadata точных репозиториев на момент запроса к Hub API, а не подтверждение скачивания. Общий размер репозитория включает все перечисленные в нём файлы и варианты; он может превышать размер выбранного workflow.

## Целевая система и статус проверки

По предоставленному владельцем выводу целевой DGX Spark — NVIDIA GB10, 128 ГБ системной unified memory по `MemTotal`, Ubuntu 24.04.5 LTS ARM64 и около 3,5 ТБ свободно. `nvidia-smi` не сообщает объём памяти (`N/A`). Docker daemon активен, но socket доступен обычному пользователю только через `sudo`.

Это **сведения владельца**, не независимый замер. По его решению модели пока не скачивались и не запускались. Ни одна строка ниже не означает, что модель установлена, загружена в память, обслуживает API или успешно генерирует результат.

NVIDIA публикует отдельные vLLM-рецепты для Spark на 64 и 128 ГБ; для указанной системы целевая инструкция — только 128-ГБ ветка.[20][65][66]

В 64-ГБ recipe указан image `vllm/vllm-openai:v0.28.0`.[65] В 128-ГБ launcher используется `nvcr.io/nvidia/vllm:26.10.pre1-py3`; runbook фиксирует digest `sha256:cb38bbefdbc3e9fe045f931dd72cbd58cd48985c7e09916bcc6c15c10f39b929`.[20][66]

## Приоритет внедрения: базовые кандидаты и отложенные компоненты

| Уровень | Компоненты | Условие выбора сейчас |
|---|---|---|
| Основной кандидат для coding API | `nvidia/Qwen3.8-27B-NVFP4` + `z-lab/Qwen3.8-27B-DFlash2` | Для 128-ГБ профиля документирован vLLM recipe; модели не скачивались, точная совместимость CLI NGC image и запуск на Spark не проверены.[20][66][68] |
| Кандидат на генерацию изображений | `Comfy-Org/z_image_turbo` BF16 bundle | Три BF16 файла и workflow зафиксированы; соответствие статически проверено, но модель не скачивалась и workflow на Spark не запускался.[67][79][93] |
| Опционально позже | FLUX.2 Klein 4B | Нужны конкретный сценарий, выбранные runtime/workflow и успешная E2E-проверка на целевой среде; совместимость Spark пока не подтверждена.[26][74][80] |
| Опционально позже | Qwen3-Embedding-0.6B и Qwen3-Reranker-0.6B | Не выбраны retrieval runtime, индекс и end-to-end процедура поиска/ранжирования; пока не устанавливать.[30][31][83] |
| Опционально позже | DeepSeek-OCR-2 | Пример из model card не подтверждает runtime на DGX Spark или end-to-end процедуру OCR.[33][84] |
| Опционально позже; не для коммерческого baseline | FLUX.2 Klein 9B | Точный checkpoint распространяется по FLUX Non-Commercial License; коммерческое/production-использование не разрешено. Для любого подходящего некоммерческого сценария потребуются отдельная проверка лицензии, выбранный runtime/workflow и сквозная проверка на целевой среде.[75][81][87] |
| Не подменять baseline автоматически | Z-Image INT8 / NVFP4 | Для вариантов нужны отдельные workflow и совместимые пары encoder; runtime на Spark не проверен.[72][94][102] |

| Точный checkpoint | Задача, runtime и память | Revision и место на диске | Лицензия | Подтверждение и статус |
|---|---|---|---|---|
| `nvidia/Qwen3.8-27B-NVFP4` — 27B, mixed NVFP4/FP8 | Coding/chat API через vLLM. 64-ГБ recipe: `vllm/vllm-openai:v0.28.0`; 128-ГБ target: `nvcr.io/nvidia/vllm:26.10.pre1-py3` с digest из runbook. Пользователь сообщил 128 ГБ unified memory; peak usage модели не измерялся | SHA `482ca0f3832238542f8f5295dde86b5f22711d80`; весь репозиторий 21.95 GB.[77] | Apache-2.0 для этого checkpoint.[13] | NVIDIA recipe и shell syntax проверены.[66] Qwen runbook фиксирует target revision; поддержка параметра в 128-ГБ image остаётся pending. На Spark не скачивался и не запускался. |
| `z-lab/Qwen3.8-27B-DFlash2` | Draft-модель для speculative decoding вместе с целевым Qwen; не самостоятельная чат-модель. Используется NVIDIA vLLM launcher; отдельный memory minimum не указан, учитывать как дополнительную нагрузку | SHA `50307d4c4cde6860d4eee73e2547cd786fe8e8a4`; весь репозиторий 3.85 GB.[78] | Apache-2.0.[68] | NVIDIA launcher использует checkpoint как draft.[66] Qwen runbook теперь закрепляет draft revision в загрузке и speculative config; support в 128-ГБ image pending. На Spark не скачивалась и не запускалась. |
| `Qwen/Qwen3-Embedding-0.6B` | Text embedding (`feature-extraction`); runtime и endpoint проекта не выбраны; отдельный Spark memory minimum в карточке не указан | SHA `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3`; репозиторий 1.21 GB; 0.6B, context 32K | Apache-2.0 | Задача/metadata проверены. Нет выбранного retrieval-сервера, индекса или end-to-end теста; не установлена.[30][82] |
| `Qwen/Qwen3-Reranker-0.6B` | Text ranking/reranking; отдельный компонент после поиска; runtime не выбран, отдельный Spark memory minimum в карточке не указан | SHA `e61197ed45024b0ed8a2d74b80b4d909f1255473`; весь репозиторий 1.21 GB; 0.6B, context 32K | Apache-2.0 | Карточка подтверждает ranking-задачу. Runtime/API и retrieval flow не выбраны; не установлен.[31][83] |

`nvidia/Qwen3.8-27B-NVFP4` — оптимизированный checkpoint; `Qwen/Qwen3.8-27B` — отдельный upstream base. Не подменяйте один другим в инструкциях или manifest.[13][85]

## Генерация и редактирование изображений

| Точный checkpoint / файл | Задача, runtime и память | Revision и место на диске | Лицензия | Подтверждение и статус |
|---|---|---|---|---|
| `Comfy-Org/z_image_turbo`: `z_image_turbo_bf16.safetensors` + `qwen_3_4b.safetensors` + `ae.safetensors` | Baseline Z-Image-Turbo text-to-image в ComfyUI: diffusion model + text encoder + VAE | SHA `6fc90a3b1b653e935a0d175e260736de25b84df5`; выбранные файлы около 20.69 GB (12.31 + 8.04 + 0.34 GB). Весь repo с альтернативами — 40.67 GB | Apache-2.0 у repackaged Comfy-Org repo | Именно эти файлы использует NVIDIA setup script для ComfyUI `v0.33.2`. Опубликованный script использует изменяемый `main`, но runbook фиксирует локальную копию на Hub snapshot; преобразование и model/workflow pairing статически проверены. Загрузки и генерации на Spark не было.[67][79][93] |
| `Comfy-Org/z_image_turbo`: `z_image_turbo_int8_convrot.safetensors` | Альтернативная INT8 diffusion weight для ComfyUI; paired encoder/workflow нужно выбирать совместно | Та же SHA `6fc90a3b1b653e935a0d175e260736de25b84df5`; diffusion-файл 6.20 GB; encoder/VAE отдельно | Apache-2.0 у Comfy-Org repo | Файл и отдельный INT8 workflow перечислены в карточке. NVIDIA Spark setup script этот вариант не загружает; workflow/loader и GB10 не тестировались.[72][79][94] |
| `Comfy-Org/z_image_turbo`: `z_image_turbo_nvfp4.safetensors` | Альтернативная NVFP4 diffusion weight; требуется совместимый encoder, loader и workflow | Та же SHA; diffusion-файл 4.51 GB; encoder/VAE отдельно | Apache-2.0 у Comfy-Org repo | Файл присутствует в pinned Hub snapshot, но в просмотренном `templates/` snapshot нет NVFP4 workflow; pairing encoder/loader не подтверждён. В baseline не включён; совместимость и память на Spark не проверялись.[72][79][102] |
| `Tongyi-MAI/Z-Image-Turbo` | Upstream 6B text-to-image модель, на которую ссылается repackaged Comfy-Org repo; это не repo весов, скачиваемый NVIDIA script | SHA `f332072aa78be7aecdf3ee76d5c247082da564a6`; весь репозиторий 32.90 GB | Apache-2.0 | Справочная upstream-модель. В проекте для baseline выбран Comfy-Org/NVIDIA набор файлов; upstream repo отдельно не скачивался.[25][86] |
| `black-forest-labs/FLUX.2-klein-4B`: Base и Distilled (4-step) — разные веса | ComfyUI text-to-image и image editing; использовать только workflow, соответствующий Base или Distilled файлу | SHA `e7b7dc27f91deacad38e78976d1f2b499d76a294`; полный repo с вариантами — 23.74 GB | Apache-2.0 | ComfyUI guide требует актуальный ComfyUI/workflow. BFL заявляет 13 GB VRAM для consumer hardware; guide приводит отдельные замеры на RTX 5090. Это не оценка Spark GB10; Spark-рецепта и теста нет.[26][74][80] |
| `black-forest-labs/FLUX.2-klein-9B`: Base и Distilled BF16 | ComfyUI text-to-image/editing; отдельные 9B веса и 8B Qwen text encoder | SHA `92196c8e11f7b6cf2b7493e037d8c5345c559216`; gated repo 52.89 GB; BFL заявляет около 29 GB VRAM | FLUX Non-Commercial License; требуется принять условия доступа. Не считать Apache-2.0; для коммерческого/production применения нужен отдельный разрешённый вариант | Отложен и не выбран. Лицензия ограничивает разрешённое использование non-commercial/non-production; runtime/workflow и сквозная проверка на Spark не выполнены.[75][81][87] |

Comfy-Org также перечисляет encoder-файлы `qwen_3_4b_fp4_mixed` (3.48 GB) и `qwen_3_4b_fp8_mixed` (5.63 GB), а также LoRA. Это не взаимозаменяемые файлы: применять их только по workflow, который указывает точные модели и узлы.[22][72][79]

**Ограничение по памяти:** upstream-карточка указывает 16 GB VRAM на consumer GPU; это не измерение пиковой unified-memory нагрузки Z-Image на GB10. Для INT8/NVFP4 в проверенных карточке и NVIDIA quick start не найдено Spark-specific memory/performance результата.[22][25][72]

## OCR

| Точный checkpoint | Задача, runtime и память | Revision и место на диске | Лицензия | Подтверждение и статус |
|---|---|---|---|---|
| `deepseek-ai/DeepSeek-OCR-2` | OCR/image-text-to-text; card sample uses Python 3.12.9, PyTorch 2.6.0, Transformers 4.46.3, CUDA 11.8 and FlashAttention 2.7.3; GB10 peak memory not specified | SHA `aaa02f3811945a91062062994c5c4a3f4c0af2b0`; весь repo 6.79 GB; 3B BF16 | Apache-2.0 | Metadata и пример проверены. Пример карточки не доказывает совместимость с DGX Spark/CUDA в этом проекте; отдельного Spark recipe и теста нет. Отложен.[33][84] |

## Инструменты и лицензии

| Компонент | Назначение | Лицензия/статус |
|---|---|---|
| Material Symbols / Lucide | Готовые векторные UI-иконки | Apache-2.0 / ISC соответственно; проверять условия выбранного набора.[45][46] |
| Android Image Asset Studio | Android launcher/notification assets | Инструмент Android Studio; сборка приложения на Spark не выполняется.[34] |
| Visual Studio asset tools | Windows app icons/assets | Отдельный Windows workflow; проект проверять на Windows.[35][36] |
| Mermaid / PlantUML / Graphviz | Текстовые диаграммы | Исходники хранить в Git и проверять выбранным renderer.[27][28][29] |
| DocFX / Dokka | .NET / Kotlin API-документация | Выбирать по фактическому языку и build pipeline приложения.[37][38] |

## Правила учёта

- SHA в таблице — Hub snapshots на 2026-10-31, не доказательство загрузки. Qwen runbook фиксирует target/draft revisions при скачивании и запуске.[77][78]
- ComfyUI runbook патчит локальную копию NVIDIA setup script на exact Z-Image snapshot и отдельно проверяет workflow pairing; это статическая проверка, не загрузка или runtime-тест.[67][79][93]
- Размеры — Hub metadata для полного репозитория, кроме явно отмеченного NVIDIA Z-Image baseline subset и отдельных diffusion-файлов. Они не учитывают контейнеры, runtime, временные файлы или возможные повторные загрузки.
- «Карточка проверена», «есть vendor recipe» и `bash -n` — разные уровни подтверждения; ни один из них не означает реальную установку или performance test.
- Публичная лицензия GitHub-репозитория не выбрана владельцем; файл `LICENSE` без его решения не добавлять.

## Sources

[13] https://huggingface.co/nvidia/Qwen3.8-27B-NVFP4
[20] https://build.nvidia.com/spark/vllm/intermediate
[22] https://build.nvidia.com/spark/comfyui/image-gen-quick-start
[25] https://huggingface.co/Tongyi-MAI/Z-Image-Turbo
[26] https://docs.comfy.org/tutorials/flux/flux-2-klein
[27] https://github.com/mermaid-js/mermaid
[28] https://plantuml.com/en
[29] https://graphviz.org/doc/info/lang.html
[30] https://huggingface.co/Qwen/Qwen3-Embedding-0.6B
[31] https://huggingface.co/Qwen/Qwen3-Reranker-0.6B
[33] https://huggingface.co/deepseek-ai/DeepSeek-OCR-2
[34] https://developer.android.com/studio/write/image-asset-studio
[35] https://learn.microsoft.com/en-us/windows/apps/design/iconography/app-icon-construction
[36] https://learn.microsoft.com/en-us/windows/apps/design/style/iconography/visual-studio-asset-generation
[37] https://dotnet.github.io/docfx/docs/dotnet-api-docs.html
[38] https://kotlinlang.org/docs/dokka-introduction.html
[45] https://fonts.google.com/icons
[46] https://lucide.dev/license
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
[85] https://huggingface.co/api/models/Qwen/Qwen3.8-27B?blobs=true
[86] https://huggingface.co/api/models/Tongyi-MAI/Z-Image-Turbo?blobs=true
[87] https://huggingface.co/black-forest-labs/FLUX.2-klein-9B/blob/main/LICENSE.md
[93] https://raw.githubusercontent.com/Comfy-Org/workflow_templates/c067929d7e9cc0f3fd15be348fa1a1d85da15946/templates/image_z_image_turbo.json
[94] https://raw.githubusercontent.com/Comfy-Org/workflow_templates/c067929d7e9cc0f3fd15be348fa1a1d85da15946/templates/image_z_image_turbo_int8.json
[102] https://github.com/Comfy-Org/workflow_templates/tree/c067929d7e9cc0f3fd15be348fa1a1d85da15946/templates
