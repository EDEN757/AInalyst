import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';
import ChatMessage from './components/ChatMessage';
import CompanySelect from './components/CompanySelect';

function App() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [companies, setCompanies] = useState([]);
  const [selectedCompany, setSelectedCompany] = useState('');
  const [filingYear, setFilingYear] = useState('');
  const messagesEndRef = useRef(null);
  
  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

  // Fetch companies on component mount
  useEffect(() => {
    const fetchCompanies = async () => {
      try {
        const response = await axios.get(`${API_URL}/api/v1/companies`);
        setCompanies(response.data);
      } catch (error) {
        console.error('Error fetching companies:', error);
      }
    };

    fetchCompanies();

    // Add welcome message
    setMessages([
      {
        role: 'system',
        content: 'Welcome to the S&P 500 10-K RAG Chatbot! Ask me anything about S&P 500 companies\'10-K filings.'
      }
    ]);
  }, [API_URL]);

  // Auto-scroll to bottom of chat
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!input.trim()) return;
    
    // Add user message to chat
    const userMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    
    // Clear input and show loading
    setInput('');
    setLoading(true);
    
    try {
      // Build query with optional filters
      const query = {
        query: input
      };
      
      if (selectedCompany) {
        query.company_symbol = selectedCompany;
      }
      
      if (filingYear && !isNaN(parseInt(filingYear))) {
        query.filing_year = parseInt(filingYear);
      }
      
      // Send to API
      const response = await axios.post(`${API_URL}/api/v1/chat`, query);
      
      // Add assistant response to chat
      const assistantMessage = {
        role: 'assistant',
        content: response.data.answer,
        sources: response.data.sources
      };
      
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error getting response:', error);
      
      // Add error message
      const errorMessage = {
        role: 'system',
        content: 'Sorry, there was an error processing your request. Please try again.'
      };
      
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>S&P 500 10-K RAG Chatbot</h1>
        <div className="filters">
          <CompanySelect 
            companies={companies} 
            selectedCompany={selectedCompany}
            onChange={setSelectedCompany}
          />
          <div className="filing-year">
            <label htmlFor="filingYear">Filing Year:</label>
            <input
              type="number"
              id="filingYear"
              value={filingYear}
              onChange={(e) => setFilingYear(e.target.value)}
              placeholder="e.g., 2023"
              min="2000"
              max="2023"
            />
          </div>
        </div>
      </header>
      
      <div className="chat-container">
        <div className="messages">
          {messages.map((message, index) => (
            <ChatMessage key={index} message={message} />
          ))}
          {loading && <div className="loading">Thinking...</div>}
          <div ref={messagesEndRef} />
        </div>
        
        <form className="input-form" onSubmit={handleSubmit}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about S&P 500 companies' 10-K filings..."
            disabled={loading}
          />
          <button type="submit" disabled={loading || !input.trim()}>
            Send
          </button>
        </form>
      </div>
    </div>
  );
}

export default App;
