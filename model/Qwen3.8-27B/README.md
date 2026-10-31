# Qwen3.8-27B на DGX Spark: установка, API и Hermes

> **Статус:** это runbook, не отчёт об установке. По данным владельца целевой Spark — GB10/128 ГБ, Ubuntu 24.04.5 ARM64; `nvidia-smi` показывает память как `N/A`, а Docker socket доступен пользователю только через `sudo`. Владелец пока запретил скачивать и запускать модели; команды ниже не выполнялись.

## Что устанавливает этот runbook

- Основной checkpoint: `nvidia/Qwen3.8-27B-NVFP4`, mixed NVFP4/FP8, Hub snapshot `482ca0f3832238542f8f5295dde86b5f22711d80`.[13][77]
- Draft checkpoint: `z-lab/Qwen3.8-27B-DFlash2`, Hub snapshot `50307d4c4cde6860d4eee73e2547cd786fe8e8a4`; это вспомогательная модель для speculative decoding, не отдельный чат-сервер.[66][68][78]
- Для целевого 128-ГБ профиля применяется NVIDIA vLLM launcher и соответствующий image; 64-ГБ вариант ниже оставлен только как отдельная справочная ветка.[20][66]
- API по умолчанию слушает только `127.0.0.1:8000`; с Windows подключайтесь через SSH-туннель, не открывая сервис в LAN.[20]

Сравнение вариантов, размеры и лицензии находятся в [технической матрице](../../docs/model-and-license-matrix.md). SHA выше — snapshot на 2026-10-31; в следующих командах он будет использован явно, а не разрешён через `main`.

## 1. Подготовить DGX Spark

### 1.1 Подключиться и проверить устройство

Подключитесь к Spark по уже настроенному SSH или через NVIDIA Sync и откройте терминал. Выполните read-only preflight на самом устройстве; не публикуйте hostname, username или секреты.

```bash
uname -m
cat /etc/os-release
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
grep -E 'MemTotal|MemAvailable' /proc/meminfo
free -h
findmnt -T /srv
df -h /srv "$HOME"
id
stat -c '%A %U:%G %n' /var/run/docker.sock
docker version
sudo docker info --format '{{.ServerVersion}}'
sudo docker ps -a
```

Для этого владельца `MemTotal` указывает на 128-ГБ систему, а `nvidia-smi` возвращает `N/A` для объёма памяти. Используйте 128-ГБ ветку; если повторный вывод отличается, остановитесь и перепроверьте профиль перед любым запуском.

Обычный пользователь не имеет доступа к Docker socket; `sudo docker info` работает. Не добавляйте пользователя в группу `docker` автоматически: это уровень привилегий root. Ручной сценарий ниже использует `sudo`; NVIDIA Sync Custom App в текущем профиле нельзя считать доступным без отдельного решения о Docker-доступе.[20]

Убедитесь, что `/srv` находится на SSD с достаточным свободным местом. Если `/srv/ai` уже существует, сначала осмотрите его — не меняйте владельца рекурсивно и не удаляйте содержимое. NVIDIA публикует отдельные image и launcher для 64 и 128 ГБ; используйте только соответствующую ветку.[20][65][66]

### 1.2 Создать каталог, только если его ещё нет

```bash
for p in \
  /srv/ai/apps/vllm \
  /srv/ai/config \
  /srv/ai/models/huggingface/hub \
  /srv/ai/cache/vllm \
  /srv/ai/cache/flashinfer \
  /srv/ai/cache/triton \
  /srv/ai/cache/torch \
  /srv/ai/cache/xdg \
  /srv/ai/cache/runtime \
  /srv/ai/tmp \
  /srv/ai/logs \
  /srv/ai/manifests; do
  if [ -d "$p" ]; then
    printf 'Уже есть: %s\n' "$p"
  elif [ -e "$p" ] || [ -L "$p" ]; then
    printf 'Путь существует, но это не каталог: %s\n' "$p" >&2
    exit 1
  else
    sudo install -d -m 0755 -o "$(id -un)" -g "$(id -gn)" "$p"
  fi
done
```

Если папка уже существовала, проверьте недостающие подкаталоги и создайте только их после осмотра. Проверьте результат и владельца:

```bash
stat -c '%U:%G %A %n' /srv/ai /srv/ai/models /srv/ai/models/huggingface
df -h /srv/ai
```

### 1.3 Задать постоянные пути

Создайте файл без секретов; он задаёт один каталог для Hugging Face Hub и отдельное место для временных файлов:

```bash
cat > /srv/ai/config/paths.sh <<'EOF'
export AI_ROOT=/srv/ai
export HF_HOME="$AI_ROOT/models/huggingface"
export HF_HUB_CACHE="$HF_HOME/hub"
export TMPDIR="$AI_ROOT/tmp"
export QWEN_REV=482ca0f3832238542f8f5295dde86b5f22711d80
export DRAFT_REV=50307d4c4cde6860d4eee73e2547cd786fe8e8a4
EOF
chmod 0644 /srv/ai/config/paths.sh
source /srv/ai/config/paths.sh
printf 'HF_HOME=%s\nHF_HUB_CACHE=%s\nTMPDIR=%s\n' "$HF_HOME" "$HF_HUB_CACHE" "$TMPDIR"
df -h "$HF_HOME" "$TMPDIR"
```

Не задавайте `HF_HOME` и `HF_HUB_CACHE` на разные несвязанные корни: официальный launcher монтирует `HF_HOME` внутрь контейнера как `/root/.cache/huggingface`. С указанными значениями `hf download` и vLLM используют один и тот же каталог моделей.[65][66]

Если `hf` не найден, установите официальный standalone CLI Hugging Face и откройте новый терминал:[20][53]

```bash
curl -LsSf https://hf.co/cli/install.sh | bash -s -- --exclude-skill
hf --help
```

Указанные ниже модели публичные; не добавляйте токены в командную строку или Git.

## 2. Установить Qwen3.8-27B

Сначала проверьте место на файловой системе, где расположен `HF_HOME`:

```bash
source /srv/ai/config/paths.sh
df -h "$HF_HOME"

printf 'Qwen revision: %s\nDFlash2 revision: %s\n' "$QWEN_REV" "$DRAFT_REV"
```

### Ветка A — DGX Spark 64 ГБ

```bash
sudo docker pull vllm/vllm-openai:v0.28.0
hf download nvidia/Qwen3.8-27B-NVFP4 --revision "$QWEN_REV"
hf download z-lab/Qwen3.8-27B-DFlash2 --revision "$DRAFT_REV"
df -h "$HF_HOME"
```

Это соответствующие NVIDIA image и checkpoint IDs для 64-ГБ рецепта.[20][65]

### Ветка B — DGX Spark 128 ГБ

Если `sudo docker pull` вернёт `unauthorized`, выполните интерактивную авторизацию в NGC самостоятельно. Docker сохранит учётные данные в root Docker config; не вставляйте API key в runbook, Git или чат. После успешной загрузки при желании очистите сохранённую авторизацию командой `sudo docker logout nvcr.io`.

```bash
# Только если `sudo docker pull` отвечает unauthorized:
sudo docker login nvcr.io

# Image digest из таблицы официального NVIDIA-рецепта:
sudo docker pull nvcr.io/nvidia/vllm:26.10.pre1-py3@sha256:cb38bbefdbc3e9fe045f931dd72cbd58cd48985c7e09916bcc6c15c10f39b929
hf download nvidia/Qwen3.8-27B-NVFP4 --revision "$QWEN_REV"
hf download z-lab/Qwen3.8-27B-DFlash2 --revision "$DRAFT_REV"
df -h "$HF_HOME"
```

Draft checkpoint необходим выбранному DFlash2 speculative-decoding launch-скрипту. Он не заменяет основной Qwen checkpoint.[20][66][68]

Проверьте, что в Hub cache появились именно требуемые snapshots, а не только каталоги с именами моделей:

```bash
for spec in \
  "models--nvidia--Qwen3.8-27B-NVFP4:$QWEN_REV" \
  "models--z-lab--Qwen3.8-27B-DFlash2:$DRAFT_REV"; do
  repo_cache=${spec%%:*}
  revision=${spec#*:}
  snapshot="$HF_HUB_CACHE/$repo_cache/snapshots/$revision"
  if [ ! -d "$snapshot" ]; then
    printf 'Не найден требуемый snapshot: %s\n' "$snapshot" >&2
    exit 1
  fi
  du -sh "$snapshot"
done
```

Hugging Face управляет структурой `hub`; не переименовывайте его snapshot/blob-файлы и не держите вторую копию тех же весов через `--local-dir`.[65][66]

## 3. Настроить DGX Spark как локальный inference-сервер

Вендорские скрипты слушают только `127.0.0.1:8000`, включают Qwen tool-call parser и управляют временем жизни контейнера через NVIDIA Sync.[20][65][66] Для этого сценария не меняйте bind на `0.0.0.0` и не открывайте порт 8000 наружу.

### 3.1 Загрузить pinned launch-скрипт и добавить пути хранения

Скрипты ниже взяты из одной проверенной ревизии playbook. Так инструкция не зависит от плавающей ветки `main`:

```bash
NVIDIA_PLAYBOOK_REV=30883150541743d580c9c347700c6ac99fc396d2
mkdir -p /srv/ai/apps/vllm
```

Для **64 ГБ**:

```bash
SCRIPT=/srv/ai/apps/vllm/launch-qwen-64gb.sh
curl -fL \
  "https://raw.githubusercontent.com/NVIDIA/dgx-spark-playbooks/${NVIDIA_PLAYBOOK_REV}/nvidia/playbook-vllm/assets/sync-vllm-spark-64gb-qwen38-27b.sh" \
  -o "$SCRIPT"
```

Для **128 ГБ**:

```bash
SCRIPT=/srv/ai/apps/vllm/launch-qwen-128gb.sh
curl -fL \
  "https://raw.githubusercontent.com/NVIDIA/dgx-spark-playbooks/${NVIDIA_PLAYBOOK_REV}/nvidia/playbook-vllm/assets/sync-vllm-spark-128gb-qwen38-27b.sh" \
  -o "$SCRIPT"
```

После выбора одной ветки модифицируйте **только скачанную локальную копию** launcher: source paths, целевой checkpoint revision и draft revision. Сохраните vendor script отдельно; скрипт ниже прекращает работу при неожиданной структуре.

```bash
python3 - "$SCRIPT" "$QWEN_REV" "$DRAFT_REV" <<'PY'
from pathlib import Path
import json
import sys

p = Path(sys.argv[1])
qwen_rev, draft_rev = sys.argv[2:]
s = p.read_text()

marker = "set -euo pipefail\n"
if s.count(marker) != 1 or "source /srv/ai/config/paths.sh" in s:
    raise SystemExit("Неожиданный launcher/повторная модификация; файл не изменён")
s = s.replace(marker, marker + "source /srv/ai/config/paths.sh\n", 1)

target = "vllm serve nvidia/Qwen3.8-27B-NVFP4 " + chr(92) + "\n"
if s.count(target) != 1:
    raise SystemExit("Не найден ровно один target vllm serve; файл не изменён")
s = s.replace(target, target + "    --revision " + qwen_rev + " " + chr(92) + "\n", 1)

lines = s.splitlines()
indices = [i for i, line in enumerate(lines) if "--speculative-config " in line]
if len(indices) != 1:
    raise SystemExit("Не найден ровно один --speculative-config; файл не изменён")
i = indices[0]
prefix, payload = lines[i].split("--speculative-config ", 1)
payload = payload.strip()
continued = payload.endswith(chr(92))
if continued:
    payload = payload[:-1].rstrip()
if len(payload) < 2 or payload[0] != "'" or payload[-1] != "'":
    raise SystemExit("Неожиданное shell quoting speculative config; файл не изменён")
config = json.loads(payload[1:-1])
if config.get("model") != "z-lab/Qwen3.8-27B-DFlash2":
    raise SystemExit("Draft model ID не совпадает с ожидаемым; файл не изменён")
if config.get("revision") not in (None, draft_rev):
    raise SystemExit("В launcher уже задана другая draft revision; файл не изменён")
config["revision"] = draft_rev
new_payload = "'" + json.dumps(config, separators=(",", ":")) + "'"
if continued:
    new_payload += " " + chr(92)
lines[i] = prefix + "--speculative-config " + new_payload
s = "\n".join(lines) + ("\n" if s.endswith("\n") else "")

if p.name.endswith("128gb.sh"):
    image = "nvcr.io/nvidia/vllm:26.10.pre1-py3"
    digest = image + "@sha256:cb38bbefdbc3e9fe045f931dd72cbd58cd48985c7e09916bcc6c15c10f39b929"
    if s.count(image) != 1:
        raise SystemExit("128-ГБ image tag не найден ровно один раз; файл не изменён")
    s = s.replace(image, digest, 1)

p.write_text(s)
PY
```

Target model revision задаётся через `--revision`; vLLM 0.28 документирует отдельное поле `revision` для draft-модели в `--speculative-config`.[88][89] 128-ГБ NGC image не запускался в этой работе; после отдельного разрешения перед стартом проверьте внутри выбранного image, что `vllm serve --help` принимает `--revision` и draft `revision`. Если аргументы не распознаются, остановитесь и не запускайте неприкреплённую модель.

После изменения проверьте скрипт и параметры:

```bash
bash -n "$SCRIPT"
grep -nE 'HF_HOME|HF_CACHE_DIR|127\.0\.0\.1|--revision|speculative-config|vllm serve|docker rm -f' "$SCRIPT"
```

Скрипт удаляет контейнер с конкретным именем `vllm-spark-...-qwen38-27b` перед созданием нового. До запуска проверьте существующие контейнеры через `sudo docker ps -a`; не запускайте его, если в системе есть важный контейнер с этим именем.[65][66]

### 3.2 Разложить временные runtime-кэши

У 64-ГБ launcher host-кэши vLLM, FlashInfer и Triton по умолчанию находятся в `$HOME`. Если это новые каталоги, их можно направить в `/srv/ai/cache`. Сначала убедитесь, что целевые пути отсутствуют; уже существующие каталоги не перезаписывайте и не удаляйте:

```bash
for p in "$HOME/.cache/vllm" "$HOME/.cache/flashinfer" "$HOME/.triton"; do
  if [ -e "$p" ] || [ -L "$p" ]; then
    printf 'Уже существует, сначала осмотрите: %s\n' "$p"
    exit 1
  fi
done
mkdir -p /srv/ai/cache/vllm /srv/ai/cache/flashinfer /srv/ai/cache/triton \
  "$HOME/.cache"
ln -s /srv/ai/cache/vllm "$HOME/.cache/vllm"
ln -s /srv/ai/cache/flashinfer "$HOME/.cache/flashinfer"
ln -s /srv/ai/cache/triton "$HOME/.triton"
```

Для 128-ГБ скрипта **не** создавайте эти ссылки без причины: его комментарий требует сохранить prebuilt kernel/autotune cache внутри image; скрипт монтирует только Hugging Face cache.[66]

### 3.3 Docker-доступ для этого устройства

По сообщённым владельцем правам обычный пользователь не может обращаться к Docker socket без `sudo`. Поэтому в этом runbook основной путь — ручной запуск launcher через `sudo bash` и SSH-туннель. **Не** добавляйте пользователя в группу `docker` автоматически: это привилегии уровня root.

NVIDIA Sync Custom App может запускать этот Docker launcher только при наличии доступа к Docker daemon. Не настраивайте Custom App и не принимайте предложение добавить пользователя в группу без отдельного решения владельца. До такого решения используйте только описанный ниже условный ручной путь; на Spark он не запускался.

## 4. Подключить Windows-ПК по SSH-туннелю

Поскольку для текущего аккаунта Docker доступен только через `sudo`, ручной запуск и обычный SSH-туннель — основной путь. В PowerShell на Windows оставьте это окно открытым; замените placeholders на адрес и имя учётной записи, настроенной владельцем:

```powershell
$sparkUser = Read-Host 'Имя пользователя на Spark'
$sparkAddress = Read-Host 'IP-адрес или SSH alias Spark'
ssh -N -L 8000:127.0.0.1:8000 "$sparkUser@$sparkAddress"
```

Не публикуйте адрес/имя устройства в Git или логах. Не запускайте два туннеля на один локальный порт. vLLM слушает loopback; SSH перенаправляет локальный порт, не открывая API в LAN.[20][65][66]

NVIDIA Sync forwarding остаётся необязательным вариантом только после того, как владелец отдельно выберет безопасный способ дать Sync доступ к Docker. Добавление в группу `docker` не выполнять автоматически.

## 5. Запустить Qwen и проверить API

**На целевом 128-ГБ Spark запускайте только эту ветку.** Все команды в разделах загрузки и запуска намеренно не выполняются в текущем этапе: владелец разрешил завершить документы, но пока запретил установку моделей. При отдельном разрешении сначала осмотрите контейнеры и запускайте только локальную копию pinned launcher.

```bash
sudo docker ps -a
source /srv/ai/config/paths.sh
sudo bash /srv/ai/apps/vllm/launch-qwen-128gb.sh
```

`sudo` нужен для текущих прав Docker socket. Не добавляйте пользователя в группу `docker`. После запуска оставьте этот терминал открытым: `Ctrl+C` завершит launcher, а его cleanup остановит и удалит созданный им контейнер.

Только если фактическая система окажется 64-ГБ конфигурацией, используйте её отдельный скрипт вместо 128-ГБ; не запускайте обе ветки подряд:

```bash
sudo docker ps -a
source /srv/ai/config/paths.sh
sudo bash /srv/ai/apps/vllm/launch-qwen-64gb.sh
```

Для просмотра журналов откройте второй терминал Spark:

```bash
# 128 ГБ (целевой профиль)
sudo docker logs --tail 50 --follow vllm-spark-128gb-qwen38-27b

# Только для отдельной 64-ГБ конфигурации
sudo docker logs --tail 50 --follow vllm-spark-64gb-qwen38-27b
```

Дождитесь сообщения о готовности vLLM. 128-ГБ image ещё не запускался на устройстве владельца; команда выше — инструкция на будущее, не результат теста. Затем проверьте API **на Spark**:

```bash
curl --fail-with-body -i http://127.0.0.1:8000/health
curl --fail-with-body -sS http://127.0.0.1:8000/v1/models
```

В PowerShell на Windows после установления SSH-туннеля проверьте доступность API и отправьте короткий запрос:

```powershell
$models = Invoke-RestMethod http://127.0.0.1:8000/v1/models
$models.data | Select-Object id
$modelId = $models.data[0].id
$body = @{
  model = $modelId
  messages = @(@{ role = 'user'; content = 'Ответь одной фразой: локальный сервер работает?' })
  max_tokens = 64
} | ConvertTo-Json -Depth 6
Invoke-RestMethod http://127.0.0.1:8000/v1/chat/completions `
  -Method Post -ContentType 'application/json' -Body $body
```

Для остановки нажмите `Ctrl+C` в терминале, где запущен `sudo bash .../launch-qwen-128gb.sh`; launcher обработает сигнал и остановит/удалит созданный им контейнер. После остановки проверьте `sudo docker ps -a`.[65][66]

## 6. Подключить модель к Hermes на Windows

Сначала убедитесь, что SSH-туннель работает и `Invoke-RestMethod http://127.0.0.1:8000/v1/models` возвращает список. Возьмите точный `id` из этого ответа; не подставляйте имя наугад.

В PowerShell на ПК запустите мастер:

```powershell
hermes model
```

В мастере выберите **Custom endpoint (self-hosted / vLLM)** и укажите:

- **Base URL:** `http://127.0.0.1:8000/v1`
- **API key:** оставить пустым — в NVIDIA launcher не включена проверка `--api-key`
- **Model:** точный `id` из `/v1/models`, обычно `nvidia/Qwen3.8-27B-NVFP4`

Hermes официально поддерживает self-hosted OpenAI-compatible endpoints через `provider: custom`, `base_url` и имя модели.[69] Проверить сохранённую конфигурацию:

```powershell
hermes config check
hermes config get model --json
hermes status
```

Откройте **новый чат Hermes**: изменённая модель применяется к новым сессиям. Выполните короткий текстовый запрос. После этого отдельно проверьте один tool call в Hermes: успешный ответ `/v1/chat/completions` сам по себе ещё не доказывает работу вызова инструментов. Официальный NVIDIA launcher включает Qwen parser и auto-tool-choice, но реальное поведение нужно проверить на своей конфигурации.[65][66]







## Ограничения и безопасность

- По переданному владельцем preflight устройство соответствует 128-ГБ профилю. Агент к Spark не подключался; checkpoint, image и модели не скачивались, установка и аппаратные тесты не выполнялись.
- Разделяйте дисковое хранение и unified memory: свободное место на SSD не означает, что несколько checkpoint одновременно поместятся в RAM/VRAM.
- Оставляйте API на `127.0.0.1` и используйте SSH forwarding; не публикуйте неаутентифицированный vLLM endpoint в LAN или интернет.
- Docker group даёт привилегии уровня root. Не меняйте членство без отдельного согласия владельца; описанный manual path использует `sudo` и тоже пока не запускался.
- Поддержка revision-параметров в закреплённом 128-ГБ NGC image не проверялась runtime-тестом; перед запуском после отдельного разрешения сверяйте его встроенный `vllm serve --help`.

## Sources

[13] https://huggingface.co/nvidia/Qwen3.8-27B-NVFP4
[20] https://build.nvidia.com/spark/vllm/intermediate
[53] https://huggingface.co/docs/huggingface_hub/en/guides/cli
[65] https://raw.githubusercontent.com/NVIDIA/dgx-spark-playbooks/30883150541743d580c9c347700c6ac99fc396d2/nvidia/playbook-vllm/assets/sync-vllm-spark-64gb-qwen38-27b.sh
[66] https://raw.githubusercontent.com/NVIDIA/dgx-spark-playbooks/30883150541743d580c9c347700c6ac99fc396d2/nvidia/playbook-vllm/assets/sync-vllm-spark-128gb-qwen38-27b.sh
[68] https://huggingface.co/z-lab/Qwen3.8-27B-DFlash2
[69] https://hermes-agent.nousresearch.com/docs/integrations/providers
[77] https://huggingface.co/api/models/nvidia/Qwen3.8-27B-NVFP4?blobs=true
[78] https://huggingface.co/api/models/z-lab/Qwen3.8-27B-DFlash2?blobs=true
[88] https://docs.vllm.ai/en/v0.28.0/api/vllm/config/speculative
[89] https://docs.vllm.ai/en/v0.28.0/cli/serve
