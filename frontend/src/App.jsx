import { useState } from "react";
import QuickSightEmbed from "./QuickSightEmbed";
import config from "./config";

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [showQuickSight, setShowQuickSight] = useState(false);

  const sendMessage = async () => {
    if (!input) return;

    const userMessage = { sender: "user", text: input };
    setMessages((prev) => [...prev, userMessage]);

    const res = await fetch(`${config.API_BASE_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: "localUser1",
        message: input
      })
    });

    const data = await res.json();

    const botMessage = { sender: "bot", text: data.reply };
    setMessages((prev) => [...prev, botMessage]);

    setInput("");
  };

  return (
    <div style={{ padding: 20, display: 'flex', justifyContent: 'flex-end' }}>
      <div style={{ width: '100%' }}>
        <div style={{ marginBottom: 20 }}>
          <button 
            onClick={() => setShowQuickSight(!showQuickSight)}
            style={{
              padding: '10px 20px',
              backgroundColor: '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '5px',
              cursor: 'pointer'
            }}
          >
            {showQuickSight ? 'Show Chat' : 'Show QuickSight Embed'}
          </button>
        </div>

      {showQuickSight ? (
        <QuickSightEmbed />
      ) : (
        <div>
          <h2>Application Chat</h2>

          <div style={{
            height: "70vh",
            border: "1px solid #ccc",
            padding: 10,
            overflowY: "auto"
          }}>
            {messages.map((msg, index) => (
              <div
                key={index}
                style={{
                  margin: "8px 0",
                  textAlign: msg.sender === "user" ? "right" : "left"
                }}
              >
                <span
                  style={{
                    display: "inline-block",
                    padding: "10px",
                    borderRadius: "10px",
                    background: msg.sender === "user" ? "#007bff" : "#eee",
                    color: msg.sender === "user" ? "white" : "black"
                  }}
                >
                  {msg.text}
                </span>
              </div>
            ))}
          </div>

          <div style={{ marginTop: 10, display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
            <input
              style={{ width: "80%" }}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type your question..."
            />
            <button onClick={sendMessage}>Send</button>
          </div>
        </div>
      )}
      </div>
    </div>
  );
}
