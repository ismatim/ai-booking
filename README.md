# AI Booking 🤖📱

An AI-powered WhatsApp appointment booking system built with Python/FastAPI, Google Gemini, Meta WhatsApp Business API, and Supabase.

## Features

- 💬 **Natural Language Booking** – Understand requests like "I want to book next Tuesday afternoon"
- 📱 **WhatsApp Integration** – Two-way messaging via Meta Business API
- 🤖 **Google Gemini AI** – Multi-turn conversation with context memory
- 📅 **Google Calendar Sync** – Real-time consultant availability
- 💾 **Supabase Database** – Full data persistence (users, bookings, history)
- ⏰ **Automated Reminders** – WhatsApp reminders 24h and 1h before appointments
- 🌍 **Multi-language** – Auto-detect and respond in the user's language
- 👥 **Multi-consultant** – Support multiple consultants with individual calendars
- 🔧 **Admin API** – Manage consultants, availability, and view statistics
- 🖥️ **Web Dashboard** – Next.js + shadcn/ui admin dashboard (standalone, port 3000)

## Prerequisites

- Python 3.11+
- Docker & Docker Compose (for containerised deployment)
- [Meta WhatsApp Business API](https://developers.facebook.com/) account
- [Google Gemini API](https://aistudio.google.com/app/apikey) key
- [Supabase](https://supabase.com/) project
- [Google Cloud](https://console.cloud.google.com/) project with Calendar API enabled

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

**Next.js dashboard (separate terminal):**

```bash
cd dashboard
npm install
cp .env.local.example .env.local   # points to http://localhost:8000 by default
npm run dev
```

The admin dashboard will be available at `http://localhost:3000`.  
See [`dashboard/README.md`](dashboard/README.md) for full dashboard documentation.

Distributed under the MIT License.

