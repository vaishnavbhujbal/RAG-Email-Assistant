
import React, { useState, useEffect, useRef } from "react";
import { GoogleOAuthProvider, GoogleLogin } from "@react-oauth/google";
import "./App.css";

const sidebarItems = [
  { icon: "📥", label: "Ask your question" },
  { icon: "💬", label: "Chat History" },
];

const BACKEND = "http://localhost:8000";
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

function App() {
  const [user, setUser] = useState(null);
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeSidebar, setActiveSidebar] = useState("Ask your question");
  const [showInboxPrompt, setShowInboxPrompt] = useState(true);
  const [inboxQA, setInboxQA] = useState(null);
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef(null);

  
  const [listening, setListening] = useState(false);
  const recognitionRef = useRef(null);

  useEffect(() => {
    if (SpeechRecognition) {
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = false;
      recognitionRef.current.lang = "en-US";

      recognitionRef.current.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        setQuestion((q) => (q ? q.trim() + " " + transcript : transcript));
        setListening(false);
      };

      recognitionRef.current.onerror = () => setListening(false);
      recognitionRef.current.onend = () => setListening(false);
    }
  }, []);

  useEffect(() => {
    if (user) {
      fetch(`${BACKEND}/api/history`)
        .then((res) => res.json())
        .then((data) => setHistory(data));
    }
  }, [user]);

  
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSidebarClick = (label) => {
    setActiveSidebar(label);
    setQuestion("");
    setShowInboxPrompt(true);
    setInboxQA(null);
  };

  const askQuestion = async () => {
    if (!user) return alert("Please login first.");
    if (!question.trim()) return;
    setLoading(true);
    const res = await fetch(`${BACKEND}/api/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const data = await res.json();
    setHistory((prev) => [...prev, data]);
    setInboxQA(data);
    setQuestion("");
    setShowInboxPrompt(true);
    setLoading(false);
  };

  const handleInputChange = (e) => {
    setQuestion(e.target.value);
    setShowInboxPrompt(e.target.value.trim() === "");
  };

  const handleGoogleLogin = async (credentialResponse) => {
    const token = credentialResponse.credential;
    const res = await fetch(`${BACKEND}/api/auth/google`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    });
    const data = await res.json();
    if (data.status === "success") {
      setUser(data.user);
      setActiveSidebar("Ask your question");
    } else {
      alert("Google login failed");
    }
  };

  const handleLogout = () => {
    setUser(null);
    setShowDropdown(false);
  };

  
  const toggleListening = () => {
    if (!SpeechRecognition) return;
    if (!listening) {
      setListening(true);
      recognitionRef.current.start();
    } else {
      setListening(false);
      recognitionRef.current.abort();
    }
  };

  
  if (!user) {
    return (
      <GoogleOAuthProvider clientId={process.env.REACT_APP_GOOGLE_CLIENT_ID}>
        <div className="rag-root">
          <div className="rag-appbar">
            <div className="rag-appbar-title">RAG Email Assistant</div>
          </div>
          <div style={{
            display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
            height: "80vh"
          }}>
            <h2>Sign in to continue</h2>
            <GoogleLogin onSuccess={handleGoogleLogin} onError={() => alert("Login Failed")} />
          </div>
        </div>
      </GoogleOAuthProvider>
    );
  }

  return (
    <GoogleOAuthProvider clientId={process.env.REACT_APP_GOOGLE_CLIENT_ID}>
      <div className="rag-root">
        
        <div className="rag-appbar">
          <div className="rag-appbar-title">RAG Email Assistant</div>
          <div
            className="rag-appbar-avatar"
            title={user.name}
            onClick={() => setShowDropdown((prev) => !prev)}
            style={{ cursor: "pointer", position: "absolute", right: 28, display: "flex", alignItems: "center" }}
            ref={dropdownRef}
          >
            <img
              src={user.picture || "https://e7.pngegg.com/pngimages/419/473/png-clipart-computer-icons-user-profile-login-user-heroes-sphere-thumbnail.png"}
              alt="avatar"
            />
            <span className="rag-appbar-username">{user.name}</span>
            {showDropdown && (
              <div className="rag-user-dropdown">
                <button onClick={handleLogout}>Logout</button>
              </div>
            )}
          </div>
        </div>
        
        <div className="rag-main">
          
          <aside className="rag-sidebar">
            <nav>
              {sidebarItems.map((item) => (
                <div
                  key={item.label}
                  className={
                    "rag-sidebar-item" +
                    (activeSidebar === item.label ? " rag-sidebar-item-active" : "")
                  }
                  onClick={() => handleSidebarClick(item.label)}
                >
                  <span className="rag-sidebar-icon">{item.icon}</span>
                  {item.label}
                </div>
              ))}
            </nav>
          </aside>
          
          <section className="rag-chat-panel">
            
            {activeSidebar === "Ask your question" && (
              <div>
                {showInboxPrompt && (
                  <div className="rag-inbox-prompt">
                    You can ask questions to the inbox in the text box provided below.
                  </div>
                )}
                
                <div className="rag-input-row" style={{ justifyContent: "center", marginTop: showInboxPrompt ? 0 : 90 }}>
                  <input
                    value={question}
                    onChange={handleInputChange}
                    onKeyDown={e => e.key === "Enter" && askQuestion()}
                    placeholder="Type your question to inbox"
                    className="rag-input"
                    style={{ maxWidth: 400 }}
                    autoFocus
                  />
                  {SpeechRecognition && (
                    <button
                      className={`rag-mic-btn${listening ? " rag-mic-btn-listening" : ""}`}
                      onClick={toggleListening}
                      type="button"
                      title={listening ? "Listening… Click to stop." : "Speak your question"}
                      aria-pressed={listening}
                    >
                      <span className="rag-mic-icon">
                        <span role="img" aria-label="mic">🎤</span>
                        {listening && <span className="rag-mic-pulse"></span>}
                      </span>
                    </button>
                  )}
                  <button
                    className="rag-ask-btn"
                    onClick={askQuestion}
                    disabled={loading}
                  >
                    {loading ? "Asking..." : "Ask"}
                  </button>
                </div>
                
                <div className="rag-chat-list" style={{ marginTop: 20 }}>
                  {!inboxQA && (
                    <div className="rag-chat-empty">No questions yet. Your Q&A will appear here.</div>
                  )}
                  {inboxQA && (
                    <>
                      <div className="rag-chat-bubble-row rag-chat-bubble-row-user">
                        <div className="rag-chat-bubble rag-chat-bubble-user">
                          <div className="rag-chat-bubble-label">You</div>
                          <div>{inboxQA.question}</div>
                        </div>
                      </div>
                      <div className="rag-chat-bubble-row rag-chat-bubble-row-ai">
                        <div className="rag-chat-bubble rag-chat-bubble-ai">
                          <div className="rag-chat-bubble-label">RAG</div>
                          <div>{inboxQA.answer}</div>
                        </div>
                      </div>
                      <div className="rag-chat-date">
                        {inboxQA.timestamp && new Date(inboxQA.timestamp).toLocaleString()}
                      </div>
                    </>
                  )}
                </div>
              </div>
            )}
            
            {activeSidebar === "Chat History" && (
              <div className="rag-chat-list">
                {history.length === 0 && (
                  <div className="rag-chat-empty">No chat history yet.</div>
                )}
                {history.slice().reverse().map((item, idx) => (
                  <React.Fragment key={idx}>
                    <div className="rag-chat-bubble-row rag-chat-bubble-row-user">
                      <div className="rag-chat-bubble rag-chat-bubble-user">
                        <div className="rag-chat-bubble-label">You</div>
                        <div>{item.question}</div>
                      </div>
                    </div>
                    <div className="rag-chat-bubble-row rag-chat-bubble-row-ai">
                      <div className="rag-chat-bubble rag-chat-bubble-ai">
                        <div className="rag-chat-bubble-label">RAG</div>
                        <div>{item.answer}</div>
                      </div>
                    </div>
                    <div className="rag-chat-date">
                      {item.timestamp && new Date(item.timestamp).toLocaleString()}
                    </div>
                  </React.Fragment>
                ))}
              </div>
            )}
          </section>
        </div>
      </div>
    </GoogleOAuthProvider>
  );
}

export default App;


