"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { ArrowLeft, Send, Music, Calendar, User } from "lucide-react";
import Link from "next/link";

export default function Playground() {
    const [activeTab, setActiveTab] = useState<'chat' | 'concerts' | 'about'>('chat');
    const [chatMessages, setChatMessages] = useState<Array<{ role: 'user' | 'ai'; content: string }>>([]);
    const [inputMessage, setInputMessage] = useState("");

    const handleSendMessage = (e: React.FormEvent) => {
        e.preventDefault();
        if (!inputMessage.trim()) return;

        setChatMessages(prev => [...prev, { role: 'user', content: inputMessage }]);
        setInputMessage("");

        // Simulate AI response
        setTimeout(() => {
            setChatMessages(prev => [...prev, {
                role: 'ai',
                content: "This feature is under development. Stay tuned for intelligent music conversations!"
            }]);
        }, 1000);
    };

    return (
        <main className="min-h-screen relative bg-black text-white font-sans selection:bg-white selection:text-black">
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

            {/* Header */}
            <nav className="relative z-50 w-full px-6 py-6 flex justify-between items-center border-b border-white/10">
                <Link href="/" className="text-xs font-mono text-white hover:text-gray-300 uppercase tracking-wider flex items-center gap-2">
                    <ArrowLeft className="w-4 h-4" />
                    [ BACK TO SYSTEM ]
                </Link>
                <div className="text-xs font-mono tracking-widest text-gray-500">
                    PLAYGROUND // V.3.0
                </div>
            </nav>

            {/* Main Content */}
            <div className="relative z-10 px-6 py-8">
                {/* Tab Navigation */}
                <div className="max-w-7xl mx-auto mb-8 flex gap-4 border-b border-white/10 pb-4">
                    <button
                        onClick={() => setActiveTab('chat')}
                        className={`px-6 py-2 font-mono text-xs uppercase tracking-widest transition-all ${activeTab === 'chat'
                                ? 'bg-white text-black'
                                : 'text-gray-500 hover:text-white border border-white/20'
                            }`}
                    >
                        <Music className="w-4 h-4 inline mr-2" />
                        CHAT
                    </button>
                    <button
                        onClick={() => setActiveTab('concerts')}
                        className={`px-6 py-2 font-mono text-xs uppercase tracking-widest transition-all ${activeTab === 'concerts'
                                ? 'bg-white text-black'
                                : 'text-gray-500 hover:text-white border border-white/20'
                            }`}
                    >
                        <Calendar className="w-4 h-4 inline mr-2" />
                        CONCERTS
                    </button>
                    <button
                        onClick={() => setActiveTab('about')}
                        className={`px-6 py-2 font-mono text-xs uppercase tracking-widest transition-all ${activeTab === 'about'
                                ? 'bg-white text-black'
                                : 'text-gray-500 hover:text-white border border-white/20'
                            }`}
                    >
                        <User className="w-4 h-4 inline mr-2" />
                        ABOUT
                    </button>
                </div>

                {/* Content Panels */}
                <div className="max-w-7xl mx-auto">
                    {/* CHAT PANEL */}
                    {activeTab === 'chat' && (
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="bg-black/80 border border-white/10 backdrop-blur-md p-8"
                        >
                            <div className="mb-6">
                                <h2 className="font-['Permanent_Marker'] text-4xl text-white mb-2 rotate-[-1deg]">
                                    MUSIC INTELLIGENCE
                                </h2>
                                <p className="font-mono text-xs text-gray-500 tracking-widest">
                                    ASK ANYTHING ABOUT MUSIC // POWERED BY AI
                                </p>
                            </div>

                            {/* Chat Messages */}
                            <div className="h-[400px] overflow-y-auto mb-6 space-y-4 border border-white/10 p-4 bg-black/50">
                                {chatMessages.length === 0 ? (
                                    <div className="h-full flex items-center justify-center text-gray-600 font-mono text-xs uppercase tracking-widest">
                                        START A CONVERSATION...
                                    </div>
                                ) : (
                                    chatMessages.map((msg, i) => (
                                        <div
                                            key={i}
                                            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                                        >
                                            <div
                                                className={`max-w-[70%] p-4 font-mono text-sm ${msg.role === 'user'
                                                        ? 'bg-white text-black'
                                                        : 'bg-white/10 text-white border border-white/20'
                                                    }`}
                                            >
                                                {msg.content}
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>

                            {/* Input */}
                            <form onSubmit={handleSendMessage} className="flex gap-4">
                                <input
                                    type="text"
                                    value={inputMessage}
                                    onChange={(e) => setInputMessage(e.target.value)}
                                    placeholder="ASK ABOUT MUSIC..."
                                    className="flex-1 bg-black/50 border border-white/20 text-white font-mono text-sm py-3 px-4 focus:outline-none focus:border-white transition-all placeholder:text-gray-700 uppercase tracking-wider"
                                />
                                <button
                                    type="submit"
                                    disabled={!inputMessage.trim()}
                                    className="bg-white text-black px-6 py-3 font-mono text-xs font-bold uppercase tracking-widest hover:bg-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    <Send className="w-4 h-4" />
                                </button>
                            </form>
                        </motion.div>
                    )}

                    {/* CONCERTS PANEL */}
                    {activeTab === 'concerts' && (
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="bg-black/80 border border-white/10 backdrop-blur-md p-8"
                        >
                            <div className="mb-6">
                                <h2 className="font-['Permanent_Marker'] text-4xl text-white mb-2 rotate-[-1deg]">
                                    LIVE EVENTS
                                </h2>
                                <p className="font-mono text-xs text-gray-500 tracking-widest">
                                    CONCERT BOOKING SYSTEM // COMING SOON
                                </p>
                            </div>

                            <div className="h-[500px] flex flex-col items-center justify-center border border-white/10 bg-black/50 p-12">
                                <Calendar className="w-24 h-24 text-gray-700 mb-6" />
                                <h3 className="font-mono text-xl text-white uppercase tracking-wider mb-4">
                                    FEATURE IN DEVELOPMENT
                                </h3>
                                <p className="text-gray-500 font-mono text-sm text-center max-w-md leading-relaxed">
                                    Soon you'll be able to discover and book concerts directly from this platform.
                                    We're building a seamless experience to connect music lovers with live performances.
                                </p>
                                <div className="mt-8 px-6 py-3 border border-white/20 font-mono text-xs text-gray-500 uppercase tracking-widest">
                                    STAY TUNED
                                </div>
                            </div>
                        </motion.div>
                    )}

                    {/* ABOUT PANEL */}
                    {activeTab === 'about' && (
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="bg-black/80 border border-white/10 backdrop-blur-md p-8"
                        >
                            <div className="mb-6">
                                <h2 className="font-['Permanent_Marker'] text-4xl text-white mb-2 rotate-[-1deg]">
                                    MANIFESTO
                                </h2>
                                <p className="font-mono text-xs text-gray-500 tracking-widest">
                                    WHY THIS EXISTS
                                </p>
                            </div>

                            <div className="space-y-8 max-w-3xl">
                                <div className="border-l-2 border-white/20 pl-6">
                                    <p className="text-gray-300 leading-relaxed text-lg mb-4">
                                        I'm a passionate explorer of both <span className="text-white font-bold">artificial intelligence</span> and,
                                        even more deeply, <span className="text-white font-bold">music</span>.
                                    </p>
                                    <p className="text-gray-300 leading-relaxed text-lg mb-4">
                                        This project was born from a simple belief: <span className="text-white italic">music discovery should capture
                                            the full depth of what you're seeking in any given moment</span>. Not just genres or moods, but the
                                        cultural context, the emotional nuance, the sonic textures that make a moment truly resonate.
                                    </p>
                                    <p className="text-gray-300 leading-relaxed text-lg mb-4">
                                        Traditional playlist generators fall short. They categorize, but they don't <span className="text-white font-bold">understand</span>.
                                        They recommend, but they don't <span className="text-white font-bold">preserve</span>.
                                    </p>
                                    <p className="text-gray-300 leading-relaxed text-lg">
                                        This Culture Preservation System uses advanced AI to analyze the essence of your request—diving into
                                        musical history, cultural movements, and sonic characteristics to curate playlists that truly
                                        capture what you're looking for. It's not just about finding songs; it's about
                                        <span className="text-white font-bold"> preserving and sharing musical culture</span>.
                                    </p>
                                </div>

                                <div className="border-t border-white/10 pt-8">
                                    <h3 className="font-mono text-sm uppercase tracking-widest text-gray-500 mb-4">
                                        BUILT WITH
                                    </h3>
                                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                                        <div className="border border-white/10 p-4 bg-black/50">
                                            <p className="font-mono text-xs text-white uppercase tracking-wider">LangGraph</p>
                                            <p className="font-mono text-xs text-gray-600 mt-1">AGENTIC AI</p>
                                        </div>
                                        <div className="border border-white/10 p-4 bg-black/50">
                                            <p className="font-mono text-xs text-white uppercase tracking-wider">Perplexity</p>
                                            <p className="font-mono text-xs text-gray-600 mt-1">DEEP RESEARCH</p>
                                        </div>
                                        <div className="border border-white/10 p-4 bg-black/50">
                                            <p className="font-mono text-xs text-white uppercase tracking-wider">Spotify API</p>
                                            <p className="font-mono text-xs text-gray-600 mt-1">MUSIC PLATFORM</p>
                                        </div>
                                        <div className="border border-white/10 p-4 bg-black/50">
                                            <p className="font-mono text-xs text-white uppercase tracking-wider">Next.js</p>
                                            <p className="font-mono text-xs text-gray-600 mt-1">FRONTEND</p>
                                        </div>
                                        <div className="border border-white/10 p-4 bg-black/50">
                                            <p className="font-mono text-xs text-white uppercase tracking-wider">FastAPI</p>
                                            <p className="font-mono text-xs text-gray-600 mt-1">BACKEND</p>
                                        </div>
                                        <div className="border border-white/10 p-4 bg-black/50">
                                            <p className="font-mono text-xs text-white uppercase tracking-wider">Python</p>
                                            <p className="font-mono text-xs text-gray-600 mt-1">CORE LOGIC</p>
                                        </div>
                                    </div>
                                </div>

                                <div className="text-center pt-8 border-t border-white/10">
                                    <p className="font-mono text-xs text-gray-600 uppercase tracking-widest">
                                        MADE FOR MUSIC LOVERS, BY A MUSIC LOVER
                                    </p>
                                    <p className="font-mono text-xs text-gray-800 mt-2">
                                        © 2025 CULTURE PRESERVATION SYSTEM
                                    </p>
                                </div>
                            </div>
                        </motion.div>
                    )}
                </div>
            </div>
        </main>
    );
}
