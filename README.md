# Developer Toolkit Recommendations

Практическая подборка моделей и инструментов для разработки desktop-приложений Windows 11 и Android. В рекомендуемой схеме DGX Spark предоставляет локальный inference API, а Windows 11 остаётся рабочей машиной.

**План моделей и структура `/srv/ai`:** [model-install-plan.md](./docs/model-install-plan.md).

**Команды настройки DGX Spark:** [DGX_Spark_Setup_Commands.md](./DGX_Spark_Setup_Commands.md).

> **Важно:** это рекомендации, а не отчёт об установленной системе. На пользовательском DGX Spark модели и инструменты не устанавливались и не тестировались; перед запуском команд проверьте память, свободное место и runtime устройства.

## 1. Генерация изображений

### Z-Image-Turbo — первый кандидат для DGX Spark

Использовать для иллюстраций, фонов, заставок и графики для страниц приложений. Модель содержит 6 млрд параметров и распространяется под Apache 2.0. NVIDIA публикует специальный quick start ComfyUI для DGX Spark, в котором для первого запуска используется Z-Image-Turbo.[22][25]

### FLUX.2 Klein 4B — генерация и редактирование

Использовать, когда нужно не только создать изображение, но и менять его по инструкции или по референсам. Официальный ComfyUI guide описывает генерацию и редактирование для FLUX.2 Klein 4B; модель 4B опубликована под Apache 2.0.[24][26]

**Лицензия:** у Klein 9B условия отличаются от Klein 4B и ограничивают коммерческое использование. Для коммерческого приложения сначала проверять лицензию точного checkpoint; по умолчанию выбирать 4B.[24]

**Практический совет:** AI-изображение подходит для концептов, заставок и иллюстраций, но не является готовым векторным набором UI-иконок. Проверять композицию и читаемость на реальных размерах и темах приложения.

## 2. Иконки приложения и интерфейса

- Для стандартных UI-иконок использовать готовые векторные наборы: **Material Symbols** (Apache 2.0) или **Lucide** (ISC). Это обычно надёжнее и визуально согласованнее, чем генерировать каждую иконку моделью.[45][46]
- Для Android использовать **Image Asset Studio**: он создаёт launcher- и notification-ресурсы нужной плотности из исходного изображения или Material-иконки.[34]
- Для WinUI/UWP **Visual Studio Manifest Designer** может создать набор Windows assets из исходного изображения. Перед выпуском проверить все размеры, масштабирование и варианты темы; для хорошего результата Microsoft рекомендует не полагаться только на автоматическое масштабирование.[35][36]
- Если нужна уникальная эмблема, модель может подготовить визуальную идею; финальную версию лучше перевести в SVG/vector-форму и проверить малый размер, прозрачность, контраст и обрезку.

## 3. Диаграммы и схемы

Для технических схем отдельная image-модель не нужна: основная языковая модель может сформировать диаграмму в текстовом DSL, а рендерер — точно её построить.

- **Mermaid** — блок-схемы, sequence, class, ER и другие диаграммы, особенно удобные в Markdown и Git.[27]
- **PlantUML** — UML и схемы взаимодействия; можно экспортировать, в частности, в PNG и SVG.[28]
- **Graphviz / DOT** — графы зависимостей, компонентные связи и автоматически раскладываемые графы.[29]

Сохранять исходник диаграммы рядом с кодом и запускать рендер/проверку при изменении, чтобы схема не расходилась с реализацией.

## 4. Help, руководства и API-документация

Отдельная модель для написания справки не обязательна. Основная coding-модель может подготовить черновики на русском, если ей передавать код, README, требования и проверенные источники. Факты о поведении приложения затем сверять с реализацией и тестами.

- **DocFX** — генерирует .NET API-справку из XML-комментариев; также позволяет добавлять Markdown-страницы с руководствами.[37]
- **Dokka** — генератор API-документации Kotlin, понимает KDoc и Java Javadoc и умеет создавать HTML и Markdown.[38]
- Для поиска по большой локальной кодовой базе и документации можно добавить **Qwen3-Embedding-0.6B** для семантического поиска и **Qwen3-Reranker-0.6B** для сортировки найденных фрагментов. Это полезное дополнение, не обязательная часть первого запуска.[30][31]
- Для извлечения текста/структуры из PDF и скриншотов можно проверить **DeepSeek-OCR-2** — OCR vision-language модель с лицензией Apache 2.0.[33]

## 5. Подключение моделей к редактору

**Continue** умеет подключаться к OpenAI-совместимому API, в том числе к self-hosted endpoint. Это позволяет держать модель на Spark и работать с кодом из IDE на Windows.[39]

Рекомендуемая схема: IDE и инструменты сборки работают на Windows 11; Spark предоставляет локальный inference API. Модельный сервер сам по себе не собирает WinUI/WPF-приложения и не проверяет их — coding-агенту нужно дать доступ к проекту, командам сборки и результатам тестов.

## 6. Сборка и проверка приложений

### Windows 11

Использовать подходящий проекту стек: Windows App SDK/WinUI 3 для нового нативного UI либо существующий WPF/WinForms/Win32. Windows App SDK предназначен для разработки Windows desktop-приложений и может применяться с WinUI 3 и существующими desktop-стеками.[44]

Тесты .NET запускать через `dotnet test` с выбранным тестовым framework, например MSTest, NUnit или xUnit.[41] Финальную Windows-сборку и UI-проверку выполнять в Windows-среде.

### Android

Использовать Android Studio, Android SDK, Gradle и эмулятор/устройство. Android Studio предоставляет инструменты сборки и тестирования; UI-тесты можно запускать из IDE или командной строки.[40][47]

### Автоматизация и безопасность

- **Git** — хранить исходники, диаграммы, документацию и историю изменений.
- **GitHub Actions** — автоматизировать сборку и тесты при push и pull request.[42]
- **OWASP Dependency-Check** — проверять зависимости проекта на известные уязвимости.[43]

## 7. Рекомендуемый стартовый комплект

1. Основная coding-модель — текущая Qwen3.8-27B; переход к более крупному варианту на Spark делать только после уточнения памяти устройства и подходящего runtime.
2. ComfyUI + Z-Image-Turbo — начать с официального Spark quick start для генерации изображений.[22][25]
3. FLUX.2 Klein 4B — добавить, если нужны редактирование изображений и работа с референсами; перед коммерческим использованием проверить лицензию checkpoint.[24][26]
4. Для стандартных UI-иконок использовать Material Symbols или Lucide.[45][46]
5. Для Android assets использовать Image Asset Studio.[34]
6. Для Windows assets использовать Visual Studio Manifest Designer.[35][36]
7. Mermaid подходит для диаграмм в Markdown; PlantUML — для UML; Graphviz — для графов зависимостей.[27][28][29]
8. DocFX — для C#/.NET help и API; Dokka — для Kotlin API.[37][38]
9. Qwen embeddings/reranker добавлять только если нужен поиск по большому корпусу проекта.[30][31]
10. Continue подключает локальный API к редактору.[39]
11. Git, Android/.NET тесты, GitHub Actions и Dependency-Check составляют базовый инженерный цикл.[40][41][42]

## 8. Ограничения и следующий шаг

Память конкретного Spark (64 или 128 ГБ), свободное место на диске, ОС и runtime не подтверждены. DGX Spark использует общую память; крупная языковая модель и image-generation workflow могут конкурировать за неё. На старте загружать несколько checkpoint на диск можно, но не следует предполагать, что все модели можно одновременно держать в памяти без замеров.

Перед точной инструкцией установки нужно уточнить конфигурацию Spark и свободное место. Ни одна модель или программа из этого списка не устанавливалась на устройство пользователя; производительность на конкретной системе не измерялась.

## Sources

[22] https://build.nvidia.com/spark/comfyui/image-gen-quick-start  
[24] https://github.com/black-forest-labs/flux2/blob/main/README.md  
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
[39] https://docs.continue.dev/customize/model-providers/top-level/openai  
[40] https://developer.android.com/studio/test  
[41] https://learn.microsoft.com/en-us/dotnet/core/testing  
[42] https://docs.github.com/actions/quickstart  
[43] https://owasp.org/www-project-dependency-check  
[44] https://learn.microsoft.com/en-us/windows/apps/windows-app-sdk  
[45] https://fonts.google.com/icons  
[46] https://lucide.dev/license  
[47] https://developer.android.com/studio
