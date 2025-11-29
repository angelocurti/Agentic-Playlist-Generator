# 🎵 Playlist Generator API

REST API per generare playlist musicali usando AI.

## 🚀 Avvio Server

```bash
# Installa dipendenze
pip install -r requirements.txt

# Avvia API server
python -m src.api
```

L'API sarà disponibile su: `http://localhost:8000`

## 📖 Documentazione Interattiva

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔌 Endpoints

### POST /generate
Genera una nuova playlist (asincrono).

**Request:**
```json
{
  "description": "Playlist con il vero suono della Dogo Gang",
  "duration_minutes": 60
}
```

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Playlist generation started. Use GET /status/{task_id} to check progress."
}
```

### GET /status/{task_id}
Verifica lo stato di una generazione.

**Response (in progress):**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "created_at": "2025-01-24T10:30:00",
  "progress": "Generazione in corso..."
}
```

**Response (completed):**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "created_at": "2025-01-24T10:30:00",
  "completed_at": "2025-01-24T10:32:30",
  "result": {
    "playlist_url": "https://open.spotify.com/playlist/xxxxx",
    "description": "Playlist con il vero suono della Dogo Gang"
  }
}
```

### GET /tasks
Lista gli ultimi task.

### DELETE /task/{task_id}
Elimina un task.

### GET /health
Controlla lo stato dell'API.

## 💻 Esempi di Utilizzo

### cURL

```bash
# Genera playlist
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Playlist energica per allenamento con rock e metal",
    "duration_minutes": 60
  }'

# Verifica stato
curl http://localhost:8000/status/YOUR_TASK_ID
```

### Python

```python
import requests
import time

# Genera playlist
response = requests.post(
    "http://localhost:8000/generate",
    json={
        "description": "Playlist rilassante con jazz e lofi",
        "duration_minutes": 45
    }
)

task_id = response.json()["task_id"]
print(f"Task ID: {task_id}")

# Polling dello stato
while True:
    status = requests.get(f"http://localhost:8000/status/{task_id}").json()
    
    print(f"Status: {status['status']} - {status.get('progress', '')}")
    
    if status["status"] in ["completed", "failed"]:
        break
    
    time.sleep(2)

# Risultato finale
if status["status"] == "completed":
    print(f"Playlist URL: {status['result']['playlist_url']}")
else:
    print(f"Error: {status.get('error')}")
```

### JavaScript/TypeScript

```javascript
// Genera playlist
const response = await fetch('http://localhost:8000/generate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    description: 'Playlist con il meglio degli anni 80',
    duration_minutes: 60
  })
});

const { task_id } = await response.json();

// Polling dello stato
const checkStatus = async () => {
  const statusRes = await fetch(`http://localhost:8000/status/${task_id}`);
  const status = await statusRes.json();
  
  console.log(`Status: ${status.status}`);
  
  if (status.status === 'completed') {
    console.log(`Playlist: ${status.result.playlist_url}`);
  } else if (status.status === 'processing') {
    setTimeout(checkStatus, 2000);
  }
};

checkStatus();
```

## 🛠️ Configurazione

L'API usa le stesse variabili d'ambiente del progetto:

- `GOOGLE_API_KEY` - Per Gemini
- `PPLX_API_KEY` - Per Perplexity
- `SPOTIPY_CLIENT_ID` - Spotify Client ID
- `SPOTIPY_CLIENT_SECRET` - Spotify Client Secret
- `SPOTIPY_REDIRECT_URI` - Spotify Redirect URI

## 📊 Note

- Le generazioni sono asincrone per non bloccare l'API
- Lo storage è in-memory (in produzione usa Redis o un DB)
- Il server supporta CORS per chiamate da frontend
- Auto-reload attivo in modalità development
