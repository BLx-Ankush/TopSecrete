# Cron Scheduler

This module provides task scheduling with natural language interface for ALICE.

## Features

- **Natural Language**: Create schedules with human-readable expressions
- **Platform Delivery**: Send results to Telegram, Discord, Slack, etc.
- **Isolated Execution**: Cronjobs run with isolated context
- **Retry Logic**: Automatic retry for transient failures
- **Execution History**: Track job runs with timestamps and results

## Structure

```
cron/
├── __init__.py
├── scheduler.py            # APScheduler integration
├── job.py                  # Job definition and execution
└── manager.py              # Job management (create, list, pause, etc.)
```

## Usage

```python
from cron.manager import CronManager

manager = CronManager(config)
job_id = await manager.create_job(
    name="daily-report",
    schedule="every day at 9am",
    task="Generate daily summary",
    platform="telegram"
)
```

## Job Storage

Jobs are stored in `data/cron/jobs.yaml` with execution logs in `data/cron/logs/`.

## Schedule Formats

- Natural language: "every day at 9am", "every Monday at 10:30"
- Cron expressions: "0 9 * * *"
- Intervals: "every 30 minutes", "every 2 hours"
