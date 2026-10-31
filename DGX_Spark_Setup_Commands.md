# DGX Spark: краткий указатель команд

**Это навигационная страница, а не установочная инструкция.** Команды установки приведены только в профильных runbook-файлах; не смешивайте шаги между разными сценариями.

## Статус целевого устройства

Владелец сообщил: NVIDIA GB10, 128 ГБ по `MemTotal`, Ubuntu 24.04.5 LTS ARM64 и около 3,5 ТБ свободно на системном разделе. `nvidia-smi` не выводит объём памяти (`N/A`); для этого устройства 128-ГБ конфигурация подтверждается выводом Linux-памяти. Docker daemon активен, но обычный пользователь не имеет доступа к socket; `sudo docker info` возвращает версию сервера.

Это сведения владельца, не независимый тест агента. **По решению владельца установка моделей пока не выполняется.** Статусы проверок находятся в [матрице валидации](./docs/validation-status.md).

## 1. Read-only preflight

Перед выбором runbook выполните на самом Spark только диагностику:

```bash
uname -m
cat /etc/os-release
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
free -h
grep -E 'MemTotal|MemAvailable' /proc/meminfo
df -h / "$HOME" /srv
docker version
id
stat -c '%A %U:%G %n' /var/run/docker.sock
sudo docker info --format '{{.ServerVersion}}'
```

`sudo docker info` — проверка доступности daemon, а не установка. Если обычная команда `docker` получает `permission denied`, не добавляйте пользователя в группу `docker` автоматически: такая группа даёт привилегии уровня root.[20]

Для Spark на 64 и 128 ГБ NVIDIA публикует разные vLLM-рецепты. Сверьте конфигурацию по `MemTotal` и используйте только подходящую ветку; не применяйте 64-ГБ команды к этому 128-ГБ устройству.[20][65][66]

## 2. Выберите отдельное руководство

| Задача | Руководство |
|---|---|
| План моделей, порядок установки и размещение данных | [План моделей и хранения](./docs/model-install-plan.md) |
| Coding API Qwen3.8-27B; отдельные ветки 64/128 ГБ | [Qwen3.8-27B runbook](./model/Qwen3.8-27B/README.md) |
| Генерация изображений ComfyUI + Z-Image-Turbo | [ComfyUI/Z-Image-Turbo runbook](./docs/comfyui-zimage.md) |
| Дополнительные модели и лицензионные условия | [Матрица моделей и лицензий](./docs/model-and-license-matrix.md) |
| Windows/Android и SSH-туннель к Spark | [Рабочий процесс Windows/Android](./docs/windows-android-toolchain.md) |

NVIDIA ComfyUI quick start — отдельный host-Python сценарий, а не продолжение vLLM-рецепта; его точные шаги и ограничения вынесены в собственный runbook.[49][67]

## 3. Правила выполнения

1. Не загружайте и не запускайте модели, пока владелец не разрешил установку.
2. Перед любым запуском проверьте место, существующие каталоги и контейнеры; не удаляйте и не меняйте владельца существующих данных вслепую.
3. Оставляйте API на loopback и используйте SSH-туннель для доступа с Windows.
4. После реального запуска запишите результат в [матрицу валидации](./docs/validation-status.md). `bash -n`, доступность Docker и HTTP health-check сами по себе не доказывают успешную работу модели.

## Sources

[20] https://build.nvidia.com/spark/vllm/intermediate
[49] https://build.nvidia.com/playbooks/comfyui/image-gen-quick-start.md
[65] https://raw.githubusercontent.com/NVIDIA/dgx-spark-playbooks/30883150541743d580c9c347700c6ac99fc396d2/nvidia/playbook-vllm/assets/sync-vllm-spark-64gb-qwen38-27b.sh
[66] https://raw.githubusercontent.com/NVIDIA/dgx-spark-playbooks/30883150541743d580c9c347700c6ac99fc396d2/nvidia/playbook-vllm/assets/sync-vllm-spark-128gb-qwen38-27b.sh
[67] https://raw.githubusercontent.com/NVIDIA/dgx-spark-playbooks/30883150541743d580c9c347700c6ac99fc396d2/nvidia/playbook-comfyui/assets/setup.sh
