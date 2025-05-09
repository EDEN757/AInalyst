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
  }, []);

  const fetchCompanies = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await apiClient.get(`${apiUrl}/api/v1/companies`);
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
      const response = await apiClient.get(`${apiUrl}/api/v1/companies/${symbol}/filings`);
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
      const response = await apiClient.delete(`${apiUrl}/api/v1/companies/${symbol}`);
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

    try {
      // Call the API to process the CSV file in the project
      const response = await apiClient.post(`${apiUrl}/api/v1/companies/import-from-csv`);

      console.log('CSV import response:', response.data);

      if (response.data.status === 'processing') {
        // Show a more detailed success message
        const importMessage = `Successfully started import of ${response.data.companies.length} companies:

${response.data.companies.slice(0, 5).join('\n')}${response.data.companies.length > 5 ? '\n...(and more)' : ''}

Processing in background. Please check back in a few minutes.`;

        alert(importMessage);
      }

      // Refresh companies list after a short delay
      setTimeout(fetchCompanies, 3000);

    } catch (error) {
      console.error('Error importing from CSV:', error);

      // Set error state for display in UI
      setError(`Error importing from CSV: ${error.response?.data?.detail || error.message}`);

      // Create a more helpful error message
      let errorMessage = 'Error importing from CSV: ';

      if (error.response) {
        if (error.response.status === 404) {
          // CSV file not found error
          errorMessage += error.response.data.detail ||
                        "The companies_to_import.csv file wasn't found.\n\n" +
                        "Please download the template, edit it with your companies, and place it in the project root directory.";
        } else if (error.response.status === 500) {
          // Server error
          errorMessage += "There was a server error processing the CSV file.\n\n" +
                        "Server message: " + (error.response.data.detail || error.response.statusText);
        } else {
          // Other API error
          errorMessage += error.response.data.detail || error.response.statusText;
        }
      } else if (error.request) {
        // Network error
        errorMessage += "Could not connect to the server. Please check that the backend is running.\n\n" +
                      "If you're using Docker, make sure all containers are up and running with 'docker-compose ps'.";
      } else {
        // Other error
        errorMessage += error.message;
      }

      // Show error dialog
      alert(errorMessage);
    } finally {
      setCsvImporting(false);
      setLoading(false);
    }
  };
  
  const handleDownloadTemplate = async () => {
    try {
      const response = await apiClient.get(`${apiUrl}/api/v1/companies/csv-template`);
      
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
      alert('Error downloading CSV template');
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString();
  };

  return (
    <div className="company-management">
      <h2>Company Management</h2>
      
      {isFirstVisit && companies.length === 0 && (
        <div className="onboarding-prompt">
          <h3>Welcome to AInalyst!</h3>
          <p>To get started, you need to add companies to your database.</p>
          <p>Use the CSV import feature to add companies and filings:</p>
          <ul>
            <li>Download the CSV template</li>
            <li>Edit it to include the companies and filing types you want</li>
            <li>Place it in the project root</li>
            <li>Import it using the button below</li>
          </ul>
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
                  <p><strong>Headers:</strong> ticker,doc_type,start_date,end_date</p>
                  <p><strong>Example:</strong> AAPL,10-K,2020-01-01,2025-12-31</p>
                  <p><strong>Supported Doc Types:</strong> 10-K, 10-Q, 8-K</p>
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
                  disabled={loading}
                >
                  {csvImporting ? 'Importing...' : '2. Import from CSV'}
                </button>
              </div>

              {error && (
                <div className="csv-error-help">
                  <h5>Troubleshooting:</h5>
                  <p>If you're having issues with the CSV import:</p>
                  <ul>
                    <li>Make sure the CSV file is named exactly <code>companies_to_import.csv</code></li>
                    <li>Check that the file is in the correct location (project root)</li>
                    <li>Verify the CSV has the correct format with headers</li>
                    <li>If using Docker, ensure volumes are mounted correctly</li>
                  </ul>
                </div>
              )}
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