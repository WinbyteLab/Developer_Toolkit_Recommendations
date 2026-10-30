# Qwen3.8-27B на DGX Spark: установка, API и Hermes

> **Статус:** это пошаговая инструкция, а не отчёт об установленной системе. Команды на пользовательском Spark не выполнялись: перед началом проверьте память, ОС, Docker и свободное место. Используйте ветку только для фактической конфигурации 64 или 128 ГБ unified memory. Не запускайте обе ветки подряд.

## Что устанавливаем

- Основной checkpoint: `nvidia/Qwen3.8-27B-NVFP4` — NVIDIA-квантованный вариант Qwen3.8-27B, который NVIDIA указывает для DGX Spark с 64 и 128 ГБ.[1][4]
- Draft checkpoint: `z-lab/Qwen3.8-27B-DFlash2` — вспомогательная модель для speculative decoding, не самостоятельная чат-модель; оба официальных launch-скрипта Qwen используют её.[1][3][5]
- Runtime: vLLM в официальном варианте контейнера для соответствующей памяти.
- API: OpenAI-compatible API на `127.0.0.1:8000`. Доступ с ПК — через NVIDIA Sync port forwarding либо через SSH-туннель, не через открытый порт в LAN.[1]

Веса Hugging Face будут храниться в `/srv/ai/models/huggingface/hub`. Не удаляйте этот каталог как «временный cache»: в нём находятся сами веса.

## 1. Подготовить DGX Spark

### 1.1 Подключиться и проверить устройство

В NVIDIA Sync добавьте Spark через mDNS, IP-адрес или существующий SSH alias, подключитесь и откройте **Terminal**. Вручную введите команды на самом Spark:

```bash
whoami
hostname
uname -m
cat /etc/os-release
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
free -h
findmnt -T /srv
df -h /srv "$HOME"
docker version
docker info
docker ps -a
```

Убедитесь, что `/srv` находится на SSD с достаточным свободным местом. Если `/srv/ai` уже существует, сначала осмотрите его — не меняйте владельца рекурсивно и не удаляйте содержимое. Далее выберите **одну** ветку по реальному объёму unified memory: 64 ГБ или 128 ГБ. NVIDIA публикует для них разные image и launch-настройки.[1]

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
EOF
chmod 0644 /srv/ai/config/paths.sh
source /srv/ai/config/paths.sh
printf 'HF_HOME=%s\nHF_HUB_CACHE=%s\nTMPDIR=%s\n' "$HF_HOME" "$HF_HUB_CACHE" "$TMPDIR"
df -h "$HF_HOME" "$TMPDIR"
```

Не задавайте `HF_HOME` и `HF_HUB_CACHE` на разные несвязанные корни: официальный launcher монтирует `HF_HOME` внутрь контейнера как `/root/.cache/huggingface`. С указанными значениями `hf download` и vLLM используют один и тот же каталог моделей.[2][3]

Если `hf` не найден, установите официальный standalone CLI Hugging Face и откройте новый терминал:[1][7]

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
```

### Ветка A — DGX Spark 64 ГБ

```bash
docker pull vllm/vllm-openai:v0.28.0
hf download nvidia/Qwen3.8-27B-NVFP4
hf download z-lab/Qwen3.8-27B-DFlash2
df -h "$HF_HOME"
```

Это соответствующие NVIDIA image и checkpoint IDs для 64-ГБ рецепта.[1][2]

### Ветка B — DGX Spark 128 ГБ

NVIDIA указывает для 128 ГБ image, закреплённый digest-ом. Если NGC отклоняет загрузку, настройте NGC-доступ на самом Spark; не вставляйте API key в этот документ или Git.

```bash
# При необходимости пройдите интерактивную авторизацию в NGC:
docker login nvcr.io

# Image digest из таблицы официального NVIDIA-рецепта:
docker pull nvcr.io/nvidia/vllm:26.10.pre1-py3@sha256:cb38bbefdbc3e9fe045f931dd72cbd58cd48985c7e09916bcc6c15c10f39b929
hf download nvidia/Qwen3.8-27B-NVFP4
hf download z-lab/Qwen3.8-27B-DFlash2
df -h "$HF_HOME"
```

Draft checkpoint необходим выбранному DFlash2 speculative-decoding launch-скрипту. Он не заменяет основной Qwen checkpoint.[1][3][5]

Проверьте, что обе модели появились в Hub-кэше:

```bash
find "$HF_HUB_CACHE" -maxdepth 1 -type d \
  \( -name 'models--nvidia--Qwen3.8-27B-NVFP4' \
  -o -name 'models--z-lab--Qwen3.8-27B-DFlash2' \) -print
du -sh "$HF_HUB_CACHE"/models--nvidia--Qwen3.8-27B-NVFP4 \
       "$HF_HUB_CACHE"/models--z-lab--Qwen3.8-27B-DFlash2
```

Hugging Face управляет структурой `hub`; не переименовывайте его snapshot/blob-файлы и не держите вторую копию тех же весов через `--local-dir`.[2][3]

## 3. Настроить DGX Spark как локальный inference-сервер

Вендорские скрипты слушают только `127.0.0.1:8000`, включают Qwen tool-call parser и управляют временем жизни контейнера через NVIDIA Sync.[1][2][3] Для этого сценария не меняйте bind на `0.0.0.0` и не открывайте порт 8000 наружу.

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

Добавьте в скачанную копию загрузку переменных путей **до** вычисления `HF_CACHE_DIR` и `mktemp`:

```bash
python3 - "$SCRIPT" <<'PY'
from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text()
marker = "set -euo pipefail\n"
if s.count(marker) != 1:
    raise SystemExit("Неожиданное содержимое launcher; остановка без изменения файла")
s = s.replace(marker, marker + "\nsource /srv/ai/config/paths.sh\n", 1)
p.write_text(s)
PY
```

**Дополнительная фиксация image для ветки 128 ГБ.** В опубликованной таблице NVIDIA для 128-ГБ рецепта указан digest, тогда как Sync-launcher этой ревизии запускает тот же image по тегу `26.10.pre1-py3`. Поэтому для воспроизводимости замените в **локальной копии** один image reference на тот же digest, который использовался в `docker pull` выше. Это единственное отличие от скачанного скрипта; остальные аргументы рецепта не меняйте.[1][3]

```bash
if [ "${SCRIPT##*qwen-}" = "128gb.sh" ]; then
  python3 - "$SCRIPT" <<'PY'
from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text()
old = "nvcr.io/nvidia/vllm:26.10.pre1-py3"
new = old + "@sha256:cb38bbefdbc3e9fe045f931dd72cbd58cd48985c7e09916bcc6c15c10f39b929"
if s.count(old) != 1:
    raise SystemExit("Image tag не найден ровно один раз; остановка")
p.write_text(s.replace(old, new, 1))
PY
fi
```

В любом случае проверьте, что файл — ожидаемый bash-скрипт:

```bash
bash -n "$SCRIPT"
grep -nE 'HF_HOME|HF_CACHE_DIR|127\.0\.0\.1|PORT=|vllm serve|docker rm -f' "$SCRIPT"
```

Скрипт удаляет контейнер с конкретным именем `vllm-spark-...-qwen38-27b` перед созданием нового. До запуска просмотрите `docker ps -a`; не запускайте его, если в системе есть важный контейнер с этим именем.[2][3]

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

Для 128-ГБ скрипта **не** создавайте эти ссылки без причины: его комментарий требует сохранить prebuilt kernel/autotune cache внутри image; скрипт монтирует только Hugging Face cache.[3]

### 3.3 Добавить приложение NVIDIA Sync

В NVIDIA Sync:

1. Подключитесь к Spark.
2. Откройте **Custom → + Add New**.
3. Для **Name** укажите `vLLM-Qwen3.8-27B-64GB` или `vLLM-Qwen3.8-27B-128GB` согласно модели устройства.
4. В **Port** укажите `8000`.
5. Вставьте содержимое соответствующего проверенного файла `launch-qwen-64gb.sh` или `launch-qwen-128gb.sh` в **Launch Script**.
6. Оставьте **Auto open** и **Launch in Terminal** выключенными, **URL Path** пустым; нажмите **Add**.

NVIDIA Sync сам делает SSH-туннель и проброс порта к ноутбуку. Запуск рецепта на 128-ГБ Spark требует отдельной проверки старта и логов: вендор отмечает, что Sync-адаптация для этого профиля требует проверки на конкретном Spark.[1]

## 4. Подключить Windows-ПК к серверу

### Вариант A — NVIDIA Sync

Подключение и проброс порта делает Sync. После запуска приложения на Spark адрес с Windows-ПК:

```text
http://127.0.0.1:8000/v1
```

### Вариант B — обычный SSH-туннель

Используйте его, если не применяете port forwarding NVIDIA Sync. В PowerShell на Windows оставьте это окно открытым:

```powershell
$sparkUser = Read-Host 'Имя пользователя на Spark'
$sparkAddress = Read-Host 'IP-адрес или имя Spark'
ssh -N -L 8000:127.0.0.1:8000 "$sparkUser@$sparkAddress"
```

Замените только имя пользователя и адрес Spark. Не запускайте одновременно два проброса одного и того же локального порта. Туннель нужен, потому что vLLM намеренно слушает loopback-интерфейс Spark, а не всю локальную сеть.[1][2][3]

## 5. Запустить Qwen и проверить API

В NVIDIA Sync нажмите созданное custom-приложение. Для ручного запуска из терминала Spark вместо кнопки Sync выполните и оставьте команду работать в этом терминале:

```bash
source /srv/ai/config/paths.sh
bash /srv/ai/apps/vllm/launch-qwen-64gb.sh
# либо для 128 ГБ:
# bash /srv/ai/apps/vllm/launch-qwen-128gb.sh
```

Для просмотра логов откройте второй терминал Spark:

```bash
# 64 ГБ
docker logs --tail 50 --follow vllm-spark-64gb-qwen38-27b

# 128 ГБ
docker logs --tail 50 --follow vllm-spark-128gb-qwen38-27b
```

Дождитесь сообщения о готовности vLLM. Первый старт может занять время на компиляцию runtime и загрузку весов. Затем проверьте API **на Spark**:

```bash
curl --fail-with-body -i http://127.0.0.1:8000/health
curl --fail-with-body -sS http://127.0.0.1:8000/v1/models
```

В PowerShell на Windows проверьте доступ через Sync или SSH-туннель и отправьте короткий запрос:

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

Для остановки нажмите **Stop** у custom app в NVIDIA Sync. При ручном запуске нажмите `Ctrl+C` в терминале, где выполняется launcher; скрипт остановит и удалит созданный им контейнер.[2][3]

## 6. Подключить модель к Hermes на Windows

Сначала убедитесь, что Sync forwarding или SSH-туннель работает и `Invoke-RestMethod http://127.0.0.1:8000/v1/models` возвращает список. Возьмите точный `id` из этого ответа; не подставляйте имя наугад.

В PowerShell на ПК запустите мастер:

```powershell
hermes model
```

В мастере выберите **Custom endpoint (self-hosted / vLLM)** и укажите:

- **Base URL:** `http://127.0.0.1:8000/v1`
- **API key:** оставить пустым — в NVIDIA launcher не включена проверка `--api-key`
- **Model:** точный `id` из `/v1/models`, обычно `nvidia/Qwen3.8-27B-NVFP4`

Hermes официально поддерживает self-hosted OpenAI-compatible endpoints через `provider: custom`, `base_url` и имя модели.[6] Проверить сохранённую конфигурацию:

```powershell
hermes config check
hermes config get model --json
hermes status
```

Откройте **новый чат Hermes**: изменённая модель применяется к новым сессиям. Выполните короткий текстовый запрос. После этого отдельно проверьте один tool call в Hermes: успешный ответ `/v1/chat/completions` сам по себе ещё не доказывает работу вызова инструментов. Официальный NVIDIA launcher включает Qwen parser и auto-tool-choice, но реальное поведение нужно проверить на своей конфигурации.[2][3]

## 7. Публикация инструкции в GitHub

Эта инструкция находится в `model/Qwen3.8-27B/README.md`; ссылка на неё добавлена в `docs/model-install-plan.md`. Для публикации будущих правок из локального клона репозитория выполните в PowerShell:

```powershell
$repo = Read-Host 'Введите полный путь к локальному клону Developer_Toolkit_Recommendations'
Set-Location $repo
git pull --ff-only
git add model/Qwen3.8-27B/README.md docs/model-install-plan.md
git diff --cached --check
git diff --cached --name-only
git diff --cached
git commit -m "docs: add Qwen3.8 DGX Spark setup guide"
git push
```

Перед `git commit` убедитесь, что в staged diff только ожидаемые Markdown-файлы, и используйте настроенную Git-идентичность. Никогда не добавляйте в репозиторий `HF_TOKEN`, NGC API key, пароли, содержимое `.env`, скачанные веса или логи.

## Ограничения и безопасность

- Эти команды не были выполнены на Spark; конфигурацию 64/128 ГБ, свободное место и существующие контейнеры нужно проверить непосредственно на устройстве.
- Разница между памятью и диском важна: несколько checkpoint можно хранить на SSD, но не следует ожидать, что они одновременно поместятся в общую память.
- Оставляйте API на `127.0.0.1` и используйте Sync/SSH forwarding. Не публикуйте неаутентифицированный vLLM endpoint в LAN или интернет.
- В группе `docker` фактически есть root-эквивалентный доступ. Если NVIDIA Sync предложит добавить пользователя в группу, принимайте это только если согласны с этим уровнем доступа.[1]

## Sources

[1] https://build.nvidia.com/spark/vllm/intermediate
[2] https://raw.githubusercontent.com/NVIDIA/dgx-spark-playbooks/30883150541743d580c9c347700c6ac99fc396d2/nvidia/playbook-vllm/assets/sync-vllm-spark-64gb-qwen38-27b.sh
[3] https://raw.githubusercontent.com/NVIDIA/dgx-spark-playbooks/30883150541743d580c9c347700c6ac99fc396d2/nvidia/playbook-vllm/assets/sync-vllm-spark-128gb-qwen38-27b.sh
[4] https://huggingface.co/nvidia/Qwen3.8-27B-NVFP4
[5] https://huggingface.co/z-lab/Qwen3.8-27B-DFlash2
[6] https://hermes-agent.nousresearch.com/docs/integrations/providers
[7] https://huggingface.co/docs/huggingface_hub/en/guides/cli
