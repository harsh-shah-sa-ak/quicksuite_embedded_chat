import streamlit as st
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8004")

# Page configuration
st.set_page_config(
    page_title="Chat Demo",
    page_icon="💬",
    layout="wide"
)

# Custom CSS for better styling
st.markdown(f"""
    <style>
    .stApp {{
        max-width: 1200px;
        margin: 0 auto;
    }}
    .chat-message {{
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }}
    .user-message {{
        background-color: #007bff;
        color: white;
        align-items: flex-end;
    }}
    .bot-message {{
        background-color: #f0f0f0;
        color: black;
        align-items: flex-start;
    }}
    </style>
    <script>
        console.log('Backend API URL:', '{API_BASE_URL}');
        console.log('Streamlit app initialized');
    </script>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "show_quicksight" not in st.session_state:
    st.session_state.show_quicksight = False
if "api_logs" not in st.session_state:
    st.session_state.api_logs = []

def log_api_call(method, url, status_code, response_time=None, response_data=None):
    """Log API calls for debugging"""
    import datetime
    log_entry = {
        "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
        "method": method,
        "url": url,
        "status": status_code,
        "response_time": response_time,
        "response": response_data
    }
    st.session_state.api_logs.append(log_entry)
    # Keep only last 10 logs
    if len(st.session_state.api_logs) > 10:
        st.session_state.api_logs.pop(0)

# Title and toggle button
col1, col2 = st.columns([3, 1])
with col1:
    st.title("💬 Application Chat")
with col2:
    if st.button("🔄 Toggle View", key="toggle_view_btn", use_container_width=True):
        st.session_state.show_quicksight = not st.session_state.show_quicksight
        st.rerun()

# Show current view
if st.session_state.show_quicksight:
    st.subheader("📊 QuickSight Embed")
    
    # Fetch embed URL
    try:
        with st.spinner("Loading QuickSight Chat..."):
            import time
            start_time = time.time()
            url = f"{API_BASE_URL}/get-embed-url/"
            response = requests.get(url)
            response_time = round((time.time() - start_time) * 1000, 2)
            
            if response.status_code == 200:
                data = response.json()
                log_api_call("GET", url, response.status_code, f"{response_time}ms", data)
            else:
                log_api_call("GET", url, response.status_code, f"{response_time}ms", {"error": response.text})
            
            if response.status_code == 200:
                embed_url = data.get("embedUrl")
                
                if embed_url:
                    # Display iframe with QuickSight embed
                    st.components.v1.iframe(embed_url, height=700, scrolling=True)
                else:
                    st.error("No embed URL received from backend")
            else:
                st.error(f"Failed to fetch embed URL: {response.status_code}")
                
    except Exception as e:
        st.error(f"Error fetching embed URL: {str(e)}")
        st.info("Make sure your backend is running at " + API_BASE_URL)

else:
    st.subheader("💬 Chat Interface")
    
    # Display chat messages
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages:
            if message["sender"] == "user":
                st.markdown(f"""
                    <div class="chat-message user-message">
                        <strong>You:</strong><br>{message["text"]}
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                    <div class="chat-message bot-message">
                        <strong>Bot:</strong><br>{message["text"]}
                    </div>
                """, unsafe_allow_html=True)
    
    # Chat input
    with st.form(key="chat_form", clear_on_submit=True):
        col1, col2 = st.columns([5, 1])
        with col1:
            user_input = st.text_input(
                "Message",
                placeholder="Type your question...",
                label_visibility="collapsed"
            )
        with col2:
            submit_button = st.form_submit_button("Send", use_container_width=True)
    
    # Handle message submission
    if submit_button and user_input:
        # Add user message
        st.session_state.messages.append({
            "sender": "user",
            "text": user_input
        })
        
        # Send to backend
        try:
            with st.spinner("Thinking..."):
                import time
                start_time = time.time()
                url = f"{API_BASE_URL}/chat"
                response = requests.post(
                    url,
                    json={
                        "user_id": "localUser1",
                        "message": user_input
                    }
                )
                response_time = round((time.time() - start_time) * 1000, 2)
                
                if response.status_code == 200:
                    data = response.json()
                    log_api_call("POST", url, response.status_code, f"{response_time}ms", data)
                else:
                    log_api_call("POST", url, response.status_code, f"{response_time}ms", {"error": response.text})
                
                if response.status_code == 200:
                    bot_reply = data.get("reply", "No response from bot")
                    
                    # Add bot message
                    st.session_state.messages.append({
                        "sender": "bot",
                        "text": bot_reply
                    })
                else:
                    st.session_state.messages.append({
                        "sender": "bot",
                        "text": f"Error: Failed to get response (Status: {response.status_code})"
                    })
                    
        except Exception as e:
            st.session_state.messages.append({
                "sender": "bot",
                "text": f"Error: {str(e)}"
            })
            st.error("Make sure your backend is running at " + API_BASE_URL)
        
        # Rerun to update chat display
        st.rerun()

# Sidebar with info
with st.sidebar:
    st.header("ℹ️ Information")
    st.write(f"**Backend URL:** {API_BASE_URL}")
    st.write(f"**Messages:** {len(st.session_state.messages)}")
    
    if st.button("Clear Chat History", key="clear_chat_btn", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    
    st.markdown("---")
    
    # API Logs section
    st.subheader("📡 API Logs")
    if st.session_state.api_logs:
        for idx, log in enumerate(reversed(st.session_state.api_logs[-5:])):  # Show last 5
            status_color = "🟢" if log["status"] == 200 else "🔴"
            st.text(f"{status_color} {log['timestamp']} {log['method']}")
            st.caption(f"{log['url']}")
            st.caption(f"Status: {log['status']} | Time: {log['response_time']}")
            
            # Show response data in expander
            if log.get("response"):
                with st.expander("View Response"):
                    st.json(log["response"])
            
            st.divider()
    else:
        st.caption("No API calls yet")
    
    if st.button("Clear Logs", key="clear_logs_btn", use_container_width=True):
        st.session_state.api_logs = []
        st.rerun()
    
    st.markdown("---")
    st.caption("Chat Demo Application")
