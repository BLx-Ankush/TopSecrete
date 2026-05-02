# 🔑 API Configuration Guide for Alice

To get Alice fully working, you need to obtain and configure several API keys. Follow these steps:

## 🎙️ LiveKit (Required for voice chat)
1. Go to [LiveKit Cloud](https://cloud.livekit.io)
2. Create a free account and project
3. Get your credentials and update `.env.local`:
   ```
   LIVEKIT_API_KEY=your_actual_api_key
   LIVEKIT_API_SECRET=your_actual_api_secret
   LIVEKIT_URL=wss://your-project.livekit.cloud
   ```

## 🧠 Mem0 (Optional - for memory features)
1. Go to [Mem0 Dashboard](https://app.mem0.ai/dashboard/api-keys)
2. Create an account and get your API key
3. Update both `.env.local` and `Alice_code/.env`:
   ```
   MEM0_API_KEY=your_mem0_api_key
   ```

## 🌤️ Weather API (Open-Meteo - default)
Open-Meteo weather API is enabled by default and requires no API keys.
Nothing to configure for weather data.

## 🤖 Google Gemini (Required for AI responses)
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create an API key
3. Update `Alice_code/.env`:
   ```
   GOOGLE_API_KEY=your_google_api_key
   ```

## 🔍 Web Search (DuckDuckGo - default)
DuckDuckGo search is enabled by default and requires no API keys.
Nothing to configure for web search.

## 🚀 After Configuration
1. Restart the development server: `pnpm dev`
2. Alice will be fully functional with all features!

**Note**: Alice can start without these keys, but some features will be limited until you configure them.