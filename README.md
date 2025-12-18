# Discord A/B/C Todo Bot

A Discord bot for managing daily tasks using the A/B/C priority system. Built with discord.py v2+ featuring slash commands and interactive buttons.

![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)
![Discord.py](https://img.shields.io/badge/discord.py-2.0%2B-blue)
![Coverage](https://img.shields.io/badge/coverage-95%25-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

- ✅ **A/B/C Priority System**: Organize tasks by importance (A = highest, B = medium, C = lowest)
- 🔘 **Interactive Buttons**: Mark tasks done/undone with a single click
- 📅 **Date Support**: View tasks for today or any specific date
- 👤 **Per-User Tasks**: Each user has their own private task list
- 📊 **Strikethrough Completed Tasks**: Visual feedback for done items
- 🔄 **Automatic Rollover**: Incomplete tasks automatically carry over to the next day at midnight
- 💾 **SQLite Storage**: Persistent task storage with easy backup
- 🐳 **Docker Support**: Easy deployment with Docker and Docker Compose
- ⚙️ **Configurable**: Environment-based configuration with sensible defaults

## Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/add` | Add a new task | `/add A Finish report` |
| `/list` | List your tasks for today | `/list` |
| `/list [date]` | List tasks for a specific date | `/list 2024-12-25` |
| `/done [id]` | Mark a task as completed | `/done 3` |
| `/delete [id]` | Delete a task permanently | `/delete 3` |
| `/clear` | Remove all completed tasks | `/clear` |
| `/rollover` | Copy incomplete tasks from yesterday to today | `/rollover` |
| `/status` | Show bot status and stats | `/status` |

> **Rate Limit:** 5 commands per 10 seconds per user

## Task Display

Tasks are displayed grouped by priority with interactive buttons:

```text
**Today's Tasks**

🔴 **A-Priority**
1. Finish report [✅]
2. Email boss [✅]

🟡 **B-Priority**
3. Review notes [✅]

🟢 **C-Priority**
4. Check emails [✅]
```

- Clicking ✅ marks the task as done
- Completed tasks appear with ~~strikethrough~~
- Click ↩️ on completed tasks to undo

## Installation

### Prerequisites

- Python 3.11 or higher
- A Discord bot token ([Get one here](https://discord.com/developers/applications))

### Quick Start with Docker (Recommended)

1. **Clone the repository**:

   ```bash
   git clone https://github.com/yourusername/todo-bot.git
   cd todo-bot
   ```

2. **Configure the bot**:

   ```bash
   cp .env.example .env
   # Edit .env and add your Discord token
   ```

3. **Run with Docker Compose**:

   ```bash
   docker-compose up -d
   ```

4. **View logs**:

   ```bash
   docker-compose logs -f
   ```

### Manual Installation

1. **Clone the repository**:

   ```bash
   git clone https://github.com/yourusername/todo-bot.git
   cd todo-bot
   ```

2. **Create a virtual environment**:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:

   ```bash
   pip install -e .
   ```

4. **Configure the bot**:

   ```bash
   cp .env.example .env
   # Edit .env and add your Discord token
   ```

5. **Run the bot**:

   ```bash
   # Using the CLI entry point
   todo-bot

   # Or using Python module
   python -m todo_bot.main
   ```

## Configuration

Create a `.env` file based on `.env.example`:

```env
# Discord Bot Token (required)
DISCORD_TOKEN=your_discord_bot_token_here

# Database Path (optional, defaults to data/tasks.db)
DATABASE_PATH=data/tasks.db

# Logging Level (optional)
# Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
# Default: INFO
LOG_LEVEL=INFO

# Command Sync (optional)
# Set to false to skip global command sync on startup (useful for development)
# Default: true
SYNC_COMMANDS_GLOBALLY=true

# Data Retention (optional)
# Number of days to keep old tasks (0 = keep forever)
# Default: 0 (disabled)
RETENTION_DAYS=0

# Auto Rollover (optional)
# Enable automatic midnight rollover of incomplete tasks
# Default: true
ENABLE_AUTO_ROLLOVER=true
```

## Automatic Task Rollover

The bot automatically rolls over incomplete tasks at midnight UTC. This ensures that tasks you didn't complete yesterday are automatically added to today's list while remaining on the previous day's list for reference.

### How it works

1. **At midnight UTC**, the bot checks for incomplete tasks from the previous day
2. **Incomplete tasks are copied** to the new day's list with their original priority
3. **Original tasks remain** on the previous day for historical tracking
4. **Duplicates are prevented** - if a task with the same description already exists on the new day, it won't be copied again

### Manual Rollover

You can also manually trigger a rollover using the `/rollover` command. This is useful if:
- You want to immediately copy yesterday's incomplete tasks
- The automatic rollover didn't run (e.g., bot was offline at midnight)
- You prefer to control when tasks roll over

### Disabling Auto-Rollover

Set `ENABLE_AUTO_ROLLOVER=false` in your environment to disable automatic midnight rollover. You can still use the `/rollover` command manually.

## Docker Deployment

The bot includes Docker support with a multi-stage build for minimal image size.

### Docker Features

- **Multi-stage build**: Minimal production image (~150MB)
- **Non-root user**: Enhanced security
- **Health checks**: Automatic container health monitoring
- **Volume persistence**: SQLite database persists across restarts
- **Resource limits**: 256MB memory, 0.5 CPU (configurable)

### Docker Commands

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the bot
docker-compose down

# Rebuild after code changes
docker-compose up -d --build

# View container status
docker-compose ps
```

### Manual Docker Build

```bash
# Build the image
docker build -t discord-todo-bot .

# Run the container
docker run -d \
  --name discord-todo-bot \
  -e DISCORD_TOKEN=your_token_here \
  -v todo-bot-data:/app/data \
  discord-todo-bot
```

## Discord Bot Setup

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to the "Bot" section and create a bot
4. Copy the bot token to your `.env` file
5. Go to "OAuth2" → "URL Generator"
6. Select scopes: `bot`, `applications.commands`
7. Select permissions: `Send Messages`, `Use Slash Commands`
8. Use the generated URL to invite the bot to your server

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests with coverage
pytest

# Run tests with verbose output
pytest -v

# Run a specific test file
pytest tests/test_task_model.py

# Run extended tests
pytest tests/test_cogs_extended.py
```

### Code Coverage

The project maintains **95% minimum code coverage**. Coverage reports are generated automatically during test runs.

### Linting

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
# Install ruff
pip install ruff

# Run linter
ruff check src/ tests/

# Auto-fix issues
ruff check src/ tests/ --fix

# Format code
ruff format src/ tests/
```

### Project Structure

```text
TodoList/
├── .github/
│   └── workflows/
│       └── tests.yml              # GitHub Actions CI/CD
├── src/
│   └── todo_bot/
│       ├── __init__.py            # Package exports
│       ├── main.py                # Entry point
│       ├── bot.py                 # Bot setup and lifecycle
│       ├── config.py              # Centralized configuration
│       ├── exceptions.py          # Custom exception hierarchy
│       ├── py.typed               # PEP 561 type marker
│       ├── cogs/
│       │   ├── __init__.py
│       │   └── tasks.py           # Slash commands
│       ├── models/
│       │   ├── __init__.py
│       │   └── task.py            # Task model
│       ├── storage/
│       │   ├── __init__.py
│       │   ├── base.py            # Abstract interface
│       │   └── sqlite.py          # SQLite implementation
│       ├── utils/
│       │   ├── __init__.py
│       │   └── formatting.py      # Display helpers
│       └── views/
│           ├── __init__.py
│           └── task_view.py       # Discord buttons
├── tests/
│   ├── conftest.py                # Test fixtures
│   ├── test_bot.py
│   ├── test_cogs.py
│   ├── test_cogs_extended.py      # Extended cog tests
│   ├── test_config.py             # Configuration tests
│   ├── test_formatting.py
│   ├── test_formatting_extended.py # Extended formatting tests
│   ├── test_main.py
│   ├── test_storage.py
│   ├── test_storage_extended.py   # Extended storage tests
│   ├── test_task_model.py
│   └── test_views.py
├── .clinerules                    # Cline AI configuration
├── .dockerignore                  # Docker ignore patterns
├── .env.example                   # Environment template
├── .gitignore
├── docker-compose.yml             # Docker Compose configuration
├── Dockerfile                     # Multi-stage Docker build
├── pyproject.toml                 # Project configuration
├── requirements.txt               # Dependencies
└── README.md
```

### Architecture

The bot uses an interface-based storage pattern for easy database swapping:

```python
# Abstract interface
class TaskStorage(ABC):
    async def add_task(...) -> Task
    async def get_tasks(...) -> List[Task]
    async def mark_done(...) -> bool
    ...

# SQLite implementation (can be swapped for PostgreSQL, MongoDB, etc.)
class SQLiteTaskStorage(TaskStorage):
    ...
```

Tasks are scoped by `(server_id, channel_id, user_id)` for isolation.

### Configuration Module

The `config.py` module provides centralized configuration:

```python
from todo_bot import BotConfig

# Load from environment variables
config = BotConfig.from_env()

# Access configuration
print(config.database_path)
print(config.log_level)
```

### Exception Hierarchy

Custom exceptions in `exceptions.py` for better error handling:

```text
TodoBotError          # Base exception
├── ValidationError   # Input validation errors
├── TaskNotFoundError # Task lookup failures
├── StorageError      # Base storage error
│   ├── StorageConnectionError
│   ├── StorageInitializationError
│   └── StorageOperationError
└── ConfigurationError # Configuration issues
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Ensure code coverage is at least 95%
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with [discord.py](https://discordpy.readthedocs.io/)
- Linting powered by [Ruff](https://docs.astral.sh/ruff/)
- CI/CD with GitHub Actions and [Codecov](https://codecov.io/)
- Inspired by the A/B/C priority method from time management principles
