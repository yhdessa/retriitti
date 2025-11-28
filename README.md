# retriitti
Project for DevOps practice

SHMusicBot

A Telegram bot for storing and delivering music files upon user request.
The bot uses a database to store track information and provides convenient search by title, artist, or tags.

---

Features:
-    Uploading music files to the database (by the administrator)
-    Searching for tracks:
-    by title
-    by artist
-    by keywords
-    Sending audio files to users
-    Storing track metadata:
    -    title
    -    author
    -    genre / tags
    -    path/file ID
-    Bot action logs
-    Ability to extend functionality

---

Technologies:
-    Python 3.10+
-    Aiogram / PyTelegramBotAPI — Telegram Bot API
-    PostgreSQL / SQLite — database
-    SQLAlchemy / asyncpg — ORM/driver

---

How to run locally

1. Clone the project

2. Create a virtual environment

```
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies

```
pip install -r requirements.txt
```

4. Configure the environment

Create a .env file (one in src directory and one in root directory):

```
BOT_TOKEN=your_token # this one for src
```

```
DB_USER=... # this for root 
DB_PASSWORD=...
DB_NAME=...
```

5. Run the bot

```
python bot/main.py
```
