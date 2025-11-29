#!/bin/bash
# Build script for Render deployment

echo "🔧 Starting build process..."

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Create data directory for SQLite
echo "📁 Creating data directory..."
mkdir -p data

# Create assets directory for frontend
echo "🎨 Creating assets directory..."
mkdir -p public/assets

echo "✅ Build complete!"
