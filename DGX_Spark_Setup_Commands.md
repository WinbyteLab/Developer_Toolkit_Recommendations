# Пошаговая настройка DGX Spark

Основной обзор моделей и инструментов: [README.md](./README.md).

Эта инструкция предназначена для терминала DGX Spark с DGX OS/Linux. Команды на Spark не запускались и не проверялись на устройстве пользователя. Сначала нужно определить фактическую память, ОС и свободное место; для 64 и 128 ГБ NVIDIA публикует разные контейнеры и скрипты запуска.[20][48][15]

## 1. Проверьте Spark

Подключитесь через NVIDIA Sync → **Terminal** или по SSH и выполните:

```bash
hostname
cat /etc/os-release
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
grep MemTotal /proc/meminfo
free -h
df -h "$HOME"
docker version
docker ps -a
python3 --version
git --version
```

- Для Z-Image NVIDIA указывает ориентир от 30 ГБ свободного места и около 24 ГБ GPU-памяти.[22][49]
- Если `nvidia-smi` или Docker выдаёт ошибку, остановитесь и сначала устраните эту проблему.
- Определите модель Spark: **64 или 128 ГБ**. Далее выполняйте только соответствующую ветку.

## 2. Установите Hugging Face CLI, если его ещё нет

Проверьте:

```bash
hf --help
```

Если команда не найдена, установите CLI:

```bash
curl -LsSf https://hf.co/cli/install.sh | bash -s -- --exclude-skill
```

После установки откройте новый терминал и снова выполните `hf --help`.[53]

## 3. Загрузите coding-модель Qwen3.8-27B

Рецепт загружает NVIDIA checkpoint `nvidia/Qwen3.8-27B-NVFP4` в смешанном NVFP4/FP8 формате; указанный размер его Hugging Face репозитория — около 21.9 GB. Дополнительно нужны место для draft-модели и контейнера; проверьте свободное место до загрузки.[13][56][20]

По умолчанию кеш Hugging Face находится в `~/.cache/huggingface`; если задана `HF_HOME`, скрипты используют этот путь. Проверьте свободное место именно на файловой системе кеша.[15][48]

Не заменяйте указанные теги контейнеров на `latest`.

### Ветка для DGX Spark 64 ГБ

```bash
docker pull vllm/vllm-openai:v0.28.0
hf download nvidia/Qwen3.8-27B-NVFP4
hf download z-lab/Qwen3.8-27B-DFlash2
```

Скачайте и просмотрите скрипт NVIDIA:

```bash
mkdir -p ~/dgx-spark/vllm
cd ~/dgx-spark/vllm

curl -fL -o launch-qwen.sh \
  'https://raw.githubusercontent.com/NVIDIA/dgx-spark-playbooks/refs/heads/main/nvidia/playbook-vllm/assets/sync-vllm-spark-64gb-qwen38-27b.sh'

less launch-qwen.sh
chmod u+x launch-qwen.sh
```

### Ветка для DGX Spark 128 ГБ

```bash
docker pull nvcr.io/nvidia/vllm:26.10.pre1-py3
hf download nvidia/Qwen3.8-27B-NVFP4
hf download z-lab/Qwen3.8-27B-DFlash2
```

Скачайте и просмотрите скрипт NVIDIA:

```bash
mkdir -p ~/dgx-spark/vllm
cd ~/dgx-spark/vllm

curl -fL -o launch-qwen.sh \
  'https://raw.githubusercontent.com/NVIDIA/dgx-spark-playbooks/refs/heads/main/nvidia/playbook-vllm/assets/sync-vllm-spark-128gb-qwen38-27b.sh'

less launch-qwen.sh
chmod u+x launch-qwen.sh
```

Загрузка контейнера для 128 ГБ может потребовать авторизации в NGC. Если `docker pull` сообщает об отказе в доступе, настройте доступ к NGC на Spark; не меняйте тег контейнера.

Перед стартом проверьте существующие контейнеры:

```bash
docker ps -a
```

Скрипт удаляет одноимённый контейнер перед созданием нового. Запускайте его только после проверки памяти и списка контейнеров:

```bash
./launch-qwen.sh
```

Оставьте этот терминал открытым. Во втором терминале Spark проверьте журнал; используйте имя контейнера для своей конфигурации:

```bash
# DGX Spark 64 ГБ
docker logs --tail 50 --follow vllm-spark-64gb-qwen38-27b

# DGX Spark 128 ГБ
docker logs --tail 50 --follow vllm-spark-128gb-qwen38-27b
```

Дождитесь сообщения о готовности сервера. Затем проверьте API на Spark:

```bash
curl --fail-with-body -i http://127.0.0.1:8000/health
curl --fail-with-body -sS http://127.0.0.1:8000/v1/models
```

Чтобы остановить модель, нажмите **Ctrl+C** в терминале, где запущен `launch-qwen.sh`.

## 4. Подключите API к Windows

В PowerShell на Windows создайте SSH-туннель, подставив имя пользователя и IP-адрес Spark:

```powershell
ssh -N -L 8000:127.0.0.1:8000 <имя_пользователя>@<IP_адрес_Spark>
```

Не закрывая это окно, откройте другое окно PowerShell и проверьте API:

```powershell
curl.exe --fail-with-body -i http://localhost:8000/health
curl.exe --fail-with-body -sS http://localhost:8000/v1/models
```

Отправьте тестовый запрос:

```powershell
$model = (Invoke-RestMethod http://localhost:8000/v1/models).data[0].id
$body = @{
  model = $model
  messages = @(@{ role = "user"; content = "Ответь одной фразой по-русски: сервер работает?" })
  max_tokens = 100
} | ConvertTo-Json -Depth 5

Invoke-RestMethod http://localhost:8000/v1/chat/completions `
  -Method Post -ContentType "application/json" -Body $body
```

## 5. Установите ComfyUI и Z-Image-Turbo

Сначала остановите Qwen. DGX Spark использует общую память; не рассчитывайте, что coding-модель и генерация изображений смогут безопасно работать одновременно.[22]

В терминале Spark:

```bash
mkdir -p ~/dgx-spark/comfyui-zimage
cd ~/dgx-spark/comfyui-zimage

curl -fL -o setup.sh \
  'https://raw.githubusercontent.com/NVIDIA/dgx-spark-playbooks/refs/heads/main/nvidia/playbook-comfyui/assets/setup.sh'

less setup.sh
```

Просмотрите файл, затем запустите его от обычного пользователя, не через `sudo`:

```bash
bash setup.sh
```

Скрипт закрепляет ComfyUI на теге `v0.33.2` и загружает около 20 GB файлов Z-Image-Turbo. Убедитесь, что в целевой файловой системе хватает места. Скрипт использует `wget -nc`: если загрузка оборвётся, не перезапускайте его вслепую — сначала проверьте частично скачанные файлы, так как повторный запуск может пропустить существующий неполный файл. Запускайте установку в новой папке; существующие `comfyui-env/` и `ComfyUI/` скрипт повторно использует.[49][50]

Скрипт создаёт Python virtualenv, ставит ComfyUI и загружает файлы Z-Image-Turbo.[49][50]

Для локального доступа запустите ComfyUI на loopback-интерфейсе:

```bash
cd ~/dgx-spark/comfyui-zimage
source comfyui-env/bin/activate
cd ComfyUI
python main.py --listen 127.0.0.1
```

В другом терминале Spark проверьте веб-сервер:

```bash
curl -I http://127.0.0.1:8188
```

В PowerShell на Windows создайте отдельный туннель:

```powershell
ssh -N -L 8188:127.0.0.1:8188 <имя_пользователя>@<IP_адрес_Spark>
```

Откройте в браузере `http://localhost:8188`. В ComfyUI выберите **Templates → Image → Z-Image-Turbo: Text to Image** и запустите шаблон. Для остановки нажмите **Ctrl+C** в терминале Spark.

## 6. FLUX.2 Klein 4B — после проверки совместимости

Не добавляйте Klein в первый запуск автоматически. Скрипт NVIDIA закрепляет определённую версию ComfyUI, тогда как актуальное руководство Klein предупреждает, что workflow может требовать обновлённый или Nightly ComfyUI. Сначала добейтесь успешной генерации Z-Image, затем обновите ComfyUI по актуальному руководству либо используйте отдельную копию. Не смешивайте версии без проверки.[26][50][54]

## 7. Что устанавливать не на Spark

Android Studio, Image Asset Studio, Visual Studio, Mermaid/PlantUML/Graphviz, DocFX/Dokka, GitHub Actions и Dependency-Check относятся к рабочей машине и проекту. На Spark в рамках этой схемы достаточно сервера vLLM и, при необходимости, ComfyUI. Embeddings и OCR из README пока отложите: загрузка весов сама по себе не настраивает и не запускает поиск или OCR.

## Sources

[13] https://huggingface.co/nvidia/Qwen3.8-27B-NVFP4
[15] https://raw.githubusercontent.com/NVIDIA/dgx-spark-playbooks/refs/heads/main/nvidia/playbook-vllm/assets/sync-vllm-spark-128gb-qwen38-27b.sh
[20] https://build.nvidia.com/spark/vllm/intermediate
[22] https://build.nvidia.com/spark/comfyui/image-gen-quick-start
[26] https://docs.comfy.org/tutorials/flux/flux-2-klein
[48] https://raw.githubusercontent.com/NVIDIA/dgx-spark-playbooks/refs/heads/main/nvidia/playbook-vllm/assets/sync-vllm-spark-64gb-qwen38-27b.sh
[49] https://build.nvidia.com/playbooks/comfyui/image-gen-quick-start.md
[50] https://raw.githubusercontent.com/NVIDIA/dgx-spark-playbooks/refs/heads/main/nvidia/playbook-comfyui/assets/setup.sh
[53] https://huggingface.co/docs/huggingface_hub/en/guides/cli
[54] https://huggingface.co/Comfy-Org/flux2-klein/tree/main/split_files
[56] https://huggingface.co/nvidia/Qwen3.8-27B-NVFP4/tree/main
