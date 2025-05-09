import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import '../App.css';

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
      const response = await axios.get(`${apiUrl}/api/v1/companies`);
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
      const response = await axios.get(`${apiUrl}/api/v1/companies/${symbol}/filings`);
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
      const response = await axios.delete(`${apiUrl}/api/v1/companies/${symbol}`);
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
      const response = await axios.post(`${apiUrl}/api/v1/companies/import-from-csv`);
      
      console.log('CSV import response:', response.data);
      
      if (response.data.status === 'processing') {
        alert(`Importing ${response.data.companies.length} queries from CSV. Processing in background. Please check back in a few minutes.`);
      }
      
      // Refresh companies list after a short delay
      setTimeout(fetchCompanies, 3000);
      
    } catch (error) {
      console.error('Error importing from CSV:', error);
      setError(`Error importing from CSV: ${error.response?.data?.detail || error.message}`);
      alert(`Error importing from CSV: ${error.response?.data?.detail || "Check if companies_to_import.csv exists in project root"}`);
    } finally {
      setCsvImporting(false);
      setLoading(false);
    }
  };
  
  const handleDownloadTemplate = async () => {
    try {
      const response = await axios.get(`${apiUrl}/api/v1/companies/csv-template`);
      
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
              <p>Import companies defined in the project's CSV file</p>
              <div className="csv-actions">
                <button 
                  onClick={handleDownloadTemplate} 
                  className="button secondary"
                  disabled={loading}
                >
                  Download Template
                </button>
                <button 
                  onClick={handleImportFromCsv} 
                  className="button primary"
                  disabled={loading}
                >
                  {csvImporting ? 'Importing...' : 'Import from CSV'}
                </button>
              </div>
              <p><strong>Note:</strong> Edit companies_to_import.csv in the project root to add companies</p>
              <p><strong>CSV Format:</strong> ticker,doc_type,date_range</p>
              <p><strong>Example:</strong> AAPL,10-K,2020-01-01,2025-12-31</p>
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