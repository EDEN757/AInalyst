import React, { createContext, useState, useContext, useEffect } from 'react';
import { getCompanies } from '../utils/api';

// Create context
const AppContext = createContext();

// Custom hook for using the app context
export function useAppContext() {
  return useContext(AppContext);
}

// Provider component
export function AppProvider({ children }) {
  // State
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedCompany, setSelectedCompany] = useState('');
  const [selectedYear, setSelectedYear] = useState('');
  const [selectedSection, setSelectedSection] = useState('');
  const [selectedModel, setSelectedModel] = useState('gpt-3.5-turbo');
  const [sessionId, setSessionId] = useState('');
  
  // Load companies on mount
  useEffect(() => {
    const loadCompanies = async () => {
      try {
        setLoading(true);
        const data = await getCompanies();
        setCompanies(data);
        setError(null);
      } catch (err) {
        console.error('Error loading companies:', err);
        setError('Failed to load companies data');
      } finally {
        setLoading(false);
      }
    };
    
    loadCompanies();
  }, []);
  
  // Load session ID from localStorage on mount
  useEffect(() => {
    const savedSessionId = localStorage.getItem('chatSessionId');
    if (savedSessionId) {
      setSessionId(savedSessionId);
    }
  }, []);
  
  // Save session ID to localStorage whenever it changes
  useEffect(() => {
    if (sessionId) {
      localStorage.setItem('chatSessionId', sessionId);
    }
  }, [sessionId]);
  
  // Clear filters
  const clearFilters = () => {
    setSelectedCompany('');
    setSelectedYear('');
    setSelectedSection('');
  };
  
  // Reset session
  const resetSession = () => {
    setSessionId('');
    localStorage.removeItem('chatSessionId');
  };
  
  // Context value
  const value = {
    // Data
    companies,
    
    // UI state
    loading,
    error,
    
    // Filters
    selectedCompany,
    setSelectedCompany,
    selectedYear,
    setSelectedYear,
    selectedSection,
    setSelectedSection,
    selectedModel,
    setSelectedModel,
    
    // Session
    sessionId,
    setSessionId,
    
    // Actions
    clearFilters,
    resetSession
  };
  
  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  );
}

export default AppContext;