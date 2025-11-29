const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// --- PLAYLIST TYPES ---

export interface PlaylistRequest {
    description: string;
    duration_minutes?: number;
    spotify_token?: string;
}

export interface Track {
    title: string;
    artist: string;
    album?: string;
    album_image?: string;
    duration?: number;
}

export interface PlaylistResult {
    playlist_url: string | null;
    duration_info: string | null;
    track_count: number;
    tracks?: Track[];
    description: string;
    generation_time?: number;
    success: boolean;
}

export interface TaskStatus {
    task_id: string;
    status: 'pending' | 'processing' | 'completed' | 'failed';
    created_at: string;
    completed_at?: string;
    result?: PlaylistResult;
    error?: string;
    error_details?: string;
    progress?: string;
}

// --- SSE STATUS (per streaming) ---
export interface SSEStatus {
    task_id: string;
    status: string;
    progress?: string;
    result?: PlaylistResult;
    error?: string;
}

// --- NEWS TYPES ---

export interface NewsRequest {
    query: string;
}

export interface NewsResponse {
    query: string;
    news: string;
}

// --- Q&A TYPES ---

export interface QuestionRequest {
    question: string;
}

export interface AnswerResponse {
    question: string;
    answer: string;
}

// --- PLAYLIST API ---

export const playlistAPI = {
    async generate(request: PlaylistRequest): Promise<{ task_id: string }> {
        const response = await fetch(`${API_BASE_URL}/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(request),
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }

        return response.json();
    },

    async getStatus(taskId: string): Promise<TaskStatus> {
        const response = await fetch(`${API_BASE_URL}/status/${taskId}`);

        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }

        return response.json();
    },

    /**
     * SSE Streaming - riceve aggiornamenti in tempo reale
     * Più efficiente del polling, il server invia dati solo quando cambiano
     */
    streamStatus(
        taskId: string,
        onStatus: (status: SSEStatus) => void,
        onError?: (error: Error) => void,
        onComplete?: () => void
    ): () => void {
        const eventSource = new EventSource(`${API_BASE_URL}/stream/${taskId}`);

        eventSource.addEventListener('status', (event) => {
            try {
                const data = JSON.parse(event.data) as SSEStatus;
                onStatus(data);

                // Chiudi automaticamente se completato/fallito
                if (data.status === 'completed' || data.status === 'failed') {
                    eventSource.close();
                    onComplete?.();
                }
            } catch (e) {
                console.error('SSE parse error:', e);
            }
        });

        eventSource.addEventListener('error', (event) => {
            console.error('SSE error:', event);
            eventSource.close();
            onError?.(new Error('SSE connection error'));
        });

        // Ritorna funzione per chiudere la connessione
        return () => {
            eventSource.close();
        };
    },

    /**
     * Polling tradizionale (fallback se SSE non supportato)
     */
    async pollUntilComplete(
        taskId: string,
        onProgress?: (status: TaskStatus) => void,
        maxAttempts = 120
    ): Promise<TaskStatus> {
        for (let i = 0; i < maxAttempts; i++) {
            const status = await this.getStatus(taskId);

            if (onProgress) {
                onProgress(status);
            }

            if (status.status === 'completed' || status.status === 'failed') {
                return status;
            }

            await new Promise(resolve => setTimeout(resolve, 2000));
        }

        throw new Error('Polling timeout: task did not complete in time');
    },

    /**
     * Metodo ibrido: prova SSE, fallback a polling se non supportato
     */
    async waitForCompletion(
        taskId: string,
        onProgress?: (status: TaskStatus | SSEStatus) => void
    ): Promise<TaskStatus> {
        return new Promise((resolve, reject) => {
            // Controlla se EventSource è supportato
            if (typeof EventSource !== 'undefined') {
                let resolved = false;

                const cleanup = this.streamStatus(
                    taskId,
                    (status) => {
                        onProgress?.(status as TaskStatus);

                        if (status.status === 'completed') {
                            resolved = true;
                            // Fetch stato completo per avere tutti i dati
                            this.getStatus(taskId).then(resolve).catch(reject);
                        } else if (status.status === 'failed') {
                            resolved = true;
                            this.getStatus(taskId).then(resolve).catch(reject);
                        }
                    },
                    (error) => {
                        if (!resolved) {
                            // Fallback a polling su errore SSE
                            console.log('SSE failed, falling back to polling...');
                            this.pollUntilComplete(taskId, onProgress as (status: TaskStatus) => void)
                                .then(resolve)
                                .catch(reject);
                        }
                    },
                    () => {
                        // onComplete - già gestito in onStatus
                    }
                );

                // Timeout di sicurezza
                setTimeout(() => {
                    if (!resolved) {
                        cleanup();
                        this.pollUntilComplete(taskId, onProgress as (status: TaskStatus) => void)
                            .then(resolve)
                            .catch(reject);
                    }
                }, 300000); // 5 minuti timeout
            } else {
                // Browser non supporta SSE, usa polling
                this.pollUntilComplete(taskId, onProgress as (status: TaskStatus) => void)
                    .then(resolve)
                    .catch(reject);
            }
        });
    },
};

// --- NEWS API ---

export const newsAPI = {
    async getNews(query: string): Promise<NewsResponse> {
        const response = await fetch(`${API_BASE_URL}/news`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query }),
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }

        return response.json();
    },
};

// --- Q&A API ---

export interface ConversationMessage {
    type: 'user' | 'ai';
    content: string;
}

export const qaAPI = {
    async askQuestion(question: string, conversationHistory?: ConversationMessage[]): Promise<AnswerResponse> {
        const response = await fetch(`${API_BASE_URL}/ask`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question,
                conversation_history: conversationHistory || []
            }),
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }

        return response.json();
    },
};

// --- HEALTH CHECK ---

export const healthAPI = {
    async check(): Promise<{ status: string; timestamp: string; active_tasks: number; http_pool_active?: boolean }> {
        const response = await fetch(`${API_BASE_URL}/health`);

        if (!response.ok) {
            throw new Error('API is not healthy');
        }

        return response.json();
    },
};
