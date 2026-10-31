# ComfyUI + Z-Image-Turbo на DGX Spark

> **Статус:** это runbook, а не отчёт об установленной системе. По переданным владельцем данным Spark — GB10/128 ГБ, Ubuntu 24.04.5 ARM64; установка, загрузка весов и генерация изображения не выполнялись. Аппаратная проверка остаётся **pending**.

## Что покрывает руководство

Официальный NVIDIA setup использует host-Python, PyTorch с CUDA 13.0, ComfyUI `v0.33.2` и BF16 bundle из трёх файлов объёмом около 20.69 GB.[49][67][79] Он не использует Docker, поэтому не зависит от прав на Docker socket.

Исходный setup script закреплён на commit NVIDIA playbook, но его Hugging Face URL использует изменяемый `main`. Ниже инструкция изменяет только локальную копию: фиксирует Z-Image snapshot, включает возобновляемую загрузку и проверяет SHA-256 файлов. Эти операции описаны, но не выполнялись на Spark.[67][79][97]

## Требования к диску и общей памяти

- **Диск:** три BF16-файла baseline занимают 20.69 GB (12.31 GB diffusion, 8.04 GB encoder, 0.34 GB VAE) по metadata закреплённого Hub snapshot.[79] Это только веса: Python environment, PyTorch/ComfyUI dependencies, кэш и output занимают дополнительное место, а общий объём установки здесь не измерен. Перед setup и после него проверьте filesystem установки через `df -h "$HOME"`; не начинайте, если доступное место едва покрывает только веса.
- **Unified memory:** по снимку владельца Spark имеет 128 ГБ, но это не измерение ComfyUI peak memory. Размер safetensors на диске не равен памяти при инференсе; в просмотренных источниках нет валидированного peak-memory результата для этого workflow на GB10.[16][22][25]
- Перед генерацией остановите Qwen/vLLM и освободите его контейнер; не считайте несколько сохранённых на SSD моделей одновременно пригодными к запуску.[16][22]

## Перед установкой

Проверьте систему на самом Spark:

```bash
uname -m
cat /etc/os-release
nvidia-smi
free -h
df -h "$HOME"
python3 --version
git --version
```

Для Z-Image оставьте запас общей памяти: DGX Spark использует unified memory, а запущенный vLLM будет конкурировать за неё. Остановите Qwen и освободите его контейнер перед запуском ComfyUI.[16][22]

NVIDIA setup script сохраняет веса внутри `ComfyUI/models/` в каталоге установки. Планируемый общий каталог `/srv/ai/models/comfyui` этим скриптом автоматически не используется; на первом этапе не создавайте дубликаты и не переносите веса символическими ссылками без отдельной проверки.[67]

## Установка

Следующие команды **не выполнялись**. Сначала проверьте свободное место на filesystem установки и выделите новую папку, чтобы скрипт не использовал случайные существующие `comfyui-env/` или `ComfyUI/`:

```bash
mkdir -p "$HOME/dgx-spark/comfyui-zimage"
cd "$HOME/dgx-spark/comfyui-zimage"

SCRIPT_URL='https://raw.githubusercontent.com/NVIDIA/dgx-spark-playbooks/30883150541743d580c9c347700c6ac99fc396d2/nvidia/playbook-comfyui/assets/setup.sh'
curl -fL --retry 3 -o setup.vendor.sh "$SCRIPT_URL"
printf '%s  %s\n' \
  'd4d456d9d09901a53fdc33e12acab7387fdfb1b5050f00a93ed9c91a09cfd728' \
  setup.vendor.sh | sha256sum -c -
bash -n setup.vendor.sh
less setup.vendor.sh
cp -- setup.vendor.sh setup.sh
bash -n setup.sh
```

Опубликованный setup script закреплён на commit NVIDIA playbook, но download base в нём указывает на изменяемый `main`. Измените только локальную копию, чтобы ссылки на веса использовали Hub snapshot из матрицы, а все три загрузки могли возобновляться. Преобразование остановится, если структура vendor script отличается:

```bash
python3 - setup.sh <<'PY'
from pathlib import Path

p = Path("setup.sh")
s = p.read_text()
old_base = "BASE=https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files"
new_base = "BASE=https://huggingface.co/Comfy-Org/z_image_turbo/resolve/6fc90a3b1b653e935a0d175e260736de25b84df5/split_files"
old_flag = "wget -nc -P"
if s.count(old_base) != 1 or s.count(old_flag) != 3:
    raise SystemExit("Unexpected NVIDIA setup script; no change written")
s = s.replace(old_base, new_base, 1).replace(old_flag, "wget -c -P")
p.write_text(s)
PY
bash -n setup.sh
grep -nE 'BASE=|wget -c' setup.sh
```

Это локальная модификация, а не неизменённый NVIDIA script. Перед дальнейшими действиями осмотрите правки и повторно проверьте синтаксис. Патч сохраняет host-Python setup, PyTorch и ComfyUI `v0.33.2`, но скачивает BF16 diffusion model, encoder и VAE из закреплённого snapshot `6fc90a3b…`. Около 20.69 GB — только baseline-веса; runtime-пакеты и кэш потребуют дополнительного места.[67][79]

Следующая команда устанавливает окружение и скачивает веса. **Выполнять только после отдельного разрешения владельца; сейчас она не запускалась:**

```bash
bash setup.sh
```

GNU Wget `-c` (`--continue`) возобновляет частичный файл, когда сервер поддерживает byte ranges. Если загрузка прервётся, не запускайте весь installer повторно вслепую: повторите только неудавшуюся загрузку с тем же pinned URL, затем выполните SHA-256 проверки ниже.[97]

Для ручного восстановления из каталога `ComfyUI` задайте тот же snapshot и выполните только строки для отсутствующих/неполных файлов:

```bash
cd "$HOME/dgx-spark/comfyui-zimage/ComfyUI"
BASE='https://huggingface.co/Comfy-Org/z_image_turbo/resolve/6fc90a3b1b653e935a0d175e260736de25b84df5/split_files'
wget -c -P models/diffusion_models "$BASE/diffusion_models/z_image_turbo_bf16.safetensors"
wget -c -P models/text_encoders "$BASE/text_encoders/qwen_3_4b.safetensors"
wget -c -P models/vae "$BASE/vae/ae.safetensors"
```

После завершения проверьте расположение и примерный размер файлов:

```bash
cd "$HOME/dgx-spark/comfyui-zimage"
find ComfyUI/models -maxdepth 2 -type f -printf '%p %s bytes\n'
du -sh ComfyUI/models
df -h "$HOME"
```

Проверьте имена, размеры и контрольные суммы файлов baseline. SHA-256 values соответствуют Hub snapshot `6fc90a3b…`; вычисление хешей прочитает около 20.69 GB и может занять время.[79]

```bash
cd "$HOME/dgx-spark/comfyui-zimage/ComfyUI"
sha256sum -c - <<'SHA256'
2407613050b809ffdff18a4ac99af83ea6b95443ecebdf80e064a79c825574a6  models/diffusion_models/z_image_turbo_bf16.safetensors
6c671498573ac2f7a5501502ccce8d2b08ea6ca2f661c458e708f36b36edfc5a  models/text_encoders/qwen_3_4b.safetensors
afc8e28272cd15db3919bacdb6918ce9c1ed22e96cb12c4d5ed0fba823529e38  models/vae/ae.safetensors
SHA256
```

Если checksum не совпадает или файл отсутствует, остановитесь и не используйте bundle; проверьте частичную загрузку и повторите только соответствующий pinned download, затем повторите все hash checks.[67][79]

## Сверка версии ComfyUI и workflow

Pinned ComfyUI `v0.33.2` соответствует commit `7cee3ceb1a35503172e0dfb8dbdbdedee2aba8aa`; эта версия требует Python `>=3.10`.[98][100] Её `requirements.txt` фиксирует frontend package `1.49.6` и workflow-template package `0.11.43`.[99]

Pinned BF16 workflow JSON имеет format `0.4`, указывает `frontendVersion` `1.42.15` и core-node metadata `0.3.64`/`0.3.73`; requirements setup-рецепта фиксируют frontend package `1.49.6`, численно новее версии в workflow metadata; это только статическое сравнение, не подтверждение успешного импорта или генерации.[93][99] В будущем тесте используйте именно pinned JSON и запишите фактический результат; при ошибке version/node остановитесь и не подменяйте веса. Встроенные model links в JSON всё ещё указывают на `resolve/main`; не скачивайте по ним, используйте pinned URL из runbook.[67][79][93]

## Варианты Z-Image и совместимость workflow

| Вариант | Пара файлов из карточки/workflow | Статус в этом runbook |
| --- | --- | --- |
| **BF16 baseline** | `z_image_turbo_bf16.safetensors` + `qwen_3_4b.safetensors` + `ae.safetensors` | Совпадает с NVIDIA setup и официальным `image_z_image_turbo.json`; это единственный baseline ниже. Шаблон загружайте после проверки, что эти три pinned-файла уже лежат в соответствующих каталогах.[67][79][93] |
| **INT8** | `z_image_turbo_int8_convrot.safetensors` + `qwen_3_4b_fp8_mixed.safetensors` + `ae.safetensors` | Отдельный `image_z_image_turbo_int8.json` называет именно INT8 diffusion и FP8 encoder. NVIDIA baseline script их не ставит; совместимость workflow с закреплённым ComfyUI tag и GB10 остаётся непроверенной. Не заменять BF16-файл или encoder по отдельности.[72][79][94] |
| **NVFP4** | `z_image_turbo_nvfp4.safetensors` (и отдельно выбранные encoder/VAE) | Файл присутствует в Hub snapshot.[79] В просмотренном pinned `templates/` snapshot нет отдельного NVFP4 workflow; matching pairing/loader не подтверждён, поэтому вариант не входит в baseline и не тестировался.[72][102] |

2K upscaler и Fun Union ControlNet — отдельные workflow, не quantized substitutes: upscaler использует BF16 baseline плюс дополнительный upscale model; Fun Union добавляет отдельный ControlNet/model patch. Они не входят в первый baseline и требуют собственной проверки файлов, узлов и памяти.[95][96]

Другие FP4/FP8 encoder-файлы и LoRA также являются отдельными компонентами. Подключайте их только если конкретный workflow перечисляет точные файлы; наличие файла в репозитории не доказывает совместимость.[72][94]

Полная сводка checkpoint, ревизий, размеров и лицензий находится в [технической матрице](./model-and-license-matrix.md); фактический статус установки и тестов — в [матрице валидации](./validation-status.md).

## Запуск только на loopback

Не используйте `--listen 0.0.0.0` для этого сценария: это открывает web UI на сетевых интерфейсах. ComfyUI поддерживает явные `--listen` и `--port`; для локального SSH-туннеля укажите loopback.[49][101]

```bash
cd "$HOME/dgx-spark/comfyui-zimage"
source comfyui-env/bin/activate
cd ComfyUI
python main.py --listen 127.0.0.1 --port 8188
```

В другом терминале на Spark проверьте HTTP-ответ:

```bash
curl --fail-with-body -I http://127.0.0.1:8188
```

На Windows откройте PowerShell и введите адрес и имя пользователя, настроенные владельцем:

```powershell
$sparkUser = Read-Host 'Имя пользователя на Spark'
$sparkAddress = Read-Host 'IP-адрес или SSH alias Spark'
ssh -N -L 8188:127.0.0.1:8188 "$sparkUser@$sparkAddress"
```

Пока туннель активен, откройте `http://localhost:8188`. Не закрывайте окно SSH во время работы с интерфейсом.

## Smoke test — выполнить только после отдельного разрешения владельца

1. Загрузите закреплённый BF16 workflow [`image_z_image_turbo.json`](https://raw.githubusercontent.com/Comfy-Org/workflow_templates/c067929d7e9cc0f3fd15be348fa1a1d85da15946/templates/image_z_image_turbo.json) в ComfyUI через импорт JSON; не используйте изменяемую ссылку `main`.[93]
2. Убедитесь, что workflow выбирает `z_image_turbo_bf16.safetensors`, `qwen_3_4b.safetensors` и `ae.safetensors`; это baseline-пара, проверенная выше.
3. Если UI сообщает о missing model, missing node или несовместимом workflow, остановитесь: не подменяйте BF16 на INT8/NVFP4 и не устанавливайте дополнительные узлы без отдельной проверки.
4. Запустите короткий prompt и дождитесь полного завершения workflow.
5. Убедитесь, что изображение сохранено в `ComfyUI/output/`; запишите дату, ComfyUI revision, имя workflow, snapshot/checksum моделей, время генерации, использование памяти и обезличенный результат.
6. После теста остановите сервер через `Ctrl+C` и проверьте использование памяти.

HTTP-ответ `200` подтверждает только доступность web-сервера; он не доказывает успешную загрузку модели или генерацию изображения. Успешная генерация на 128-ГБ Spark останется **pending**, пока этот тест реально не выполнен.

## Остановка и удаление

Остановите ComfyUI `Ctrl+C` в терминале запуска, затем выполните `deactivate`. Не удаляйте каталоги, если в них есть другие файлы. Если владелец решит полностью удалить эту отдельную установку, сначала сверьте путь:

```bash
printf 'Установка: %s\n' "$HOME/dgx-spark/comfyui-zimage"
```

Удаление каталога — необратимая операция и не требуется для обычной остановки; в этой ревизии команда удаления намеренно не включена.

## Sources

[16] https://docs.nvidia.com/dgx/dgx-spark/hardware.html
[22] https://build.nvidia.com/spark/comfyui/image-gen-quick-start
[25] https://huggingface.co/Tongyi-MAI/Z-Image-Turbo
[49] https://build.nvidia.com/playbooks/comfyui/image-gen-quick-start.md
[67] https://raw.githubusercontent.com/NVIDIA/dgx-spark-playbooks/30883150541743d580c9c347700c6ac99fc396d2/nvidia/playbook-comfyui/assets/setup.sh
[72] https://huggingface.co/Comfy-Org/z_image_turbo
[79] https://huggingface.co/api/models/Comfy-Org/z_image_turbo?blobs=true
[93] https://raw.githubusercontent.com/Comfy-Org/workflow_templates/c067929d7e9cc0f3fd15be348fa1a1d85da15946/templates/image_z_image_turbo.json
[94] https://raw.githubusercontent.com/Comfy-Org/workflow_templates/c067929d7e9cc0f3fd15be348fa1a1d85da15946/templates/image_z_image_turbo_int8.json
[95] https://raw.githubusercontent.com/Comfy-Org/workflow_templates/c067929d7e9cc0f3fd15be348fa1a1d85da15946/templates/utility_z_image_turbo_2k_upscaler.app.json
[96] https://raw.githubusercontent.com/Comfy-Org/workflow_templates/c067929d7e9cc0f3fd15be348fa1a1d85da15946/templates/image_z_image_turbo_fun_union_controlnet.json
[97] https://www.gnu.org/software/wget/manual/wget.html
[98] https://raw.githubusercontent.com/Comfy-Org/ComfyUI/7cee3ceb1a35503172e0dfb8dbdbdedee2aba8aa/comfyui_version.py
[99] https://raw.githubusercontent.com/Comfy-Org/ComfyUI/7cee3ceb1a35503172e0dfb8dbdbdedee2aba8aa/requirements.txt
[100] https://raw.githubusercontent.com/Comfy-Org/ComfyUI/7cee3ceb1a35503172e0dfb8dbdbdedee2aba8aa/pyproject.toml
[101] https://raw.githubusercontent.com/Comfy-Org/ComfyUI/7cee3ceb1a35503172e0dfb8dbdbdedee2aba8aa/comfy/cli_args.py
[102] https://github.com/Comfy-Org/workflow_templates/tree/c067929d7e9cc0f3fd15be348fa1a1d85da15946/templates
