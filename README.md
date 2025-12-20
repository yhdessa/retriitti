# 🎵 Retriitti Music Bot

A Telegram bot for managing and sharing your personal music collection. Upload tracks, organize by artist and album, search your library, and download entire collections with one click.

## What It Does

**Retriitti** is your personal music library bot that:

- 📤 **Stores your music** - Upload tracks directly through Telegram
- 🔍 **Smart search** - Find tracks by artist, title, or album
- 📚 **Auto-organizes** - Automatically fetches album info from MusicBrainz
- 📥 **Bulk downloads** - Download entire albums or artist discographies with one click
- 🎤 **Artist info** - Get biographies, stats, and top tracks from Genius
- 🔐 **Admin-only uploads** - Secure access control for uploading

Perfect for music collectors who want to organize and share their music collection via Telegram.

---

## Quick Start

### 1. Prerequisites

- **Docker & Docker Compose** installed
- **Telegram Bot Token** - Get from [@BotFather](https://t.me/BotFather)
- **Your Telegram ID** - Get from [@userinfobot](https://t.me/userinfobot)

### 2. Installation

```bash
git clone https://github.com/yhdessa/retriitti.git
cd retriitti

cp .env.example .env

nano .env
```

### 3. Configure

Edit `.env` file:

```bash
BOT_TOKEN=your_bot_token_from_botfather
ADMIN_IDS=your_telegram_user_id

DB_PASSWORD=your_secure_password

GENIUS_API_TOKEN=your_genius_token
```

### 4. Run

```bash
docker-compose up -d

docker-compose ps

docker-compose logs -f bot
```

That's it! Send `/start` to your bot in Telegram.

---

## How to Use

### Basic Commands

```
/start      - Start the bot
/help       - Show help
/browse     - Browse your music by artist
/stats      - View library statistics
/artist     - Get artist information (e.g., /artist Queen)
```

### Upload Music (Admins Only)

1. Send an audio file to the bot
2. Bot extracts metadata (artist, title, duration)
3. Bot automatically searches for album info
4. Track is saved to your library

**Tip:** Send files as "Audio" (not "Document") for best results.

### Search & Download

**Search:**
```
Just type: Bohemian Rhapsody
Bot shows results with download buttons
```

**Browse:**
```
/browse
→ Select artist
→ View albums
→ Click track to download
```

**Bulk download:**
- Click **[📥 Download All]** to get all tracks by an artist
- Click **[📥 Album]** to get a complete album

---

## Features

### For Users
- 🔍 Search by artist, title, or album
- 📚 Browse organized by artist and album
- 📥 Download individual tracks or entire collections
- 🎤 View artist bios, stats, and popular tracks
- 🏠 Quick navigation with home button

### For Admins
- 📤 Upload tracks with automatic metadata extraction
- 💿 Auto-fetch album info from MusicBrainz
- 🔄 Bulk update missing metadata with `/enrich_all`
- 📊 View detailed statistics
- 🔐 Full access control

---

## Project Structure

```
retriitti/
├── docker-compose.yml      # Docker services
├── Dockerfile             # Bot container
├── requirements.txt       # Python dependencies
├── .env.example          # Environment template
└── src/
    ├── bot.py            # Main bot
    ├── config.yaml       # Configuration
    ├── handlers/         # Command handlers
    ├── db/              # Database models
    └── utils/           # Helper utilities
```

---

## Technology

- **Python 3.11** with aiogram (async Telegram bot framework)
- **PostgreSQL** for storing tracks
- **Docker** for easy deployment
- **MusicBrainz API** for album metadata
- **Genius API** for artist information

---

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `BOT_TOKEN` | Yes | Telegram bot token from @BotFather |
| `ADMIN_IDS` | Yes | Comma-separated Telegram user IDs (e.g., `123456789,987654321`) |
| `DB_PASSWORD` | Yes | PostgreSQL password |
| `GENIUS_API_TOKEN` | No | For `/artist` command (get from [genius.com](https://genius.com/api-clients)) |

### config.yaml

Customize bot behavior:

```yaml
# Auto-fetch albums on upload
metadata:
  auto_fetch_album: true

# Search settings
search:
  max_results: 5

# Items per page
pagination:
  tracks_per_page: 8
  albums_per_page: 5
```

---

## Maintenance

### View Logs

```bash
docker-compose logs -f bot
```

### Restart Bot

```bash
docker-compose restart
```

### Backup Database

```bash
docker-compose exec postgres pg_dump -U postgres music_bot > backup.sql
```

### Update Bot

```bash
git pull
docker-compose down
docker-compose up -d --build
```
---

## Troubleshooting

### Bot not responding?

```bash
docker-compose ps
docker-compose logs bot
docker-compose restart
```

### Can't upload tracks?

- Verify your Telegram ID is in `ADMIN_IDS`
- Check `.env` file has correct user ID
- Restart bot after changing `.env`

### Database connection error?

- Check `DB_PASSWORD` in `.env`
- Ensure PostgreSQL container is running: `docker-compose ps`

---

## Security

- **Admin IDs** stored securely in `.env` (not in code)
- **Database credentials** in `.env` file
- **Never commit** `.env` to git (it's in `.gitignore`)
