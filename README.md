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
- 🖥️ **Web Dashboard** – Single-page admin UI at `/ui/`

## Project Structure

```
ai-booking/
├── main.py                       # FastAPI application entry point
├── config.py                     # Configuration & environment variables
├── models.py                     # Pydantic data models
├── database.py                   # Supabase client initialization
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Container configuration
├── docker-compose.yml            # Multi-service Docker setup
├── .env.example                  # Environment variables template
│
├── frontend/
│   └── index.html                # Admin dashboard SPA (Tailwind CSS + Alpine.js)
│
├── services/
│   ├── whatsapp_service.py       # Meta WhatsApp Business API integration
│   ├── gemini_service.py         # Google Gemini AI conversation engine
│   ├── calendar_service.py       # Google Calendar availability & events
│   ├── booking_service.py        # Booking business logic
│   ├── reminder_service.py       # APScheduler-based reminders
│   └── supabase_service.py       # Supabase CRUD operations
│
├── routes/
│   ├── whatsapp.py               # WhatsApp webhook endpoints
│   ├── bookings.py               # Booking CRUD API
│   ├── consultants.py            # Consultant management API
│   └── admin.py                  # Admin operations API
│
└── utils/
    ├── logger.py                 # Structured logging
    ├── validators.py             # Input validation
    └── helpers.py                # Helper utilities
```

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

### 2. Set up Supabase

Run the following SQL in your Supabase SQL editor:

```sql
-- Users
create table users (
  id uuid primary key default gen_random_uuid(),
  phone_number text unique not null,
  name text,
  language text default 'en',
  created_at timestamptz default now()
);

-- Consultants
create table consultants (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  email text not null,
  calendar_id text,
  rate numeric,
  services text[],
  bio text,
  created_at timestamptz default now()
);

-- Availability (weekly schedule per consultant)
create table availability (
  id uuid primary key default gen_random_uuid(),
  consultant_id uuid references consultants(id) on delete cascade,
  day_of_week integer not null,   -- 0=Monday … 6=Sunday
  start_time time not null,
  end_time time not null,
  created_at timestamptz default now(),
  unique(consultant_id, day_of_week)
);

-- Bookings
create table bookings (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  consultant_id uuid references consultants(id) on delete cascade,
  start_time timestamptz not null,
  end_time timestamptz not null,
  status text default 'confirmed',
  notes text,
  service text,
  calendar_event_id text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Conversation history
create table conversation_history (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade unique,
  messages jsonb default '[]',
  context jsonb default '{}',
  updated_at timestamptz default now()
);
```

### 3. Run with Docker

```bash
docker-compose up --build
```

### 4. Run locally

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.  
Interactive docs at `http://localhost:8000/docs`.  
**Admin dashboard** at `http://localhost:8000/ui/`.

## WhatsApp Webhook Setup

1. In the [Meta Developer Console](https://developers.facebook.com/), set your webhook URL to:
   ```
   https://your-domain.com/webhook
   ```
2. Set the verify token to match `WHATSAPP_VERIFY_TOKEN` in your `.env`.
3. Subscribe to the `messages` webhook field.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check |
| GET/POST | `/webhook` | WhatsApp webhook |
| GET/POST | `/bookings` | List / create bookings |
| GET/PUT/POST | `/bookings/{id}` | Get / update / cancel booking |
| GET/POST | `/consultants` | List / create consultants |
| GET/PUT/DELETE | `/consultants/{id}` | Manage single consultant |
| POST | `/consultants/{id}/availability` | Set availability slot |
| GET | `/admin/stats` | Booking statistics |
| GET | `/admin/users` | List all users |
| GET | `/admin/bookings/all` | All bookings (admin) |
| GET | `/ui/` | Web admin dashboard |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `WHATSAPP_TOKEN` | ✅ | Meta permanent access token |
| `WHATSAPP_PHONE_NUMBER_ID` | ✅ | WhatsApp Business phone number ID |
| `WHATSAPP_VERIFY_TOKEN` | ✅ | Custom webhook verify token |
| `GEMINI_API_KEY` | ✅ | Google Gemini API key |
| `SUPABASE_URL` | ✅ | Supabase project URL |
| `SUPABASE_KEY` | ✅ | Supabase anon or service role key |
| `GOOGLE_CALENDAR_CREDENTIALS` | ✅ | Path or JSON of Google credentials |
| `TIMEZONE` | ❌ | App timezone (default: UTC) |
| `GEMINI_MODEL` | ❌ | Gemini model (default: gemini-1.5-flash) |
| `REMINDER_CHECK_INTERVAL_MINUTES` | ❌ | Reminder check frequency (default: 5) |

## License

Distributed under the MIT License.