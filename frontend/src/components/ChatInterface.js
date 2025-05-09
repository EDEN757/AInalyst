import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { useAppContext } from '../context/AppContext';
import ChatMessage from './ChatMessage';
import CompanySelect from './CompanySelect';
import { sendChatMessage, createChatStream } from '../utils/api';

const ChatInterface = () => {
  // Get context values
  const {
    selectedCompany,
    selectedYear,
    selectedSection,
    selectedModel,
    sessionId,
    setSessionId,
  } = useAppContext();

  // Local state
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamedResponse, setStreamedResponse] = useState('');
  const [streamedSources, setStreamedSources] = useState([]);
  
  // Refs
  const messageListRef = useRef(null);
  const eventSourceRef = useRef(null);
  
  // Load messages from localStorage on mount
  useEffect(() => {
    if (sessionId) {
      const savedMessages = localStorage.getItem(`chatMessages_${sessionId}`);
      if (savedMessages) {
        try {
          setMessages(JSON.parse(savedMessages));
        } catch (error) {
          console.error('Error parsing saved messages:', error);
        }
      }
    }
  }, [sessionId]);
  
  // Save messages to localStorage when they change
  useEffect(() => {
    if (sessionId && messages.length > 0) {
      localStorage.setItem(`chatMessages_${sessionId}`, JSON.stringify(messages));
    }
  }, [sessionId, messages]);
  
  // Scroll to bottom when messages change
  useEffect(() => {
    if (messageListRef.current) {
      messageListRef.current.scrollTop = messageListRef.current.scrollHeight;
    }
  }, [messages, streamedResponse]);
  
  // Cleanup event source on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  // Send a message using regular API call
  const sendMessage = async () => {
    if (!input.trim()) return;

    // Add user message to chat
    const userMessage = { role: 'user', content: input };
    setMessages([...messages, userMessage]);
    setInput('');
    setLoading(true);

    try {
      // Build request body
      const requestBody = {
        message: input,
        session_id: sessionId,
        model: selectedModel
      };

      // Add filters if selected
      if (selectedCompany) requestBody.ticker = selectedCompany;
      if (selectedYear) requestBody.year = parseInt(selectedYear);
      if (selectedSection) requestBody.section_name = selectedSection;

      // Send request to backend
      const data = await sendChatMessage(requestBody);

      // Update session ID if returned
      if (data.session_id) {
        setSessionId(data.session_id);
      }

      // Add assistant message to chat
      const assistantMessage = {
        role: 'assistant',
        content: data.message,
        sources: data.sources
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      // Add error message
      const errorMessage = {
        role: 'assistant',
        content: 'Sorry, there was an error processing your request. Please try again later.'
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };
  
  // Send a message using streaming API
  const sendStreamingMessage = () => {
    if (!input.trim()) return;
    
    // Add user message to chat
    const userMessage = { role: 'user', content: input };
    setMessages([...messages, userMessage]);
    setInput('');
    
    // Reset streaming state
    setIsStreaming(true);
    setStreamedResponse('');
    setStreamedSources([]);
    
    // Build request body
    const requestBody = {
      message: input,
      session_id: sessionId,
      model: selectedModel
    };
    
    // Add filters if selected
    if (selectedCompany) requestBody.ticker = selectedCompany;
    if (selectedYear) requestBody.year = parseInt(selectedYear);
    if (selectedSection) requestBody.section_name = selectedSection;
    
    // Close existing event source if any
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    
    // Create new event source
    const eventSource = createChatStream(requestBody);
    eventSourceRef.current = eventSource;
    
    // Handle events
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        switch (data.type) {
          case 'metadata':
            // Update session ID if returned
            if (data.session_id) {
              setSessionId(data.session_id);
            }
            break;
          
          case 'content':
            // Update streamed response
            setStreamedResponse((prev) => prev + data.content);
            break;
          
          case 'sources':
            // Update sources
            setStreamedSources(data.sources);
            break;
          
          case 'done':
            // Add final message to chat
            setMessages((prev) => [
              ...prev,
              {
                role: 'assistant',
                content: streamedResponse,
                sources: streamedSources
              }
            ]);
            
            // Close event source
            eventSource.close();
            setIsStreaming(false);
            break;
          
          case 'error':
            // Handle error
            console.error('Stream error:', data.error);
            setMessages((prev) => [
              ...prev,
              {
                role: 'assistant',
                content: 'Sorry, there was an error processing your request. Please try again later.'
              }
            ]);
            
            // Close event source
            eventSource.close();
            setIsStreaming(false);
            break;
          
          default:
            console.log('Unknown message type:', data.type);
            break;
        }
      } catch (error) {
        console.error('Error processing SSE message:', error);
      }
    };
    
    eventSource.onerror = (error) => {
      console.error('SSE error:', error);
      
      // Add error message
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry, there was an error with the streaming connection. Please try again later.'
        }
      ]);
      
      // Close event source
      eventSource.close();
      setIsStreaming(false);
    };
  };

  // Clear chat history
  const clearChat = () => {
    setMessages([]);
    if (sessionId) {
      localStorage.removeItem(`chatMessages_${sessionId}`);
    }
  };

  return (
    <div className="chat-container">
      <div className="controls-container">
        <div className="company-selector">
          <CompanySelect />
          <select
            className="select-field"
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
          >
            <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
            <option value="gpt-4">GPT-4</option>
          </select>
        </div>
        
        <div className="chat-actions">
          <button 
            className="action-button clear-button" 
            onClick={clearChat}
            disabled={loading || isStreaming || messages.length === 0}
          >
            Clear Chat
          </button>
          <label className="streaming-toggle">
            <input
              type="checkbox"
              checked={isStreaming}
              onChange={() => setIsStreaming(!isStreaming)}
              disabled={loading}
            />
            Streaming Mode
          </label>
        </div>
      </div>

      <div className="message-list" ref={messageListRef}>
        {messages.length === 0 ? (
          <div className="welcome-message">
            <h2>Welcome to AInalyst!</h2>
            <p>Ask questions about financial reports and SEC filings.</p>
            <p>Examples:</p>
            <ul>
              <li>What were Apple's main risk factors in 2022?</li>
              <li>Summarize Microsoft's business strategy</li>
              <li>How did Amazon's revenue change from 2020 to 2022?</li>
            </ul>
          </div>
        ) : (
          <>
            {messages.map((message, index) => (
              <ChatMessage key={index} message={message} />
            ))}
            
            {/* Show streaming response if available */}
            {isStreaming && streamedResponse && (
              <div className="chat-message assistant streaming">
                <div className="message-header">
                  <span className="message-role">AInalyst</span>
                  <span className="streaming-indicator">Streaming...</span>
                </div>
                <div className="message-content">
                  <ReactMarkdown>{streamedResponse}</ReactMarkdown>
                </div>
              </div>
            )}
          </>
        )}
        {loading && <div className="loading-message">Loading...</div>}
      </div>

      <div className="message-input">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && (isStreaming ? sendStreamingMessage() : sendMessage())}
          placeholder="Ask a question about financial filings..."
          disabled={loading || isStreaming}
        />
        <button 
          onClick={isStreaming ? sendStreamingMessage : sendMessage} 
          disabled={loading || isStreaming}
        >
          Send
        </button>
      </div>

      <style jsx>{`
        .controls-container {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 1rem;
          border-bottom: 1px solid var(--border-color);
        }
        
        .company-selector {
          display: flex;
          gap: 1rem;
          align-items: center;
        }
        
        .chat-actions {
          display: flex;
          gap: 1rem;
          align-items: center;
        }
        
        .action-button {
          padding: 0.5rem 1rem;
          border: 1px solid var(--border-color);
          background-color: white;
          border-radius: var(--border-radius);
          cursor: pointer;
        }
        
        .clear-button {
          color: var(--error-color);
          border-color: var(--error-color);
        }
        
        .streaming-toggle {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          font-size: 0.9rem;
          cursor: pointer;
        }
        
        .streaming-indicator {
          font-size: 0.8rem;
          color: var(--primary-color);
          animation: pulse 1.5s infinite;
          margin-left: 0.5rem;
        }
        
        @keyframes pulse {
          0% {
            opacity: 0.5;
          }
          50% {
            opacity: 1;
          }
          100% {
            opacity: 0.5;
          }
        }
        
        .chat-message.streaming {
          border: 1px solid var(--primary-color);
        }
      `}</style>
    </div>
  );
};

export default ChatInterface;