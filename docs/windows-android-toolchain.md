# Рабочий процесс Windows 11 и Android

DGX Spark в предлагаемой схеме предоставляет inference API. IDE, исходники, Android SDK, Windows-сборки и проверки приложений выполняются на рабочей машине Windows 11. Это рекомендации, а не отчёт об установленной или протестированной рабочей станции.

> **Граница выполнения:** PowerShell, Gradle, .NET и Android build-команды ниже предназначены для Windows-машины из корня соответствующего приложения. Не выполняйте их на Spark. В этой работе не было доступного app-проекта; сборки и тесты не запускались ни на Spark, ни на Windows.

## Матрица инструментов

| Задача | Инструмент | Где запускать | Проверка результата |
| --- | --- | --- | --- |
| Подключить локальную coding-модель к редактору | Continue с OpenAI-совместимым endpoint | IDE на Windows; API доступен через защищённый SSH-туннель к Spark | Получить model ID из `/v1/models`; выполнить тестовый запрос.[39] |
| Android-разработка | Android Studio, Android SDK, Gradle Wrapper, эмулятор или устройство | Windows 11 | Сборку и тесты запускать Gradle Wrapper из корня проекта.[40][47][62] |
| Windows desktop-разработка | Стек проекта: WinUI/Windows App SDK, WPF, WinForms или Win32 | Windows 11 | Проверять реальную сборку и UI в Windows-среде.[44] |
| .NET тестирование | Выбранный framework: MSTest, NUnit или xUnit; `dotnet test` | Windows 11 или Windows CI | Сборка и тесты должны выполняться в чистом checkout проекта.[41] |
| Иконки и platform assets | Material Symbols/Lucide; Image Asset Studio; Visual Studio asset generation | Windows 11 и IDE проекта | Проверить векторный исходник, плотности, тему, прозрачность и маленький размер.[34][35][36][45][46] |
| Диаграммы | Mermaid, PlantUML, Graphviz/DOT | Репозиторий приложения | Хранить текстовый исходник рядом с кодом; рендерить тем же инструментом в CI.[27][28][29] |
| API/help | DocFX для .NET; Dokka для Kotlin | Рабочая машина или CI | Генерировать из актуальных комментариев API и markdown-руководств.[37][38] |
| Автоматизация | GitHub Actions; OWASP Dependency-Check | GitHub Actions runner | Сборка/тесты запускаются на push и pull request; отчёты зависимостей просматриваются перед выпуском.[42][43] |

## Android: команды проекта

Запускайте команды из корня Android-репозитория в PowerShell. Используйте Gradle Wrapper, уже включённый в проект, а не случайную глобальную версию Gradle.[62]

```powershell
# Посмотреть доступные задачи
.\gradlew.bat tasks

# Запустить тесты проекта
.\gradlew.bat test

# Собрать debug APK (имя модуля может отличаться)
.\gradlew.bat assembleDebug
```

Если проект использует отдельные Android-тесты, список задач и их имена зависят от модулей; сначала проверьте `tasks`, затем запускайте соответствующие задачи. Android Studio/SDK и лицензии Android SDK должны быть настроены на Windows-машине; сами сборки не выполняются DGX Spark.[40][47][62]

## .NET: команды проекта

```powershell
dotnet --info
dotnet test <путь-к-файлу-решения.sln>
```

Замените placeholder на существующий solution или project в вашем репозитории. Не считайте успешным тестом вывод команды, запущенной не из нужного checkout.[41]

## Подключение Continue к Spark

1. На Spark запустите Qwen и оставьте сервер привязанным к loopback.
2. На Windows откройте SSH-туннель к порту API согласно [руководству DGX Spark](../DGX_Spark_Setup_Commands.md).
3. В Continue укажите OpenAI-совместимый base URL `http://localhost:8000/v1` и model ID, возвращённый `/v1/models`.
4. Не размещайте endpoint без аутентификации в публичной сети. Не вставляйте токены или приватные ключи в конфигурацию, которую коммитите.
5. Выполните тестовый запрос в редакторе, затем проверьте изменения компилятором и тестами.

Точный формат конфигурации Continue зависит от версии расширения и редактора; сверяйте его с актуальной документацией провайдера.[39]

## Sources

[27] https://github.com/mermaid-js/mermaid
[28] https://plantuml.com/en
[29] https://graphviz.org/doc/info/lang.html
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
[62] https://developer.android.com/build/building-cmdline
