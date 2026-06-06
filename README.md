# AI Booking 🤖📱

An AI-powered WhatsApp appointment booking system built with Python/FastAPI, Google Gemini, Meta WhatsApp Business API.

## Features

- 💬 **Natural Language Booking** – Understand requests like "I want to book next Tuesday afternoon"
- 📱 **WhatsApp Integration** – Two-way messaging via Meta Business API
- 📅 **Google Calendar Sync** – Real-time consultant availability
- ⏰ **Automated Reminders** – WhatsApp reminders 24h and 1h before appointments
- 🌍 **Multi-language** – Auto-detect and respond in the user's language
- 👥 **Multi-consultant** – Support multiple consultants with individual calendars
- 🔧 **Admin API** – Manage consultants, availability, and view statistics

## Prerequisites

- Python 3.11+
- Docker & Docker Compose (for containerised deployment)

## Quick Start

### 1. Clone and configure

```bash
git clone https://github.com/ismatim/ai-booking.git
cd ai-booking
cp .env.example .env
# Edit .env with your credentials
```

### 3. Run with Docker

```bash
docker-compose up --build
```

### 4. Run locally

**FastAPI backend:**

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.  
Interactive docs at `http://localhost:8000/docs`.

#### License

Distributed under the MIT License.
