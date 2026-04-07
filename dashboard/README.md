# AI Booking – Admin Dashboard

Next.js 14 (App Router) + shadcn/ui admin dashboard for the [AI Booking](../) system.

## Pages

| Route | Description |
|-------|-------------|
| `/dashboard` | Stats overview + recent bookings |
| `/bookings` | Filter, search, and cancel bookings |
| `/consultants` | Add / edit / delete consultants |
| `/users` | List users and clear conversation history |

## Running Separately (Local Development)

The dashboard is a standalone Next.js app that talks to the FastAPI backend over HTTP.  
You can start it independently — **no Docker required**.

### 1. Install dependencies

```bash
cd dashboard
npm install
```

### 2. Configure the API URL

```bash
cp .env.local.example .env.local
```

The default `.env.local.example` already points to `http://localhost:8000`.  
Edit `.env.local` if your FastAPI backend runs on a different host or port.

### 3. Start the FastAPI backend

In a separate terminal, from the repo root:

```bash
pip install -r requirements.txt
uvicorn main:app --reload
# → API available at http://localhost:8000
```

### 4. Start the Next.js dev server

```bash
npm run dev
# → Dashboard available at http://localhost:3000
```

Open [http://localhost:3000](http://localhost:3000) in your browser.  
The dashboard auto-reloads as you edit source files.

---

## Running with Docker Compose

To run both services together from the repo root:

```bash
docker-compose up --build
```

| Service | URL |
|---------|-----|
| FastAPI backend | http://localhost:8000 |
| Next.js dashboard | http://localhost:3000 |

---

## Available Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server (hot-reload) |
| `npm run build` | Production build |
| `npm start` | Start production server (requires build first) |
| `npm run lint` | Run ESLint |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Base URL of the FastAPI backend |

## Stack

- [Next.js 14](https://nextjs.org/) – App Router, Server + Client Components
- [shadcn/ui](https://ui.shadcn.com/) – Component library (New York style)
- [Tailwind CSS 4](https://tailwindcss.com/) – Styling
- [TypeScript](https://www.typescriptlang.org/) – Type safety
- [Lucide React](https://lucide.dev/) – Icons
