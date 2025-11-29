# 🎵 Your Music Playlist Generator

> **AI-Powered Playlist Generator** - Describe a feeling, get a perfect Spotify playlist.

![Version](https://img.shields.io/badge/version-3.0.0-emerald)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![Next.js](https://img.shields.io/badge/next.js-14+-black)
![License](https://img.shields.io/badge/license-MIT-green)

<p align="center">
  <img src="https://img.shields.io/badge/LangGraph-Agent-purple" alt="LangGraph">
  <img src="https://img.shields.io/badge/Gemini-2.5-blue" alt="Gemini">
  <img src="https://img.shields.io/badge/Perplexity-Sonar-orange" alt="Perplexity">
  <img src="https://img.shields.io/badge/Spotify-API-1DB954" alt="Spotify">
</p>

---

## ✨ Features

- 🤖 **AI-Powered Curation** - Describe any mood, memory, or vibe in natural language
- 🔍 **Multi-Source Search** - Searches millions of sources via Perplexity AI
- 🎧 **Spotify Integration** - Creates real playlists directly in your account
- 📚 **Your Playground** - Library of generated playlists + Music Oracle Q&A
- 🚀 **Real-time Updates** - SSE streaming for live progress tracking
- 💾 **Persistent Storage** - SQLite + Redis for history and caching

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Playlist Generator Architecture             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌─────────────┐ │
│  │   Next.js    │────▶│   FastAPI    │────▶│  LangGraph  │ │
│  │   Frontend   │◀────│   Backend    │◀────│    Agent    │ │
│  └──────────────┘     └──────────────┘     └─────────────┘ │
│         │                    │                    │         │
│         │              ┌─────┴─────┐              │         │
│         │              │           │              │         │
│         ▼              ▼           ▼              ▼         │
│  ┌──────────┐   ┌──────────┐ ┌──────────┐ ┌───────────┐   │
│  │ Tailwind │   │  SQLite  │ │  Redis   │ │ MCP Server│   │
│  │   CSS    │   │    DB    │ │  Cache   │ │(Perplexity)│   │
│  └──────────┘   └──────────┘ └──────────┘ └───────────┘   │
│                                                   │         │
│                                                   ▼         │
│                                           ┌───────────┐    │
│                                           │  Spotify  │    │
│                                           │    API    │    │
│                                           └───────────┘    │
55: └─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (optional, for Redis)

### 1. Clone & Setup

```bash
git clone https://github.com/yourusername/playlist-generator.git
cd playlist-generator

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: .\venv\Scripts\activate  # Windows

# Install Python dependencies
pip install -r requirements.txt

# Install Node dependencies
npm install
```

### 2. Configure Environment

```bash
# Copy template
cp .env.example .env

# Edit with your API keys
nano .env  # or use your editor
```

**Required API Keys:**
- [Google Gemini](https://makersuite.google.com/app/apikey) - `GOOGLE_API_KEY`
- [Perplexity](https://www.perplexity.ai/settings/api) - `PPLX_API_KEY`
- [Spotify Developer](https://developer.spotify.com/dashboard) - `SPOTIPY_CLIENT_ID`, `SPOTIPY_CLIENT_SECRET`

### 3. Start Redis (Optional)

```bash
docker-compose up -d
```

### 4. Run the App

```bash
# Terminal 1: Backend
python -m src.api

# Terminal 2: Frontend
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) 🎉

---

## 📁 Project Structure

```
playlist-generator/
├── app/                    # Next.js Frontend
│   ├── page.tsx           # Main page (playlist generator)
│   ├── playground/        # Library + News + Music Oracle
│   ├── api-client.ts      # API client with SSE support
│   └── global.css         # Tailwind styles
│
├── src/                    # Python Backend
│   ├── api.py             # FastAPI endpoints
│   ├── agent.py           # LangGraph agent builder
│   ├── database.py        # SQLite operations
│   ├── cache.py           # Redis operations
│   ├── nodes/             # LangGraph nodes
│   │   ├── input_handler.py
│   │   ├── online_search.py
│   │   ├── playlist_generation.py
│   │   └── output.py
│   └── servers/           # MCP Server
│       └── online_searcher.py
│
├── data/                   # SQLite database (auto-created)
├── docker-compose.yml      # Redis container
├── requirements.txt        # Python dependencies
└── package.json           # Node dependencies
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/generate` | Start playlist generation |
| `GET` | `/status/{id}` | Get task status |
| `GET` | `/stream/{id}` | SSE real-time updates |
| `GET` | `/playlists` | Get playlist history |
| `GET` | `/playlists/{id}` | Get playlist with tracks |
| `POST` | `/news` | Get music news |
| `POST` | `/ask` | Ask Music Oracle |
| `GET` | `/health` | Health check |
| `GET` | `/stats` | Database stats |

Full API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🎨 Features in Detail

### 🎵 Playlist Generator
Describe any vibe in natural language:
- *"Late night drive through Tokyo with neon lights and melancholy beats"*
- *"Sunday morning coffee, jazz and rain on the window"*
- *"Workout playlist with aggressive electronic and no vocals"*

### 📚 Your Playground
- **Bookshelf Library** - Visual collection of your playlists
- **News Hub** - Latest news on your favorite artists
- **Music Oracle** - AI Q&A with conversation memory

### ⚡ Performance Optimizations
- Connection pooling (httpx)
- LRU cache for Spotify searches
- Batch LLM calls
- SSE instead of polling
- Warm-up on startup

---

## 🐳 Docker Deployment

```bash
# Build and run everything
docker-compose -f docker-compose.prod.yml up -d
```

---

## 🔧 Configuration

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_API_KEY` | Gemini API key | ✅ |
| `PPLX_API_KEY` | Perplexity API key | ✅ |
| `SPOTIPY_CLIENT_ID` | Spotify Client ID | ✅ |
| `SPOTIPY_CLIENT_SECRET` | Spotify Secret | ✅ |
| `SPOTIPY_REDIRECT_URI` | Spotify callback URL | ✅ |
| `REDIS_URL` | Redis connection | ❌ (fallback) |
| `NEXT_PUBLIC_API_URL` | Backend URL for frontend | ❌ |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open a Pull Request

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- [LangChain](https://langchain.com/) & [LangGraph](https://langchain-ai.github.io/langgraph/)
- [Perplexity AI](https://perplexity.ai/)
- [Google Gemini](https://ai.google.dev/)
- [Spotify Web API](https://developer.spotify.com/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Next.js](https://nextjs.org/)

---

<p align="center">
  Made with ❤️ and 🎵
</p>
