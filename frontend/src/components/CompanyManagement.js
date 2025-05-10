import React, { useState, useEffect } from 'react';
import { getCompanies } from '../utils/api';
import { useAppContext } from '../context/AppContext';

const CompanyManagement = () => {
  // Context values
  const { loading: contextLoading, error: contextError } = useAppContext();

  // Local state
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortConfig, setSortConfig] = useState({ key: 'ticker', direction: 'asc' });

  // Fetch data on component mount
  useEffect(() => {
    fetchCompanies();
  }, []);

  // Fetch companies
  const fetchCompanies = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const data = await getCompanies();
      setCompanies(data);
    } catch (err) {
      console.error('Error fetching companies:', err);
      setError('Failed to load companies');
    } finally {
      setLoading(false);
    }
  };

  // Request refresh of data
  const refreshData = () => {
    fetchCompanies();
  };

  // Sort companies
  const sortedCompanies = [...companies].sort((a, b) => {
    if (a[sortConfig.key] < b[sortConfig.key]) {
      return sortConfig.direction === 'asc' ? -1 : 1;
    }
    if (a[sortConfig.key] > b[sortConfig.key]) {
      return sortConfig.direction === 'asc' ? 1 : -1;
    }
    return 0;
  });

  // Filter companies by search term
  const filteredCompanies = sortedCompanies.filter(company => 
    company.ticker.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Handle sort click
  const handleSort = (key) => {
    setSortConfig(prevConfig => ({
      key,
      direction: prevConfig.key === key && prevConfig.direction === 'asc' ? 'desc' : 'asc'
    }));
  };

  return (
    <div className="db-explorer">
      <div className="db-header">
        <h2>Database Explorer</h2>
        <div className="db-actions">
          <button className="refresh-button" onClick={refreshData} disabled={loading}>
            {loading ? 'Refreshing...' : 'Refresh Data'}
          </button>
          <div className="search-container">
            <input
              type="text"
              className="search-input"
              placeholder="Search by ticker..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        </div>
      </div>

      {loading && <div className="loading">Loading data...</div>}
      {error && <div className="error">{error}</div>}
      
      <div className="status-section">
        <h3>Database Status</h3>
        <div className="status-summary">
          <div className="status-item">
            <div className="status-label">Companies in Database:</div>
            <div className="status-value">{companies.length}</div>
          </div>
        </div>
      </div>

      <h3>Companies in Database</h3>
      {filteredCompanies.length > 0 ? (
        <div className="companies-grid">
          {filteredCompanies.map(company => (
            <div key={company.ticker} className="company-card">
              <h3>{company.ticker}</h3>
              <div className="company-details">
                <div className="years-label">Available Years:</div>
                <div className="years-list">
                  {company.years.map(year => (
                    <span key={year} className="year-badge">{year}</span>
                  ))}
                </div>
                <div className="document-count">
                  {company.total_documents} documents
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="no-results">
          {searchTerm ? 'No companies match your search.' : 'No companies in database.'}
        </div>
      )}

      <style jsx>{`
        .db-explorer {
          max-width: 1200px;
          margin: 0 auto;
          padding: 20px;
        }
        
        .db-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 24px;
        }
        
        .db-actions {
          display: flex;
          gap: 16px;
          align-items: center;
        }
        
        .refresh-button {
          padding: 8px 16px;
          background-color: var(--primary-color);
          color: white;
          border: none;
          border-radius: var(--border-radius);
          cursor: pointer;
        }
        
        .refresh-button:disabled {
          background-color: var(--secondary-color);
          cursor: not-allowed;
        }
        
        .search-container {
          position: relative;
        }
        
        .search-input {
          padding: 8px 12px;
          border: 1px solid var(--border-color);
          border-radius: var(--border-radius);
          min-width: 200px;
        }
        
        h2 {
          color: var(--primary-color);
          margin-bottom: 20px;
        }
        
        h3 {
          color: var(--text-color);
          margin-top: 24px;
          margin-bottom: 16px;
        }
        
        .loading {
          padding: 12px;
          background-color: #e6f7ff;
          border: 1px solid #91d5ff;
          border-radius: 4px;
          margin-bottom: 20px;
        }
        
        .error {
          padding: 12px;
          background-color: #fff2f0;
          border: 1px solid #ffccc7;
          border-radius: 4px;
          color: #f5222d;
          margin-bottom: 20px;
        }
        
        .status-section {
          background-color: #fafafa;
          border: 1px solid #e8e8e8;
          border-radius: 8px;
          padding: 16px;
          margin-bottom: 24px;
        }
        
        .status-summary {
          display: flex;
          gap: 24px;
          flex-wrap: wrap;
        }
        
        .status-item {
          display: flex;
          flex-direction: column;
          align-items: center;
        }
        
        .status-label {
          font-size: 0.9em;
          color: #8c8c8c;
          margin-bottom: 4px;
        }
        
        .status-value {
          font-size: 1.5em;
          font-weight: bold;
          color: #1890ff;
        }
       
        .companies-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
          gap: 16px;
        }
        
        .company-card {
          background-color: white;
          border: 1px solid #e8e8e8;
          border-radius: 8px;
          padding: 16px;
          transition: box-shadow 0.3s;
        }
        
        .company-card:hover {
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }
        
        .company-card h3 {
          margin-top: 0;
          margin-bottom: 12px;
          color: #1890ff;
        }
        
        .years-label {
          font-size: 0.9em;
          color: #8c8c8c;
          margin-bottom: 8px;
        }
        
        .years-list {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
          margin-bottom: 12px;
        }
        
        .year-badge {
          background-color: #f0f0f0;
          color: #595959;
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 0.8em;
        }
        
        .document-count {
          font-size: 0.9em;
          color: #8c8c8c;
        }
        
        .no-results {
          padding: 24px;
          text-align: center;
          color: #8c8c8c;
          background-color: #fafafa;
          border-radius: 8px;
        }
      `}</style>
    </div>
  );
};

export default CompanyManagement;