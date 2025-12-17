# Streamlit App

This is a Streamlit version of the React frontend that replicates the chat interface and QuickSight embed functionality.

## Features

- 💬 Chat interface with message history
- 📊 QuickSight embed view
- 🔄 Toggle between chat and QuickSight views
- 💾 Session state management
- 🎨 Custom styling similar to React app

## Setup

1. Install dependencies:
```bash
cd streamlit_app
pip install -r requirements.txt
```

2. Configure environment:
   - Copy `.env` and update `API_BASE_URL` if needed

3. Run the app:
```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

## Usage

- **Chat Mode**: Enter messages and chat with the bot
- **QuickSight Mode**: Click "Toggle View" to see the embedded QuickSight dashboard
- **Clear History**: Use the sidebar button to clear chat messages

## Configuration

Edit `.env` file to change:
- `API_BASE_URL`: Your backend API endpoint (default: http://localhost:8004)

## Docker Support

You can also run this in Docker (see docker-compose.yml in root directory).
