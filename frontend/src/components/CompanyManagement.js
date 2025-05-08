import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import '../App.css';

const CompanyManagement = ({ apiUrl, onCompaniesUpdated }) => {
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [newSymbol, setNewSymbol] = useState('');
  const [filingLimit, setFilingLimit] = useState(2);
  const [selectedCompany, setSelectedCompany] = useState(null);
  const [filings, setFilings] = useState([]);
  const [isFirstVisit, setIsFirstVisit] = useState(true);
  const [processingCompany, setProcessingCompany] = useState(null);
  const [csvFile, setCsvFile] = useState(null);
  const [csvUploading, setCsvUploading] = useState(false);
  const fileInputRef = useRef(null);

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

  const handleAddCompany = async (e) => {
    e.preventDefault();
    
    if (!newSymbol.trim()) return;
    
    setLoading(true);
    setError(null);
    setProcessingCompany(newSymbol);
    
    try {
      const response = await axios.post(`${apiUrl}/api/v1/companies/add`, {
        symbol: newSymbol.toUpperCase(),
        filing_limit: filingLimit
      });
      
      console.log('Add company response:', response.data);
      
      // Show success message based on response
      if (response.data.status === 'success') {
        alert(`Company ${newSymbol.toUpperCase()} already exists!`);
      } else if (response.data.status === 'processing') {
        alert(`Adding ${newSymbol.toUpperCase()} to the database (processing in background). Please check back in a minute.`);
      }
      
      // Clear the form
      setNewSymbol('');
      
      // Refresh companies list after a short delay
      setTimeout(fetchCompanies, 3000);
      
    } catch (error) {
      console.error('Error adding company:', error);
      setError('Error adding company. Please try again later.');
    } finally {
      setLoading(false);
      setProcessingCompany(null);
    }
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

  const handleAddDemoCompanies = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.post(`${apiUrl}/api/v1/companies/add-demo`, {
        enabled: true
      });
      
      console.log('Add demo companies response:', response.data);
      alert('Adding demo companies (AAPL, MSFT, GOOGL). Please check back in a minute.');
      
      // Refresh companies list after a short delay
      setTimeout(fetchCompanies, 3000);
      
    } catch (error) {
      console.error('Error adding demo companies:', error);
      setError('Error adding demo companies. Please try again later.');
    } finally {
      setLoading(false);
    }
  };
  
  const handleCsvFileChange = (e) => {
    if (e.target.files.length > 0) {
      setCsvFile(e.target.files[0]);
    } else {
      setCsvFile(null);
    }
  };
  
  const handleCsvUpload = async (e) => {
    e.preventDefault();
    
    if (!csvFile) {
      alert('Please select a CSV file first');
      return;
    }
    
    if (!csvFile.name.endsWith('.csv')) {
      alert('Please select a CSV file');
      return;
    }
    
    setCsvUploading(true);
    setLoading(true);
    setError(null);
    
    try {
      // Create form data object
      const formData = new FormData();
      formData.append('file', csvFile);
      
      // Upload the CSV file
      const response = await axios.post(
        `${apiUrl}/api/v1/companies/import-csv`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        }
      );
      
      console.log('CSV import response:', response.data);
      
      if (response.data.status === 'processing') {
        alert(`Importing ${response.data.companies.length} companies from CSV. Processing in background. Please check back in a few minutes.`);
      }
      
      // Clear the file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      setCsvFile(null);
      
      // Refresh companies list after a short delay
      setTimeout(fetchCompanies, 3000);
      
    } catch (error) {
      console.error('Error uploading CSV:', error);
      setError(`Error uploading CSV: ${error.response?.data?.detail || error.message}`);
    } finally {
      setCsvUploading(false);
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
          <p>You can either:</p>
          <ul>
            <li>Load demo companies (Apple, Microsoft, Google) to explore the app quickly</li>
            <li>Add specific companies by entering their ticker symbols</li>
          </ul>
          <button 
            className="button primary" 
            onClick={handleAddDemoCompanies}
            disabled={loading}
          >
            Load Demo Companies
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
              <p>Add companies using the form or load demo companies.</p>
              <button 
                className="button secondary" 
                onClick={handleAddDemoCompanies}
                disabled={loading}
              >
                Load Demo Companies
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
          
          <div className="add-company-form">
            <h4>Add New Company</h4>
            <form onSubmit={handleAddCompany}>
              <div className="form-group">
                <label htmlFor="newSymbol">Ticker Symbol:</label>
                <input
                  type="text"
                  id="newSymbol"
                  value={newSymbol}
                  onChange={(e) => setNewSymbol(e.target.value)}
                  placeholder="e.g., AAPL"
                  required
                  disabled={loading}
                />
              </div>
              <div className="form-group">
                <label htmlFor="filingLimit">Number of 10-Ks:</label>
                <select
                  id="filingLimit"
                  value={filingLimit}
                  onChange={(e) => setFilingLimit(Number(e.target.value))}
                  disabled={loading}
                >
                  <option value="1">1 (Latest)</option>
                  <option value="2">2 (Last two years)</option>
                  <option value="3">3 (Last three years)</option>
                  <option value="5">5 (Last five years)</option>
                </select>
              </div>
              <button 
                type="submit" 
                className="button primary"
                disabled={loading || !newSymbol.trim()}
              >
                {loading && processingCompany === newSymbol ? 'Adding...' : 'Add Company'}
              </button>
            </form>
            
            <div className="csv-upload-section">
              <h4>Bulk Import from CSV</h4>
              <div className="csv-template-info">
                <p>Import multiple companies at once from a CSV file</p>
                <button 
                  onClick={handleDownloadTemplate} 
                  className="button secondary"
                  disabled={loading}
                >
                  Download CSV Template
                </button>
              </div>
              
              <form onSubmit={handleCsvUpload} className="csv-upload-form">
                <div className="form-group">
                  <label htmlFor="csvFile">Select CSV File:</label>
                  <input
                    type="file"
                    id="csvFile"
                    onChange={handleCsvFileChange}
                    accept=".csv"
                    ref={fileInputRef}
                    disabled={loading}
                  />
                </div>
                <button 
                  type="submit" 
                  className="button primary"
                  disabled={loading || !csvFile}
                >
                  {csvUploading ? 'Uploading...' : 'Upload CSV'}
                </button>
              </form>
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