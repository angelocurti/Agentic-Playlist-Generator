import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./global.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
    title: "Your Music Playlist Generator",
    description: "Create perfect playlists powered by AI. Describe your mood, moment, or memory and let our intelligent agents curate your soundtrack.",
    keywords: ["playlist", "AI", "music", "Spotify", "curation", "mood", "generator"],
    authors: [{ name: "Playlist Generator" }],
    openGraph: {
        title: "Your Music Playlist Generator",
        description: "Create perfect playlists powered by AI",
        type: "website",
    },
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en" className="dark">
            <head>
                <link rel="icon" href="/favicon.ico" />
                {/* Google Fonts: Inter for UI, Permanent Marker for Graffiti */}
                <link rel="preconnect" href="https://fonts.googleapis.com" />
                <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
                <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;900&family=Permanent+Marker&display=swap" rel="stylesheet" />
            </head>
            <body className={`${inter.className} bg-black text-white antialiased selection:bg-white selection:text-black`}>
                {children}
            </body>
        </html>
    );
}
