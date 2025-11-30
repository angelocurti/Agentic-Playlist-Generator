# 🚀 Deployment Guide - Render.com

Complete guide to deploy the Culture Preservation System on Render.

## 📋 Prerequisites

1. GitHub account
2. Render.com account (free tier available)
3. Push your code to GitHub
4. Spotify Developer App credentials
5. Perplexity API key
6. Google API key

## 🔧 Step 1: Prepare Your Repository

Make sure all files are committed to GitHub:

```bash
git add .
git commit -m "Prepare for Render deployment"
git push origin main
```

## 🌐 Step 2: Deploy Backend (FastAPI)

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Configure:
   - **Name**: `playlist-generator-api`
   - **Region**: Frankfurt (or closest to you)
   - **Branch**: `main`
   - **Root Directory**: Leave empty
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn src.api:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free

5. **Environment Variables** (click "Advanced" → "Add Environment Variable"):
   ```
   PPLX_API_KEY=your_perplexity_api_key
   GOOGLE_API_KEY=your_google_api_key
   SPOTIPY_CLIENT_ID=your_spotify_client_id
   SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
   SPOTIPY_REDIRECT_URI=https://YOUR-BACKEND-URL.onrender.com/auth/callback
   ```

6. Click **"Create Web Service"**

7. **IMPORTANT**: After deployment, copy your backend URL (e.g., `https://playlist-generator-api.onrender.com`)

## 🎨 Step 3: Deploy Frontend (Next.js)

**IMPORTANT**: Next.js with App Router must be deployed as a **Web Service** (not Static Site) because it requires server-side rendering.

1. In Render Dashboard, click **"New +"** → **"Web Service"**
2. Connect the same GitHub repository
3. Configure:
   - **Name**: `playlist-generator-frontend`
   - **Region**: Frankfurt (or closest to you)
   - **Branch**: `main`
   - **Root Directory**: Leave empty
   - **Runtime**: `Node`
   - **Build Command**: `npm install && npm run build`
   - **Start Command**: `npm start`
   - **Plan**: Free

4. **Environment Variables** (click "Advanced" → "Add Environment Variable"):
   ```
   NODE_VERSION=18
   NEXT_PUBLIC_API_URL=https://YOUR-BACKEND-URL.onrender.com
   ```
   (Replace with your actual backend URL from Step 2)

5. Click **"Create Web Service"**

**Note**: The `start.js` script automatically handles the PORT environment variable provided by Render.

## 🎵 Step 4: Update Spotify Developer Dashboard

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Select your app
3. Click **"Settings"**
4. Under **"Redirect URIs"**, add:
   ```
   https://YOUR-BACKEND-URL.onrender.com/auth/callback
   ```
5. Click **"Save"**

## ✅ Step 5: Verify Deployment

1. Wait for both services to finish deploying (check Render dashboard)
2. Visit your frontend URL: `https://playlist-generator-frontend.onrender.com`
3. Check browser console for any errors
4. Test the Spotify login flow
5. Generate a test playlist
6. Check backend and frontend logs in Render dashboard if issues occur

**Tip**: On the free tier, services may take 30-60 seconds to wake up on first request after inactivity.

## ⚠️ Important Notes

### Free Tier Limitations
- **Backend**: Spins down after 15 minutes of inactivity
- **First request**: May take 30-60 seconds to wake up
- **Solution**: Consider upgrading to paid tier ($7/month) for always-on service

### Database Persistence
- SQLite database is stored in `/data` directory
- On free tier, data persists but may be lost on redeploys
- **Solution**: Use Render's persistent disk (paid feature) or migrate to PostgreSQL

### Environment Variables
- Never commit `.env` file to GitHub
- Always use Render's environment variable settings
- Update `SPOTIPY_REDIRECT_URI` to match your backend URL

## 🔄 Updating Your Deployment

After making changes:

```bash
git add .
git commit -m "Update: description of changes"
git push origin main
```

Render will automatically redeploy both services.

## 🐛 Troubleshooting

### Backend won't start
- Check logs in Render dashboard
- Verify all environment variables are set
- Ensure `requirements.txt` is complete

### Frontend won't start or shows errors
- Check logs in Render dashboard for build/start errors
- Verify `NODE_VERSION` is set to `18` or higher
- Ensure `NEXT_PUBLIC_API_URL` environment variable is set correctly
- Check that the build completed successfully (look for "Compiled successfully")

### Frontend can't connect to backend
- Verify `NEXT_PUBLIC_API_URL` is correct (should be your backend Render URL)
- Check CORS settings in `src/api.py`
- Ensure backend is running (check Render dashboard)
- Verify backend URL is accessible (try opening it in browser)

### Spotify auth fails
- Verify redirect URI in Spotify dashboard matches backend URL exactly
- Check `SPOTIPY_REDIRECT_URI` environment variable
- Ensure all Spotify credentials are correct

## 📊 Monitoring

- **Logs**: Available in Render dashboard for each service
- **Metrics**: CPU, memory usage visible in dashboard
- **Alerts**: Configure email notifications for deployment failures

## 🎯 Next Steps

1. **Custom Domain**: Add your own domain in Render settings
2. **SSL**: Automatically provided by Render
3. **Scaling**: Upgrade to paid tier for better performance
4. **Database**: Consider PostgreSQL for production use

---

**Need help?** Check Render's [documentation](https://render.com/docs) or open an issue on GitHub.
