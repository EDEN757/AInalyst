// API Utilities for the AInalyst frontend
const API_BASE_URL = process.env.REACT_APP_API_URL || '';
const API_PREFIX = '/api/v1';

// Default fetch options
const defaultOptions = {
  headers: {
    'Content-Type': 'application/json',
  },
};

/**
 * Perform API request with error handling
 * @param {string} endpoint - API endpoint path
 * @param {Object} options - Fetch options
 * @returns {Promise<any>} - Response data
 */
const apiRequest = async (endpoint, options = {}) => {
  try {
    const url = `${API_BASE_URL}${API_PREFIX}${endpoint}`;
    const response = await fetch(url, {
      ...defaultOptions,
      ...options,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API Error (${response.status}): ${errorText}`);
    }

    if (response.headers.get('content-type')?.includes('application/json')) {
      return await response.json();
    }

    return await response.text();
  } catch (error) {
    console.error('API Request Error:', error);
    throw error;
  }
};

/**
 * Get companies list
 * @returns {Promise<Array>} List of companies
 */
export const getCompanies = async () => {
  return await apiRequest('/data/companies');
};

/**
 * Get company details
 * @param {string} ticker Company ticker
 * @returns {Promise<Object>} Company details
 */
export const getCompanyDetails = async (ticker) => {
  return await apiRequest(`/data/companies/${ticker}`);
};

/**
 * Get companies from CSV
 * @returns {Promise<Array>} List of companies from CSV
 */
export const getCompaniesFromCsv = async () => {
  return await apiRequest('/data/companies-csv');
};

/**
 * Get companies status (ingestion status)
 * @returns {Promise<Array>} List of companies with ingestion status
 */
export const getCompaniesStatus = async () => {
  return await apiRequest('/data/companies-status');
};

/**
 * Send a chat message
 * @param {Object} chatRequest Chat request object
 * @returns {Promise<Object>} Chat response
 */
export const sendChatMessage = async (chatRequest) => {
  return await apiRequest('/chat/chat', {
    method: 'POST',
    body: JSON.stringify(chatRequest),
  });
};

/**
 * Create a streaming chat message connection
 * @param {Object} chatRequest Chat request object
 * @returns {EventSource} Server-sent events connection
 */
export const createChatStream = (chatRequest) => {
  // Encode the request as URL parameters for EventSource
  const params = new URLSearchParams({
    message: chatRequest.message,
  });
  
  if (chatRequest.session_id) params.append('session_id', chatRequest.session_id);
  if (chatRequest.ticker) params.append('ticker', chatRequest.ticker);
  if (chatRequest.year) params.append('year', chatRequest.year);
  if (chatRequest.document_type) params.append('document_type', chatRequest.document_type);
  if (chatRequest.model) params.append('model', chatRequest.model);
  
  // Create a new EventSource for SSE
  return new EventSource(`${API_BASE_URL}${API_PREFIX}/chat/chat/stream?${params.toString()}`);
};

/**
 * Get chat history
 * @param {string} sessionId Chat session ID
 * @param {number} limit Maximum number of history items
 * @returns {Promise<Array>} Chat history
 */
export const getChatHistory = async (sessionId, limit = 10) => {
  return await apiRequest(`/chat/history?session_id=${sessionId}&limit=${limit}`);
};

/**
 * Retrieve similar documents
 * @param {Object} retrieveQuery Retrieve query object
 * @returns {Promise<Object>} Retrieve response
 */
export const retrieveDocuments = async (retrieveQuery) => {
  return await apiRequest('/search/retrieve', {
    method: 'POST',
    body: JSON.stringify(retrieveQuery),
  });
};

/**
 * Retrieve similar documents (GET method)
 * @param {string} query Search query
 * @param {Object} filters Optional filters (ticker, year, etc.)
 * @returns {Promise<Object>} Retrieve response
 */
export const searchDocuments = async (query, filters = {}) => {
  const params = new URLSearchParams({
    q: query,
    k: filters.k || 5,
  });
  
  if (filters.ticker) params.append('ticker', filters.ticker);
  if (filters.year) params.append('year', filters.year);
  if (filters.document_type) params.append('document_type', filters.document_type);
  if (filters.section_name) params.append('section_name', filters.section_name);
  if (filters.similarity_threshold) params.append('similarity_threshold', filters.similarity_threshold);
  
  return await apiRequest(`/search/retrieve?${params.toString()}`);
};