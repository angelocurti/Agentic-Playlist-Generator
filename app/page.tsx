"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
    Search, Music, Disc3, Sparkles, ExternalLink, Loader2, Zap, Radio,
    CheckCircle, Brain, Globe, Feather, Library, Clock, Play, Pause,
    Music2, Album, Headphones, ArrowRight
} from "lucide-react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import Link from "next/link";
import { playlistAPI, TaskStatus } from "./api-client";

// --- UTILS ---
function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

// --- CONFIGURAZIONE API ---
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// STEP DI LOADING
const LOADING_STEPS = [
    { step: 1, title: "ANALYZING VIBE", description: "Deconstructing cultural signals...", duration: 3000 },
    { step: 2, title: "SCANNING ARCHIVES", description: "Accessing global music history...", duration: 4000 },
    { step: 3, title: "CURATING ARTIFACTS", description: "Selecting essential tracks...", duration: 3000 },
    { step: 4, title: "PRESERVING CULTURE", description: "Finalizing playlist generation...", duration: 2000 },
];

const formatDuration = (seconds?: number): string => {
    if (!seconds || seconds === 0) return "3:30";
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
};

// --- COMPONENTS ---

const SpotifyTrackCard = ({ track, index }: { track: any; index: number }) => {
    const [isHovered, setIsHovered] = useState(false);

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05 }}
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
            className="group relative border-b border-white/10 last:border-0"
        >
            <div className={cn(
                "flex items-center gap-4 p-4 transition-all duration-300 cursor-pointer",
                "hover:bg-white/5"
            )}>
                {/* Track Number */}
                <div className="w-8 flex justify-center font-mono text-gray-500 text-sm">
                    {index + 1}
                </div>

                {/* Album Art (B&W) */}
                <div className="relative w-12 h-12 flex-shrink-0 grayscale group-hover:grayscale-0 transition-all duration-500">
                    {track.album_image ? (
                        <img
                            src={track.album_image}
                            alt={track.album || track.title}
                            className="w-full h-full object-cover"
                        />
                    ) : (
                        <div className="w-full h-full bg-neutral-900 flex items-center justify-center border border-white/10">
                            <Disc3 className="w-6 h-6 text-gray-600" />
                        </div>
                    )}
                </div>

                {/* Track Info */}
                <div className="flex-1 min-w-0">
                    <h4 className="font-bold text-white uppercase tracking-wider text-sm truncate">
                        {track.title}
                    </h4>
                    <p className="text-xs text-gray-400 uppercase tracking-widest truncate">
                        {track.artist}
                    </p>
                </div>

                {/* Duration */}
                <div className="flex items-center gap-4">
                    <span className="text-xs text-gray-600 font-mono">
                        {formatDuration(track.duration)}
                    </span>
                    {track.url && (
                        <a
                            href={track.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="opacity-0 group-hover:opacity-100 transition-opacity"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <ExternalLink className="w-4 h-4 text-white" />
                        </a>
                    )}
                </div>
            </div>
        </motion.div>
    );
};

// --- MAIN PAGE ---

export default function Home() {
    const [query, setQuery] = useState("");
    const [appState, setAppState] = useState<'idle' | 'searching' | 'results' | 'error'>('idle');
    const [currentStep, setCurrentStep] = useState(0);
    const [playlist, setPlaylist] = useState<any[]>([]);
    const [playlistUrl, setPlaylistUrl] = useState<string | null>(null);
    const [playlistTitle, setPlaylistTitle] = useState("");
    const [statusMessage, setStatusMessage] = useState("SYSTEM READY");
    const [taskId, setTaskId] = useState<string | null>(null);
    const [spotifyToken, setSpotifyToken] = useState<string | null>(null);

    // Auth Logic
    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        const token = params.get("spotify_token");
        if (token) {
            setSpotifyToken(token);
            localStorage.setItem("spotify_token", token);
            window.history.replaceState({}, document.title, "/");
        } else {
            const savedToken = localStorage.getItem("spotify_token");
            if (savedToken) setSpotifyToken(savedToken);
        }
    }, []);

    const handleSpotifyLogin = async () => {
        try {
            const res = await fetch(`${API_URL}/auth/login`);
            const data = await res.json();
            window.location.href = data.url;
        } catch (e) {
            console.error("Login failed", e);
        }
    };

    const handleLogout = () => {
        setSpotifyToken(null);
        localStorage.removeItem("spotify_token");
    };

    // Loading Simulation
    useEffect(() => {
        if (appState === 'searching' && currentStep < LOADING_STEPS.length) {
            const timer = setTimeout(() => {
                setCurrentStep(prev => Math.min(prev + 1, LOADING_STEPS.length));
            }, LOADING_STEPS[currentStep]?.duration || 2000);
            return () => clearTimeout(timer);
        }
    }, [appState, currentStep]);

    const handleSearch = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!query.trim()) return;

        setAppState('searching');
        setCurrentStep(1);
        setPlaylist([]);
        setPlaylistUrl(null);
        setStatusMessage("INITIALIZING...");

        try {
            const { task_id } = await playlistAPI.generate({
                description: query,
                spotify_token: spotifyToken || undefined
            });
            setTaskId(task_id);

            const result = await playlistAPI.waitForCompletion(task_id, (status) => {
                if (status.progress) setStatusMessage(status.progress.toUpperCase());
            });

            if (result.status === 'completed' && result.result) {
                setCurrentStep(LOADING_STEPS.length + 1);
                setPlaylistUrl(result.result.playlist_url);
                setPlaylistTitle(result.result.description || query);
                const tracks = result.result.tracks && result.result.tracks.length > 0
                    ? result.result.tracks
                    : [{ title: "Tracks loaded", artist: "Check Spotify", album: "", duration: 0 }];
                setPlaylist(tracks);
                setAppState('results');
                setStatusMessage("GENERATION COMPLETE");

                // Save to localStorage
                const savedPlaylists = JSON.parse(localStorage.getItem('playlists') || '[]');
                savedPlaylists.push({
                    id: task_id,
                    title: query,
                    url: result.result.playlist_url,
                    createdAt: new Date().toISOString(),
                    trackCount: result.result.track_count || tracks.length
                });
                localStorage.setItem('playlists', JSON.stringify(savedPlaylists));
            } else if (result.status === 'failed') {
                throw new Error(result.error || 'Generation failed');
            }
        } catch (err: any) {
            console.error("API Error:", err);
            setStatusMessage("SYSTEM ERROR");
            setAppState('error');
        }
    };

    const resetState = () => {
        setAppState('idle');
        setCurrentStep(0);
        setQuery("");
        setPlaylist([]);
        setPlaylistUrl(null);
        setStatusMessage("SYSTEM READY");
    };

    return (
        <main className="min-h-screen relative bg-black text-white font-sans selection:bg-white selection:text-black overflow-x-hidden">
            {/* Background Texture */}
            <div
                className="fixed inset-0 z-0 opacity-40 pointer-events-none"
                style={{
                    backgroundImage: `url('/assets/wall.png')`,
                    backgroundSize: 'cover',
                    backgroundPosition: 'center',
                    backgroundRepeat: 'no-repeat'
                }}
            />

            {/* Header / Nav */}
            <nav className="relative z-50 w-full px-6 py-6 flex justify-between items-center mix-blend-difference">
                <div className="text-xs font-mono tracking-widest text-gray-500">
                    V.3.0 // SYSTEM ONLINE
                </div>
                <div className="flex items-center gap-6">
                    {spotifyToken ? (
                        <button onClick={handleLogout} className="text-xs font-mono text-emerald-500 hover:text-emerald-400 uppercase tracking-wider">
                            [ CONNECTED ]
                        </button>
                    ) : (
                        <button onClick={handleSpotifyLogin} className="text-xs font-mono text-gray-500 hover:text-white uppercase tracking-wider transition-colors">
                            [ LOGIN SPOTIFY ]
                        </button>
                    )}
                    <Link href="/playground" className="text-xs font-mono text-white hover:text-gray-300 uppercase tracking-wider">
                        [ ENTER PLAYGROUND ]
                    </Link>
                </div>
            </nav>

            {/* Main Content */}
            <div className="relative z-10 flex flex-col items-center justify-center min-h-[80vh] px-4">

                {/* Hero Text */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 1 }}
                    className="text-center mb-12"
                >
                    <h1 className="font-['Permanent_Marker'] text-5xl md:text-8xl text-white leading-tight tracking-tighter drop-shadow-2xl opacity-90 rotate-[-1deg]">
                        CULTURE<br />PRESERVATION<br />SYSTEM
                    </h1>
                </motion.div>

                {/* Search Input */}
                <div className="w-full max-w-2xl relative group">
                    <form onSubmit={handleSearch} className="relative">
                        <input
                            type="text"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            placeholder="DESCRIBE THE VIBE..."
                            className="w-full bg-black/50 border-b-2 border-white/20 text-white text-xl md:text-2xl font-mono py-4 px-2 focus:outline-none focus:border-white transition-all placeholder:text-gray-700 text-center uppercase tracking-widest backdrop-blur-sm"
                            disabled={appState === 'searching'}
                        />
                        <button
                            type="submit"
                            disabled={!query.trim() || appState === 'searching'}
                            className="absolute right-0 top-1/2 -translate-y-1/2 p-2 opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                            <ArrowRight className="w-6 h-6 text-white" />
                        </button>
                    </form>

                    {/* Status Message */}
                    <div className="mt-4 text-center font-mono text-xs text-gray-500 tracking-[0.2em]">
                        {statusMessage}
                    </div>
                </div>

                {/* Results Area */}
                <AnimatePresence>
                    {appState === 'searching' && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="mt-16 w-full max-w-md"
                        >
                            {LOADING_STEPS.map((step) => (
                                <div key={step.step} className="flex items-center gap-4 mb-4 font-mono text-xs">
                                    <div className={cn(
                                        "w-2 h-2 bg-white transition-all duration-300",
                                        currentStep === step.step ? "animate-pulse" :
                                            currentStep > step.step ? "opacity-100" : "opacity-20"
                                    )} />
                                    <span className={cn(
                                        "tracking-widest transition-colors duration-300",
                                        currentStep === step.step ? "text-white" :
                                            currentStep > step.step ? "text-gray-500 line-through" : "text-gray-800"
                                    )}>
                                        {step.title}
                                    </span>
                                </div>
                            ))}
                        </motion.div>
                    )}

                    {appState === 'results' && (
                        <motion.div
                            initial={{ opacity: 0, y: 50 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="w-full max-w-3xl mt-20 mb-20 bg-black/80 border border-white/10 backdrop-blur-md p-8"
                        >
                            <div className="flex justify-between items-end mb-8 border-b border-white/20 pb-6">
                                <div>
                                    <h2 className="font-['Permanent_Marker'] text-3xl text-white mb-2 rotate-[-1deg]">
                                        {playlistTitle.toUpperCase()}
                                    </h2>
                                    <p className="font-mono text-xs text-gray-500 tracking-widest">
                                        GENERATED ARTIFACT // {playlist.length} TRACKS
                                    </p>
                                </div>
                                {playlistUrl && (
                                    <a
                                        href={playlistUrl}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="bg-white text-black px-6 py-2 font-mono text-xs font-bold uppercase tracking-widest hover:bg-gray-200 transition-colors"
                                    >
                                        OPEN SPOTIFY
                                    </a>
                                )}
                            </div>

                            <div className="space-y-1">
                                {playlist.map((track, i) => (
                                    <SpotifyTrackCard key={i} track={track} index={i} />
                                ))}
                            </div>

                            <div className="mt-8 text-center">
                                <button
                                    onClick={resetState}
                                    className="text-xs font-mono text-gray-500 hover:text-white uppercase tracking-widest underline decoration-1 underline-offset-4"
                                >
                                    INITIALIZE NEW SEARCH
                                </button>
                            </div>
                        </motion.div>
                    )}

                    {appState === 'error' && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="mt-16 text-center"
                        >
                            <div className="w-20 h-20 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-6 border border-red-500/30">
                                <Radio className="w-10 h-10 text-red-500" />
                            </div>
                            <h3 className="text-2xl font-mono font-bold text-red-400 mb-2 uppercase tracking-wider">SYSTEM MALFUNCTION</h3>
                            <p className="text-gray-400 mb-8 font-mono text-sm">{statusMessage}</p>
                            <button
                                onClick={resetState}
                                className="bg-white text-black px-8 py-3 font-mono text-xs font-bold uppercase tracking-widest hover:bg-gray-200 transition-colors"
                            >
                                RETRY
                            </button>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </main>
    );
}
