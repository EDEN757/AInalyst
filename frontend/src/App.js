import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';
import ChatMessage from './components/ChatMessage';
import CompanySelect from './components/CompanySelect';
import CompanyManagement from './components/CompanyManagement';

// Create custom axios instance with retry logic
const apiClient = axios.create();

// Make apiClient available globally for other components
window.apiClient = apiClient;

// Add a request interceptor for logging
apiClient.interceptors.request.use(
  config => {
    console.log(`API Request: ${config.method.toUpperCase()} ${config.url}`);
    return config;
  },
  error => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Add retry logic for failed requests
apiClient.interceptors.response.use(
  response => response,
  async error => {
    const { config } = error;

    // Only retry GET requests to avoid side effects
    if (!config || !config.method || config.method.toLowerCase() !== 'get' || config._retryCount >= 2) {
      return Promise.reject(error);
    }

    // Set retry count
    config._retryCount = config._retryCount || 0;
    config._retryCount++;

    console.log(`Retrying request ${config.url} (attempt ${config._retryCount}/2)`);

    // Wait before retrying - increase delay for subsequent retries
    const delay = config._retryCount * 1000; // 1s for first retry, 2s for second
    await new Promise(resolve => setTimeout(resolve, delay));

    return apiClient(config);
  }
);

function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [companies, setCompanies] = useState([]);
  const [selectedCompanies, setSelectedCompanies] = useState([]);
  const [filingYear, setFilingYear] = useState('');
  const [apiError, setApiError] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const messagesEndRef = useRef(null);
  
  // Try multiple API URLs if the primary one fails
  // Order of precedence: Environment variable, host.docker.internal, localhost, backend service name
  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
  const API_FALLBACK_URLS = [
    API_URL,
    'http://host.docker.internal:8000',
    'http://localhost:8000',
    'http://backend:8000',  // Docker service name
    'http://sp500_rag_backend:8000'  // Docker container name
  ];
  
  // Check API connectivity
  // Function to try multiple API URLs
  const getWorkingApiUrl = async () => {
    // Try each URL in the fallback list
    for (const url of API_FALLBACK_URLS) {
      try {
        console.log(`Testing API URL: ${url}`);
        // Simple ping test first - fast and lightweight
        const pingResponse = await apiClient.get(`${url}/ping`, {
          timeout: 3000,
          headers: { 'Cache-Control': 'no-cache' }
        });

        if (pingResponse.data) {
          console.log(`✅ Found working API at ${url}`);
          // Return the first URL that responds
          return url;
        }
      } catch (error) {
        console.warn(`❌ API at ${url} failed ping test:`, error.message);
      }
    }
    return null;  // No working URLs found
  };

  useEffect(() => {
    const checkApiStatus = async () => {
      try {
        setApiError(null);
        console.log('Checking API connectivity...');

        // Find a working API URL
        const workingUrl = await getWorkingApiUrl();

        if (!workingUrl) {
          throw new Error("No working API URL found");
        }

        // Store the working URL globally
        window.workingApiUrl = workingUrl;

        // If it's not our primary URL, log a warning
        if (workingUrl !== API_URL) {
          console.warn(`Using fallback URL ${workingUrl} instead of primary URL ${API_URL}`);
        }

        // If we found a URL that works, do a full health check
        const response = await apiClient.get(`${workingUrl}/health`, {
          timeout: 5000,
          headers: { 'Cache-Control': 'no-cache' }
        });

        if (response.data.status === 'ok') {
          setIsConnected(true);
          console.log('✅ API connected successfully');
          console.log('Database status:', response.data.database);

          // Show a warning if using fallback
          if (workingUrl !== API_URL) {
            setApiError(`Note: Using fallback API URL ${workingUrl} instead of ${API_URL}`);
          }
        } else {
          console.error('❌ API health check returned non-ok status:', response.data);
          setApiError(`API Error: ${JSON.stringify(response.data)}`);
          setIsConnected(false);
        }
      } catch (error) {
        console.error('❌ API health check error:', error);
        setIsConnected(false);

        // Construct a helpful error message
        let errorMsg = "Connection Error: Unable to reach the API server. Please check if the backend is running.";
        errorMsg += "\n\nAttempted these URLs:";
        API_FALLBACK_URLS.forEach(url => {
          errorMsg += `\n- ${url}`;
        });
        errorMsg += "\n\nIf you're using Docker, make sure all containers are running with 'docker-compose ps'.";

        setApiError(errorMsg);
      }
    };

    console.log(`API URL configured as: ${API_URL}`);
    checkApiStatus();

    // Check API health every 20 seconds
    const interval = setInterval(checkApiStatus, 20000);
    return () => clearInterval(interval);
  }, [API_URL]);

  // Fetch companies on component mount
  useEffect(() => {
    const fetchCompanies = async () => {
      if (!isConnected) return; // Don't fetch if not connected
      
      try {
        setApiError(null);
        // Use the working URL if one was found, otherwise fall back to the default
        const apiUrl = window.workingApiUrl || API_URL;
        const response = await apiClient.get(`${apiUrl}/api/v1/companies`, { timeout: 10000 });
        
        if (response.data && Array.isArray(response.data)) {
          console.log(`Fetched ${response.data.length} companies successfully`);
          setCompanies(response.data);
          
          if (response.data.length === 0) {
            setApiError('Warning: No companies found in the database. The database might be empty.');
            // Show the management tab on first load if no companies
            setActiveTab('manage');
          }
        } else {
          console.error('Companies API returned unexpected data format:', response.data);
          setApiError('Error: Received invalid data format from the server.');
        }
      } catch (error) {
        console.error('Error fetching companies:', error);
        
        if (error.response) {
          // Server responded with an error
          setApiError(`Companies API Error (${error.response.status}): ${error.response.data.detail || JSON.stringify(error.response.data)}`);
        } else if (error.request) {
          // No response received from the request
          setApiError('Connection Error: Unable to fetch companies. The request timed out.');
        } else {
          // Something else went wrong
          setApiError(`Request Error: ${error.message}`);
        }
      }
    };

    if (isConnected) {
      fetchCompanies();
    }

    // Add welcome message
    setMessages([
      {
        role: 'system',
        content: 'Welcome to the S&P 500 10-K RAG Chatbot! Ask me anything about S&P 500 companies\'10-K filings.'
      }
    ]);
    
    // If there's an API error, add it as a system message
    if (apiError) {
      setMessages(prev => [...prev, {
        role: 'system',
        content: apiError
      }]);
    }
  }, [API_URL, isConnected, apiError]);

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
      
      if (selectedCompanies && selectedCompanies.length > 0) {
        query.company_symbols = selectedCompanies;
      }
      
      if (filingYear && !isNaN(parseInt(filingYear))) {
        query.filing_year = parseInt(filingYear);
      }
      
      console.log('Sending chat query:', query);
      
      // Send to API with timeout
      // Use the working URL if one was found, otherwise fall back to the default
      const apiUrl = window.workingApiUrl || API_URL;
      const response = await apiClient.post(
        `${apiUrl}/api/v1/chat`,
        query,
        { timeout: 30000 } // 30 second timeout for chat requests
      );
      
      // Add assistant response to chat
      const assistantMessage = {
        role: 'assistant',
        content: response.data.answer,
        sources: response.data.sources
      };
      
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error getting chat response:', error);
      
      // Create error message with detailed information
      let errorContent = 'Sorry, there was an error processing your request. ';
      
      if (error.response) {
        // Server responded with an error
        console.error('Error response:', error.response);
        errorContent += `Server Error (${error.response.status}): `;
        
        if (error.response.data && error.response.data.detail) {
          errorContent += error.response.data.detail;
        } else {
          errorContent += 'Unknown server error';
        }
      } else if (error.request) {
        // Request made but no response received (timeout)
        errorContent += 'The request timed out. The server might be overloaded or experiencing issues.';
      } else {
        // Error in setting up the request
        errorContent += `Request Error: ${error.message}`;
      }
      
      // Add error message
      const errorMessage = {
        role: 'system',
        content: errorContent
      };
      
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };
  
  // Handler for company updates from the management component
  const handleCompaniesUpdated = (updatedCompanies) => {
    setCompanies(updatedCompanies);
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>AInalyst: 10-K Analysis Platform</h1>
        {apiError && (
          <div className="api-error">
            <span className="error-icon">⚠️</span> {apiError}
          </div>
        )}
        <div className="connection-status">
          API Status: <span className={isConnected ? "connected" : "disconnected"}>
            {isConnected ? "✅ Connected" : "❌ Disconnected"}
          </span>
          {isConnected && companies.length === 0 && (
            <span className="warning">⚠️ No companies found in database</span>
          )}
        </div>
        
        <div className="app-nav">
          <div 
            className={`nav-item ${activeTab === 'chat' ? 'active' : ''}`}
            onClick={() => setActiveTab('chat')}
          >
            Chat Interface
          </div>
          <div 
            className={`nav-item ${activeTab === 'manage' ? 'active' : ''}`}
            onClick={() => setActiveTab('manage')}
          >
            Company Management
          </div>
        </div>
      </header>
      
      {activeTab === 'chat' && (
        <>
          <div className="filters">
            <CompanySelect 
              companies={companies} 
              selectedCompanies={selectedCompanies}
              onChange={setSelectedCompanies}
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
                disabled={loading || !isConnected || companies.length === 0}
              />
              <button 
                type="submit" 
                disabled={loading || !input.trim() || !isConnected || companies.length === 0}
                title={
                  !isConnected 
                    ? "API is disconnected" 
                    : companies.length === 0 
                      ? "No companies in database. Add companies first." 
                      : ""
                }
              >
                Send
              </button>
            </form>
          </div>
        </>
      )}
      
      {activeTab === 'manage' && (
        <CompanyManagement
          apiUrl={window.workingApiUrl || API_URL}
          onCompaniesUpdated={handleCompaniesUpdated}
        />
      )}
    </div>
  );
}

export default App;
