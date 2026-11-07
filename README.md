# PayPilot · ДЗ №9 · L10

**Рішення:** залишити хмарного суддю з ручною перевіркою ескалації. [Model Selection Recommendation](model-selection-recommendation.md)

- [Хмарна заява довіри](judge-trust-statement.md) · [локальна заява довіри](judge-trust-statement.local.md)
- [Повний локальний звіт і 150 сирих спроб](evals/reports/calibration-l09_labels-schema-20261107T160535826977Z.json) · [чинний хмарний перерахунок](evals/reports/calibration-raw-recount.json) · [первинний хмарний звіт](evals/reports/calibration-l09_labels-20261029T142704481494Z-02244a87.json)
- [Зафіксовані кейси](evals/sets/l09_labels.jsonl) · [рубрика](rubrics/rubric.v1.md) · [запис freeze](evidence/labels-freeze.json)
- [Універсальний шаблон](model-selection-recommendation.template.md) · [план](docs/execution-plan.md) · [контракт і самотест](docs/lab-preparation.md) · [пілот](docs/lab-recommendation-draft.md)

## Відтворення

Перевірено на `qwen2.5:7b` станом на 7 листопада 2026 року. Потрібні Docker Compose, Python-образ із Compose і Ollama на хості з точним дайджестом із [judge.local.env](judge.local.env). Калібратор передає в Ollama записане питання, відповідь і рубрику. Мітки залишаються в калібраторі. Профіль живого стенду не використовується цим запуском.

Офлайн-валідація набору:

```powershell
docker compose run --rm --entrypoint python eval tools/calibrate_run.py l09_labels --validate-only
```

Повна команда для L13, PowerShell:

```powershell
$env:JUDGE_MODEL = 'ollama:qwen2.5:7b'
docker compose run --rm --entrypoint python eval tools/calibrate_run.py l09_labels
```

Bash:

```bash
JUDGE_MODEL=ollama:qwen2.5:7b docker compose run --rm --entrypoint python eval tools/calibrate_run.py l09_labels
```

Команда пише `reports/calibration-l09_labels-*.json` із `judge_model`, `runs: 5` та сирими відповідями. У здачі перевірений звіт лежить у `evals/reports/`. Повний живий прогін через Ollama завершився в робочій копії. Окремий тест команди на чистому Git-клоні використав ізольований тестовий API і підтвердив 30 × 5 та заповнений `judge_model`. Його відповіді не входять у калібрування.

Лабораторний пілот можна повторити командами з тією самою службою `eval` і аргументом `l10_one --format schema`, `l10_one --format none` або `l10_pilot`.

Хмарні витрати та таймінги взято з перших 150 спроб `rubric.v1` у ДЗ8. Оцінка оплати — USD 0,182620. Сума `duration_ms` зі збережених викликів — 220,056 с. Цей час відрізняється за методикою від локального стінного часу. [Джерело таймінгів ДЗ8](https://github.com/roman-olshevskiy/paypilot-hw8/blob/908ccfc/evidence/final-analysis.json)
