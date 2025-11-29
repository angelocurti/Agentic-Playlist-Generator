"""
Script di test per l'API di generazione playlist.
Esempio di utilizzo dell'API tramite requests.
"""

import requests
import time
import json

# Base URL dell'API
BASE_URL = "http://localhost:8000"


def test_health():
    """Test health endpoint"""
    print("\n" + "="*60)
    print("🏥 Testing Health Endpoint")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200


def generate_playlist(description: str, duration_minutes: int = 60):
    """Genera una playlist e ritorna il task_id"""
    print("\n" + "="*60)
    print("🎵 Generating Playlist")
    print("="*60)
    print(f"Description: {description}")
    print(f"Duration: {duration_minutes} minutes")
    
    response = requests.post(
        f"{BASE_URL}/generate",
        json={
            "description": description,
            "duration_minutes": duration_minutes
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        task_id = data["task_id"]
        print(f"\n✅ Task created successfully!")
        print(f"Task ID: {task_id}")
        return task_id
    else:
        print(f"\n❌ Error: {response.status_code}")
        print(response.text)
        return None


def check_status(task_id: str, wait: bool = False):
    """Verifica lo stato di un task"""
    print("\n" + "="*60)
    print(f"📊 Checking Status: {task_id}")
    print("="*60)
    
    while True:
        response = requests.get(f"{BASE_URL}/status/{task_id}")
        
        if response.status_code == 200:
            data = response.json()
            status = data["status"]
            progress = data.get("progress", "N/A")
            
            print(f"Status: {status}")
            print(f"Progress: {progress}")
            
            if status == "completed":
                print("\n✅ Playlist completata!")
                result = data.get("result", {})
                playlist_url = result.get("playlist_url")
                if playlist_url:
                    print(f"🎵 Playlist URL: {playlist_url}")
                print(f"\nFull result:\n{json.dumps(result, indent=2)}")
                return data
            
            elif status == "failed":
                print(f"\n❌ Generazione fallita")
                error = data.get("error")
                if error:
                    print(f"Error: {error}")
                return data
            
            elif status in ["pending", "processing"]:
                if not wait:
                    return data
                # Continua polling
                print("⏳ Waiting...")
                time.sleep(3)
            
        else:
            print(f"❌ Error: {response.status_code}")
            return None


def list_tasks():
    """Lista i task recenti"""
    print("\n" + "="*60)
    print("📋 Recent Tasks")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/tasks?limit=5")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Total tasks: {data['total']}")
        print("\nRecent tasks:")
        for task in data['tasks']:
            print(f"  - {task['task_id'][:8]}... | {task['status']} | {task['created_at']}")
    else:
        print(f"❌ Error: {response.status_code}")


def main():
    """Main test flow"""
    print("\n" + "="*60)
    print("🎵 Playlist Generator API - Test Client")
    print("="*60)
    
    # 1. Health check
    if not test_health():
        print("\n❌ API non raggiungibile. Assicurati che il server sia avviato:")
        print("   python -m src.api")
        return
    
    # 2. Genera playlist
    task_id = generate_playlist(
        description="Playlist con il vero suono della Dogo Gang, solo cose da intenditore",
        duration_minutes=60
    )
    
    if not task_id:
        print("\n❌ Errore nella creazione del task")
        return
    
    # 3. Polling dello stato con attesa
    check_status(task_id, wait=True)
    
    # 4. Lista task
    list_tasks()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except requests.exceptions.ConnectionError:
        print("\n\n❌ Cannot connect to API. Make sure the server is running:")
        print("   python -m src.api")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
