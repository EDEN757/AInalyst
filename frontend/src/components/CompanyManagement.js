import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import '../App.css';

// Import our custom apiClient or create a new one if not available
const apiClient = window.apiClient || axios;

const CompanyManagement = ({ apiUrl, onCompaniesUpdated }) => {
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedCompany, setSelectedCompany] = useState(null);
  const [filings, setFilings] = useState([]);
  const [isFirstVisit, setIsFirstVisit] = useState(true);
  const [csvImporting, setCsvImporting] = useState(false);
  const [importStatus, setImportStatus] = useState(null);
  const [importStatusTimer, setImportStatusTimer] = useState(null);
  const [csvImportResults, setCsvImportResults] = useState(null);

  // Determine the active API URL (fallback or primary)
  const getEffectiveApiUrl = () => {
    return window.workingApiUrl || apiUrl;
  };

  // Fetch companies on component mount
  useEffect(() => {
    fetchCompanies();
    
    // Check if this is the first visit
    const hasVisited = localStorage.getItem('hasVisitedCompanyManagement');
    if (!hasVisited) {
      setIsFirstVisit(true);
      localStorage.setItem('hasVisitedCompanyManagement', 'true');
    } else {
      setIsFirstVisit(false);
    }

    // Start checking import status
    checkImportStatus();

    // Cleanup on component unmount
    return () => {
      if (importStatusTimer) {
        clearInterval(importStatusTimer);
      }
    };
  }, []);

  const fetchCompanies = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Use the working URL if one was found, otherwise fall back to the default
      const effectiveApiUrl = getEffectiveApiUrl();
      console.log(`Fetching companies using API URL: ${effectiveApiUrl}`);
      
      const response = await apiClient.get(`${effectiveApiUrl}/api/v1/companies`);
      setCompanies(response.data);
      
      // Notify parent component that companies were updated
      if (onCompaniesUpdated) {
        onCompaniesUpdated(response.data);
      }
      
    } catch (error) {
      console.error('Error fetching companies:', error);
      setError('Error fetching companies. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  const fetchFilings = async (symbol) => {
    if (!symbol) return;
    
    setLoading(true);
    setError(null);
    
    try {
      // Use the working URL if one was found, otherwise fall back to the default
      const effectiveApiUrl = getEffectiveApiUrl();
      console.log(`Fetching filings for ${symbol} using API URL: ${effectiveApiUrl}`);
      
      const response = await apiClient.get(`${effectiveApiUrl}/api/v1/companies/${symbol}/filings`);
      setFilings(response.data);
    } catch (error) {
      console.error(`Error fetching filings for ${symbol}:`, error);
      setError(`Error fetching filings for ${symbol}`);
      setFilings([]);
    } finally {
      setLoading(false);
    }
  };

  const handleCompanySelect = (company) => {
    setSelectedCompany(company);
    fetchFilings(company.symbol);
  };

  const handleDeleteCompany = async (symbol) => {
    if (!window.confirm(`Are you sure you want to delete ${symbol} and all its data?`)) {
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      // Use the working URL if one was found, otherwise fall back to the default
      const effectiveApiUrl = getEffectiveApiUrl();
      console.log(`Deleting company ${symbol} using API URL: ${effectiveApiUrl}`);
      
      const response = await apiClient.delete(`${effectiveApiUrl}/api/v1/companies/${symbol}`);
      console.log('Delete company response:', response.data);
      
      // Refresh companies list
      fetchCompanies();
      
      // Clear selected company if it's the one deleted
      if (selectedCompany && selectedCompany.symbol === symbol) {
        setSelectedCompany(null);
        setFilings([]);
      }
      
    } catch (error) {
      console.error(`Error deleting company ${symbol}:`, error);
      setError(`Error deleting company ${symbol}`);
    } finally {
      setLoading(false);
    }
  };
  
  const handleImportFromCsv = async () => {
    setLoading(true);
    setError(null);
    setCsvImporting(true);
    setCsvImportResults(null);

    try {
      // Use the working URL if one was found, otherwise fall back to the default
      const effectiveApiUrl = getEffectiveApiUrl();
      console.log(`Importing CSV using API URL: ${effectiveApiUrl}`);
      
      // Call the API to process the CSV file in the project
      const response = await apiClient.post(`${effectiveApiUrl}/api/v1/companies/import-from-csv`);
      console.log('CSV import response:', response.data);

      if (response.data.status === 'processing') {
        // Start polling the import status
        startStatusPolling();
        
        // Show importation started success message
        const companies = response.data.companies || [];
        setCsvImportResults({
          status: 'processing',
          message: `Started importing ${companies.length} companies. Processing in background.`,
          companies: companies
        });
      }

      // Refresh companies list after a short delay
      setTimeout(fetchCompanies, 3000);

    } catch (error) {
      console.error('Error importing from CSV:', error);
      handleCsvImportError(error);
    } finally {
      setCsvImporting(false);
      setLoading(false);
    }
  };

  const handleCsvImportError = (error) => {
    // Set error state for display in UI
    setError(`Error importing from CSV: ${error.response?.data?.detail || error.message}`);

    // Create detailed error information for display
    let errorDetails = {
      status: 'error',
      message: 'Error importing from CSV'
    };

    if (error.response) {
      if (error.response.status === 404) {
        // CSV file not found error
        errorDetails.message = error.response.data.detail ||
                    "The companies_to_import.csv file wasn't found. Please download the template, edit it with your companies, and place it in the project root directory.";
        errorDetails.type = 'file_not_found';
      } else if (error.response.status === 500) {
        // Server error
        errorDetails.message = "There was a server error processing the CSV file.\n\n" +
                    "Server message: " + (error.response.data.detail || error.response.statusText);
        errorDetails.type = 'server_error';
      } else if (error.response.status === 400) {
        // Bad request (likely invalid CSV format)
        errorDetails.message = error.response.data.detail || "Invalid CSV format. Please check the template and try again.";
        errorDetails.type = 'invalid_format';
      } else {
        // Other API error
        errorDetails.message = error.response.data.detail || error.response.statusText;
        errorDetails.type = 'api_error';
      }
    } else if (error.request) {
      // Network error
      errorDetails.message = "Could not connect to the server. Please check that the backend is running.\n\nIf you're using Docker, make sure all containers are up and running with 'docker-compose ps'.";
      errorDetails.type = 'network_error';
    } else {
      // Other error
      errorDetails.message = error.message;
      errorDetails.type = 'unknown_error';
    }

    setCsvImportResults(errorDetails);
  };
  
  const handleDownloadTemplate = async () => {
    try {
      // Use the working URL if one was found, otherwise fall back to the default
      const effectiveApiUrl = getEffectiveApiUrl();
      console.log(`Downloading template using API URL: ${effectiveApiUrl}`);
      
      const response = await apiClient.get(`${effectiveApiUrl}/api/v1/companies/csv-template`);
      
      // Create a blob from the CSV content
      const blob = new Blob([response.data.content], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      
      // Create a temporary link element and trigger download
      const a = document.createElement('a');
      a.href = url;
      a.download = response.data.filename;
      document.body.appendChild(a);
      a.click();
      
      // Clean up
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      // Show instructions
      alert(response.data.instructions);
      
    } catch (error) {
      console.error('Error downloading template:', error);
      setError('Error downloading CSV template. Please try again later.');
    }
  };

  const startStatusPolling = () => {
    // Clear existing timer if any
    if (importStatusTimer) {
      clearInterval(importStatusTimer);
    }

    // Set up a new interval to check import status every 5 seconds
    const timer = setInterval(checkImportStatus, 5000);
    setImportStatusTimer(timer);
  };

  const checkImportStatus = async () => {
    try {
      const effectiveApiUrl = getEffectiveApiUrl();
      const response = await apiClient.get(`${effectiveApiUrl}/api/v1/companies/import-status`);
      
      if (response.data) {
        setImportStatus(response.data);
      }
    } catch (error) {
      console.warn("Error checking import status:", error);
      // Don't set an error - this is a background check
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString();
  };

  const renderImportResults = () => {
    if (!csvImportResults) return null;

    if (csvImportResults.status === 'processing') {
      return (
        <div className="csv-import-results success">
          <h4><span className="status-icon">⏳</span> Import Started</h4>
          <p>{csvImportResults.message}</p>
          {csvImportResults.companies && csvImportResults.companies.length > 0 && (
            <div className="importing-companies">
              <p>Companies being imported:</p>
              <ul className="companies-list">
                {csvImportResults.companies.slice(0, 5).map((company, index) => (
                  <li key={index}>{company}</li>
                ))}
                {csvImportResults.companies.length > 5 && (
                  <li>...and {csvImportResults.companies.length - 5} more</li>
                )}
              </ul>
            </div>
          )}
        </div>
      );
    } else if (csvImportResults.status === 'error') {
      return (
        <div className="csv-import-results error">
          <h4><span className="status-icon">❌</span> Import Failed</h4>
          <p>{csvImportResults.message}</p>
          <div className="error-troubleshooting">
            <h5>Troubleshooting:</h5>
            {csvImportResults.type === 'file_not_found' && (
              <ul>
                <li>Download the CSV template and save it as <code>companies_to_import.csv</code></li>
                <li>Place the CSV file in the project root directory (not inside backend or frontend folders)</li>
                <li>Ensure the file has the correct name: <code>companies_to_import.csv</code></li>
              </ul>
            )}
            {csvImportResults.type === 'invalid_format' && (
              <ul>
                <li>Make sure the CSV has the required headers: ticker and doc_type</li>
                <li>Check that date formats are YYYY-MM-DD</li>
                <li>Make sure there are no empty rows or special characters</li>
              </ul>
            )}
            {csvImportResults.type === 'network_error' && (
              <ul>
                <li>Check that both frontend and backend containers are running</li>
                <li>Run <code>docker-compose ps</code> to verify container status</li>
                <li>Check container logs for any errors</li>
              </ul>
            )}
            {(csvImportResults.type === 'server_error' || csvImportResults.type === 'unknown_error') && (
              <ul>
                <li>Check backend logs for detailed error information</li>
                <li>Ensure CSV format matches the template</li>
                <li>Try with a smaller number of companies initially</li>
              </ul>
            )}
          </div>
        </div>
      );
    }
    
    return null;
  };

  const renderImportStatus = () => {
    if (!importStatus) return null;

    return (
      <div className="import-status">
        <h5>System Status:</h5>
        <div className="status-items">
          <div className="status-item">
            <span className="status-label">Companies:</span>
            <span className="status-value">{importStatus.companies}</span>
          </div>
          <div className="status-item">
            <span className="status-label">Filings:</span>
            <span className="status-value">{importStatus.filings.processing_progress}</span>
            <span className="status-percent">{importStatus.filings.total > 0 ? 
              `(${Math.round((importStatus.filings.processed / importStatus.filings.total) * 100)}%)` : 
              '(0%)'}</span>
          </div>
          <div className="status-item">
            <span className="status-label">Embeddings:</span>
            <span className="status-value">{importStatus.chunks.embedding_progress}</span>
            <span className="status-percent">{importStatus.chunks.total > 0 ? 
              `(${Math.round((importStatus.chunks.embedded / importStatus.chunks.total) * 100)}%)` : 
              '(0%)'}</span>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="company-management">
      <h2>Company Management</h2>
      
      {/* Onboarding prompt for first-time users */}
      {isFirstVisit && companies.length === 0 && (
        <div className="onboarding-prompt">
          <h3>Welcome to AInalyst!</h3>
          <p>To get started, you need to add companies to your database.</p>
          <p>Use the CSV import feature to add companies and filings:</p>
          <ol>
            <li>Download the CSV template</li>
            <li>Edit it to include the companies you want to analyze</li>
            <li>Save the file as <code>companies_to_import.csv</code> in the project root directory</li>
            <li>Import the file using the button below</li>
          </ol>
          <button 
            className="button primary" 
            onClick={handleDownloadTemplate}
            disabled={loading}
          >
            Download CSV Template
          </button>
        </div>
      )}
      
      <div className="management-container">
        <div className="companies-panel">
          <h3>Companies in Database</h3>
          
          {loading && !companies.length && <div className="loading">Loading...</div>}
          {error && <div className="error">{error}</div>}
          
          {!loading && !error && companies.length === 0 && (
            <div className="empty-state">
              <p>No companies found in the database.</p>
              <p>Add companies using the CSV import feature.</p>
              <button 
                className="button secondary" 
                onClick={handleDownloadTemplate}
                disabled={loading}
              >
                Download CSV Template
              </button>
            </div>
          )}
          
          {companies.length > 0 && (
            <div className="company-list">
              <table>
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Name</th>
                    <th>Filings</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {companies.map(company => (
                    <tr 
                      key={company.symbol}
                      className={selectedCompany && selectedCompany.symbol === company.symbol ? 'selected' : ''}
                      onClick={() => handleCompanySelect(company)}
                    >
                      <td>{company.symbol}</td>
                      <td>{company.name}</td>
                      <td>{company.filings_count || 0}</td>
                      <td>
                        <button 
                          className="button-small danger"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteCompany(company.symbol);
                          }}
                          disabled={loading}
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          
          <div className="csv-import-section">
            <h4>Import Companies from CSV</h4>
            
            {/* Show import results if available */}
            {renderImportResults()}
            
            {/* Show import status */}
            {renderImportStatus()}
            
            <div className="csv-info">
              <div className="csv-instructions">
                <h5>How to Import Companies:</h5>
                <ol>
                  <li>Download the CSV template using the button below</li>
                  <li>Edit the CSV to add the companies and filings you need</li>
                  <li>Place the edited file in the project root directory as <code>companies_to_import.csv</code></li>
                  <li>Click the "Import from CSV" button to load the companies</li>
                </ol>

                <div className="csv-format-info">
                  <h5>CSV Format:</h5>
                  <p><strong>Required Columns:</strong></p>
                  <ul>
                    <li><code>ticker</code> - Company symbol (e.g., AAPL)</li>
                    <li><code>doc_type</code> - Filing type (e.g., 10-K, 10-Q, 8-K)</li>
                  </ul>
                  <p><strong>Optional Columns:</strong></p>
                  <ul>
                    <li><code>cik</code> - SEC Central Index Key (speeds up import)</li>
                    <li><code>start_date</code> - Start date in YYYY-MM-DD format</li>
                    <li><code>end_date</code> - End date in YYYY-MM-DD format</li>
                  </ul>
                </div>
              </div>

              <div className="csv-actions">
                <button
                  onClick={handleDownloadTemplate}
                  className="button secondary"
                  disabled={loading}
                >
                  1. Download Template
                </button>
                <button
                  onClick={handleImportFromCsv}
                  className="button primary"
                  disabled={loading || csvImporting}
                >
                  {csvImporting ? 'Importing...' : '2. Import from CSV'}
                </button>
              </div>
            </div>
          </div>
        </div>
        
        <div className="filings-panel">
          <h3>Company Filings</h3>
          
          {!selectedCompany && (
            <div className="empty-state">
              <p>Select a company to view its filings</p>
            </div>
          )}
          
          {selectedCompany && (
            <>
              <h4>{selectedCompany.name} ({selectedCompany.symbol})</h4>
              
              {loading && <div className="loading">Loading filings...</div>}
              {error && <div className="error">{error}</div>}
              
              {!loading && !error && filings.length === 0 && (
                <div className="empty-state">
                  <p>No filings found for {selectedCompany.symbol}</p>
                </div>
              )}
              
              {filings.length > 0 && (
                <div className="filings-list">
                  <table>
                    <thead>
                      <tr>
                        <th>Type</th>
                        <th>Date</th>
                        <th>Year</th>
                        <th>Status</th>
                        <th>Chunks</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filings.map(filing => (
                        <tr key={filing.id}>
                          <td>{filing.filing_type}</td>
                          <td>{formatDate(filing.filing_date)}</td>
                          <td>{filing.fiscal_year}</td>
                          <td>
                            <span className={filing.processed ? 'status-processed' : 'status-pending'}>
                              {filing.processed ? 'Processed' : 'Pending'}
                            </span>
                          </td>
                          <td>{filing.chunks_count || 0}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default CompanyManagement;