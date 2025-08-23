import React, { useState, useRef, useEffect } from "react";
import {
  Upload,
  Send,
  FileText,
  BarChart3,
  Code,
  Image,
  MessageCircle,
  Trash2,
  Download,
  Loader,
} from "lucide-react";
import "./App.css";

const CSVAnalyzer = () => {
  const [chatHistory, setChatHistory] = useState([]);
  const [currentFile, setCurrentFile] = useState(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef(null);
  const chatEndRef = useRef(null);
  const [sessionId, setSessionId] = useState(null);

  // Store image URLs for each assistant message by message id
  const [imageURLs, setImageURLs] = useState({});

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory]);

  // Upload file to backend and get sessionId
  const handleFileUpload = async (file) => {
    if (file && file.type === "text/csv") {
      setCurrentFile(file);
      // Upload to backend and get sessionId
      const formData = new FormData();
      formData.append("file", file);
      try {
        const response = await fetch(
          "https://finanalystai.onrender.com/upload/",
          {
            method: "POST",
            body: formData,
          }
        );
        const result = await response.json();
        if (result.session_id) {
          setSessionId(result.session_id);
        } else {
          alert("Failed to upload file.");
          setCurrentFile(null);
        }
      } catch (err) {
        alert("Failed to upload file.");
        setCurrentFile(null);
      }
    } else {
      alert("Please upload a valid CSV file");
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    handleFileUpload(file);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setDragOver(false);
  };

  // Analyze using sessionId and query
  const analyzeCSV = async () => {
    if (!currentFile || !query.trim() || !sessionId) return;

    setLoading(true);

    const formData = new FormData();
    formData.append("session_id", sessionId);
    formData.append("user_query", query);

    const userMessage = {
      id: Date.now(),
      type: "user",
      content: query,
      timestamp: new Date().toLocaleTimeString(),
      fileName: currentFile.name,
    };

    setChatHistory((prev) => [...prev, userMessage]);
    setQuery("");

    try {
      const response = await fetch(
        "https://finanalystai.onrender.com/analyze/",
        {
          method: "POST",
          body: formData,
        }
      );

      const result = await response.json();

      const assistantMessage = {
        id: Date.now() + 1,
        type: "assistant",
        content: result,
        timestamp: new Date().toLocaleTimeString(),
      };

      setChatHistory((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        type: "error",
        content: `Error: ${error.message}`,
        timestamp: new Date().toLocaleTimeString(),
      };
      setChatHistory((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  // Fetch and display image for the current session
  const fetchAndShowImage = async (msgId, timestamp) => {
    if (!sessionId || !timestamp) return;
    try {
      const response = await fetch(
        `https://finanalystai.onrender.com/get_image/?session_id=${sessionId}&timestamp=${timestamp}`
      );
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        setImageURLs((prev) => ({ ...prev, [msgId]: url }));
      }
    } catch (error) {
      console.error("Error fetching image:", error);
    }
  };

  // Download image for the current session
  const downloadImage = async (timestamp) => {
    if (!sessionId || !timestamp) return;
    try {
      const response = await fetch(
        `https://finanalystai.onrender.com/get_image/?session_id=${sessionId}&timestamp=${timestamp}`
      );
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `analysis-output-${timestamp}.png`;
        a.click();
        window.URL.revokeObjectURL(url);
      }
    } catch (error) {
      console.error("Error downloading image:", error);
    }
  };

  // Clear chat and session on backend
  const clearChat = async () => {
    if (sessionId) {
      const formData = new FormData();
      formData.append("session_id", sessionId);
      try {
        await fetch("https://finanalystai.onrender.com/clear_session/", {
          method: "POST",
          body: formData,
        });
      } catch (err) {
        // Ignore error, just clear frontend state
      }
    }
    setChatHistory([]);
    setCurrentFile(null);
    setSessionId(null);
    setImageURLs({});
  };

  const CodeBlock = ({ code }) => (
    <div className="code-block">
      <div className="code-header">
        <div className="code-title">
          <Code size={16} color="#60a5fa" />
          <span>Generated Code</span>
        </div>
        <button
          onClick={() => navigator.clipboard.writeText(code)}
          className="copy-btn"
        >
          Copy
        </button>
      </div>
      <pre className="code-content">
        <code>{code}</code>
      </pre>
    </div>
  );

  // OutputDisplay now only renders if stdout is present
  const OutputDisplay = ({ stdout, stderr }) => (
    <div className="output-display">
      {stdout && (
        <div className="output-success">
          <div className="output-header success">
            <BarChart3 size={16} color="#16a34a" />
            <span>Analysis Output</span>
          </div>
          <pre className="output-content success">{stdout}</pre>
        </div>
      )}
      {stderr && (
        <div className="output-error">
          <div className="output-header error">
            <span>Error Output</span>
          </div>
          <pre className="output-content error">{stderr}</pre>
        </div>
      )}
    </div>
  );

  // Add a useEffect to fetch image when a new assistant message with image_generated or both_generated is added
  useEffect(() => {
    // Find the latest assistant message with image_generated or both_generated and no imageURL yet
    const lastAssistant = [...chatHistory]
      .reverse()
      .find(
        (msg) =>
          msg.type === "assistant" &&
          msg.content &&
          (msg.content.flags?.image_generated ||
            msg.content.flags?.both_generated) &&
          !imageURLs[msg.id] &&
          msg.content.image_timestamp
      );
    if (lastAssistant) {
      fetchAndShowImage(
        lastAssistant.id,
        lastAssistant.content.image_timestamp
      );
    }
    // eslint-disable-next-line
  }, [chatHistory]);

  // Helper to determine if we should show the image for a message
  const shouldShowImage = (flags) => {
    return flags?.image_generated || flags?.both_generated;
  };

  // Helper to determine if we should show the analysis output for a message
  const shouldShowStdout = (flags) => {
    return flags?.stdout_generated || flags?.both_generated;
  };

  return (
    <div className="app-container">
      {/* Header */}
      <div className="header">
        <div className="header-content">
          <div className="header-brand">
            <div className="header-icon">
              <BarChart3 size={24} />
            </div>
            <div>
              <h1 className="header-title">CSV Analyzer Pro</h1>
              <p className="header-subtitle">
                AI-Powered Data Analysis & Visualization
              </p>
            </div>
          </div>
          <button onClick={clearChat} className="clear-btn">
            <Trash2 size={16} />
            Clear Chat
          </button>
        </div>
      </div>

      <div className="main-content">
        <div className="grid">
          {/* File Upload Section */}
          <div>
            <div className="upload-section">
              <h2 className="section-title">
                <Upload size={20} color="#2563eb" />
                Upload Dataset
              </h2>

              <div
                className={`upload-zone ${dragOver ? "drag-over" : ""} ${
                  currentFile ? "has-file" : ""
                }`}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={(e) => handleFileUpload(e.target.files[0])}
                  accept=".csv"
                  className="hidden"
                />

                {currentFile ? (
                  <div>
                    <div className="upload-icon-container success">
                      <FileText size={32} color="#16a34a" />
                    </div>
                    <div>
                      <p className="upload-text success">{currentFile.name}</p>
                      <p className="upload-subtext success">
                        {(currentFile.size / 1024).toFixed(2)} KB
                      </p>
                    </div>
                  </div>
                ) : (
                  <div>
                    <div className="upload-icon-container default">
                      <Upload size={32} color="#6b7280" />
                    </div>
                    <div>
                      <p className="upload-text default">
                        Drop your CSV file here
                      </p>
                      <p className="upload-subtext default">
                        or click to browse
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {/* Query Input */}
              <div className="query-section">
                <label className="query-label">Analysis Query</label>
                <div>
                  <textarea
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="What would you like to analyze? E.g., 'Create a bar chart showing sales by region' or 'Show correlation between price and quantity'"
                    className="query-textarea"
                    disabled={loading}
                  />
                </div>
                <button
                  onClick={analyzeCSV}
                  disabled={!currentFile || !query.trim() || loading}
                  className="analyze-btn"
                >
                  {loading ? (
                    <Loader size={20} className="animate-spin" />
                  ) : (
                    <Send size={20} />
                  )}
                  {loading ? "Analyzing..." : "Analyze Data"}
                </button>
              </div>
            </div>
          </div>

          {/* Chat History */}
          <div>
            <div className="chat-section">
              <div className="chat-header">
                <h2 className="section-title">
                  <MessageCircle size={20} color="#2563eb" />
                  Analysis History
                </h2>
              </div>

              <div className="chat-content">
                {chatHistory.length === 0 ? (
                  <div className="chat-empty">
                    <div className="chat-empty-icon">
                      <MessageCircle size={40} color="#9ca3af" />
                    </div>
                    <p className="chat-empty-text">No analysis history yet</p>
                    <p className="chat-empty-subtext">
                      Upload a CSV file and ask a question to get started
                    </p>
                  </div>
                ) : (
                  <div className="chat-messages">
                    {chatHistory.map((message) => {
                      // For assistant messages, get flags
                      const flags = message.content?.flags || {};
                      return (
                        <div
                          key={message.id}
                          className={`message ${message.type}`}
                        >
                          <div className={`message-bubble ${message.type}`}>
                            {message.type === "user" ? (
                              <div>
                                <div className="message-header user">
                                  <span>You</span>
                                  <span>{message.timestamp}</span>
                                  {message.fileName && (
                                    <span className="file-tag">
                                      {message.fileName}
                                    </span>
                                  )}
                                </div>
                                <p className="message-content">
                                  {message.content}
                                </p>
                              </div>
                            ) : message.type === "error" ? (
                              <div>
                                <div className="message-header error">
                                  <span>Error</span>
                                  <span>{message.timestamp}</span>
                                </div>
                                <p className="message-content">
                                  {message.content}
                                </p>
                              </div>
                            ) : (
                              <div>
                                <div className="message-header assistant">
                                  <span>AI Assistant</span>
                                  <span>{message.timestamp}</span>
                                </div>

                                {/* Do NOT show Dataset Information */}

                                {message.content.generated_code && (
                                  <CodeBlock
                                    code={message.content.generated_code}
                                  />
                                )}

                                {/* Show analysis output only if stdout_generated or both_generated */}
                                {shouldShowStdout(flags) && (
                                  <OutputDisplay
                                    stdout={message.content.stdout}
                                    stderr={message.content.stderr}
                                  />
                                )}

                                {/* Show image inline only if image_generated or both_generated */}
                                {shouldShowImage(flags) && (
                                  <div className="image-display">
                                    <div className="image-header">
                                      <div className="image-title">
                                        <Image size={16} color="#7c3aed" />
                                        <span>Visualization</span>
                                      </div>
                                      <button
                                        onClick={() =>
                                          downloadImage(
                                            message.content.image_timestamp
                                          )
                                        }
                                        className="download-btn"
                                      >
                                        <Download size={16} />
                                        Download
                                      </button>
                                    </div>
                                    {imageURLs[message.id] ? (
                                      <div className="image-preview">
                                        <img
                                          src={imageURLs[message.id]}
                                          alt="Analysis Visualization"
                                          style={{
                                            maxWidth: "100%",
                                            borderRadius: "0.5rem",
                                            marginTop: "0.5rem",
                                          }}
                                        />
                                      </div>
                                    ) : (
                                      <p className="image-description">
                                        Loading visualization...
                                      </p>
                                    )}
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                    <div ref={chatEndRef} />
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CSVAnalyzer;
