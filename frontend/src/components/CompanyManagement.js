import React, { useState, useEffect } from 'react';
import { getCompanies, getCompaniesStatus } from '../utils/api';
import { useAppContext } from '../context/AppContext';

const CompanyManagement = () => {
  // Context values
  const { loading: contextLoading, error: contextError } = useAppContext();

  // Local state
  const [companies, setCompanies] = useState([]);
  const [companiesStatus, setCompaniesStatus] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('database'); // 'database' or 'status'
  const [searchTerm, setSearchTerm] = useState('');
  const [sortConfig, setSortConfig] = useState({ key: 'ticker', direction: 'asc' });

  // Fetch data on component mount
  useEffect(() => {
    fetchCompanies();
    fetchCompaniesStatus();
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

  // Fetch companies status
  const fetchCompaniesStatus = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const data = await getCompaniesStatus();
      setCompaniesStatus(data);
    } catch (err) {
      console.error('Error fetching companies status:', err);
      setError('Failed to load companies status');
    } finally {
      setLoading(false);
    }
  };

  // Request refresh of data
  const refreshData = () => {
    fetchCompanies();
    fetchCompaniesStatus();
  };

  // Find companies that are in the CSV but not in the database
  const findMissingCompanies = () => {
    if (!companies.length || !companiesStatus.length) return [];

    const dbCompanies = new Set(companies.map(company => company.ticker));
    return companiesStatus.filter(company => !dbCompanies.has(company.ticker));
  };

  const missingCompanies = findMissingCompanies();

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

      <div className="tabs">
        <button
          className={`tab-button ${activeTab === 'database' ? 'active' : ''}`}
          onClick={() => setActiveTab('database')}
        >
          Database ({companies.length})
        </button>
        <button
          className={`tab-button ${activeTab === 'status' ? 'active' : ''}`}
          onClick={() => setActiveTab('status')}
        >
          Ingestion Status
        </button>
      </div>

      {loading && <div className="loading">Loading data...</div>}
      {error && <div className="error">{error}</div>}
      
      {activeTab === 'database' && (
        <>
          <div className="status-section">
            <h3>Database Status</h3>
            <div className="status-summary">
              <div className="status-item">
                <div className="status-label">Companies in Database:</div>
                <div className="status-value">{companies.length}</div>
              </div>
              <div className="status-item">
                <div className="status-label">Companies in CSV:</div>
                <div className="status-value">{companiesStatus.length}</div>
              </div>
              <div className="status-item">
                <div className="status-label">Missing Companies:</div>
                <div className="status-value">{missingCompanies.length}</div>
              </div>
            </div>
          </div>

          {missingCompanies.length > 0 && (
            <div className="missing-companies">
              <h3>Companies in CSV Awaiting Ingestion</h3>
              <ul>
                {missingCompanies.map(company => (
                  <li key={company.ticker}>
                    {company.ticker} - {company.company_name} ({company.start_year} to {company.end_year})
                  </li>
                ))}
              </ul>
            </div>
          )}

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
        </>
      )}

      {activeTab === 'status' && (
        <>
          <h3>Ingestion Status by Company</h3>
          {companiesStatus.length > 0 ? (
            <div className="status-table-container">
              <table className="status-table">
                <thead>
                  <tr>
                    <th onClick={() => handleSort('ticker')}>
                      Ticker {sortConfig.key === 'ticker' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                    </th>
                    <th>Company Name</th>
                    <th>Years Range</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {companiesStatus.map(company => {
                    // Calculate ingestion progress
                    const totalYears = company.end_year - company.start_year + 1;
                    const totalDocuments = totalYears * 2; // 10-K and 10-K/A per year
                    
                    let ingestedDocuments = 0;
                    company.years.forEach(yearData => {
                      yearData.documents.forEach(doc => {
                        if (doc.exists) ingestedDocuments++;
                      });
                    });
                    
                    const progressPercent = Math.round((ingestedDocuments / totalDocuments) * 100);
                    
                    return (
                      <tr key={company.ticker}>
                        <td>{company.ticker}</td>
                        <td>{company.company_name}</td>
                        <td>{company.start_year} - {company.end_year}</td>
                        <td>
                          <div className="progress-container">
                            <div 
                              className="progress-bar" 
                              style={{width: `${progressPercent}%`}}
                            ></div>
                            <span className="progress-text">{progressPercent}%</span>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="no-results">No ingestion status available.</div>
          )}
        </>
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
        
        .tabs {
          display: flex;
          margin-bottom: 24px;
          border-bottom: 1px solid var(--border-color);
        }
        
        .tab-button {
          padding: 12px 20px;
          background: none;
          border: none;
          border-bottom: 2px solid transparent;
          cursor: pointer;
          font-weight: 500;
        }
        
        .tab-button.active {
          color: var(--primary-color);
          border-bottom: 2px solid var(--primary-color);
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
        
        .missing-companies {
          background-color: #fffbe6;
          border: 1px solid #ffe58f;
          border-radius: 8px;
          padding: 16px;
          margin-bottom: 24px;
        }
        
        .missing-companies h3 {
          color: #d48806;
          margin-top: 0;
        }
        
        .missing-companies ul {
          padding-left: 20px;
          margin: 0;
        }
        
        .missing-companies li {
          margin-bottom: 8px;
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
        
        .status-table-container {
          overflow-x: auto;
        }
        
        .status-table {
          width: 100%;
          border-collapse: collapse;
        }
        
        .status-table th {
          background-color: #fafafa;
          padding: 12px 16px;
          text-align: left;
          border-bottom: 1px solid #e8e8e8;
          cursor: pointer;
        }
        
        .status-table th:hover {
          background-color: #f0f0f0;
        }
        
        .status-table td {
          padding: 12px 16px;
          border-bottom: 1px solid #e8e8e8;
        }
        
        .progress-container {
          width: 100%;
          background-color: #f0f0f0;
          border-radius: 4px;
          height: 20px;
          position: relative;
        }
        
        .progress-bar {
          height: 100%;
          background-color: #52c41a;
          border-radius: 4px;
        }
        
        .progress-text {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          display: flex;
          align-items: center;
          justify-content: center;
          color: #595959;
          font-size: 0.8em;
          font-weight: 500;
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