import React, { useState, useEffect } from 'react';
import { useAppContext } from '../context/AppContext';
import { getCompanies, getCompanyDetails } from '../utils/api';

const CompanySelect = () => {
  // Get context values
  const { 
    companies: contextCompanies,
    selectedCompany, 
    setSelectedCompany, 
    selectedYear, 
    setSelectedYear,
    selectedSection,
    setSelectedSection, 
    clearFilters
  } = useAppContext();

  // Local state
  const [companies, setCompanies] = useState([]);
  const [companyDetails, setCompanyDetails] = useState(null);
  const [years, setYears] = useState([]);
  const [sections, setSections] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Initialize companies from context if available
  useEffect(() => {
    if (contextCompanies && contextCompanies.length > 0) {
      setCompanies(contextCompanies);
    } else {
      fetchCompanies();
    }
  }, [contextCompanies]);

  // Fetch company details when selected company changes
  useEffect(() => {
    if (selectedCompany) {
      fetchCompanyDetails(selectedCompany);
    } else {
      setCompanyDetails(null);
      setYears([]);
      setSections([]);
    }
  }, [selectedCompany]);

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

  // Fetch company details
  const fetchCompanyDetails = async (ticker) => {
    setLoading(true);
    setError(null);
    
    try {
      const details = await getCompanyDetails(ticker);
      setCompanyDetails(details);
      
      // Get available years
      if (details.years) {
        setYears(details.years);
      }
      
      // Get available sections
      if (details.section_counts) {
        const sectionList = Object.keys(details.section_counts).map(section => ({
          name: section,
          count: details.section_counts[section]
        }));
        setSections(sectionList);
      }
    } catch (err) {
      console.error(`Error fetching details for ${ticker}:`, err);
      setError(`Failed to load details for ${ticker}`);
      setCompanyDetails(null);
      setYears([]);
      setSections([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="company-select">
      {/* Company dropdown */}
      <div className="select-container">
        <label htmlFor="company-select">Company</label>
        <select
          id="company-select"
          className="select-field"
          value={selectedCompany}
          onChange={(e) => setSelectedCompany(e.target.value)}
          disabled={loading}
        >
          <option value="">All Companies</option>
          {companies.map((company) => (
            <option key={company.ticker} value={company.ticker}>
              {company.ticker}
            </option>
          ))}
        </select>
      </div>
      
      {/* Year dropdown */}
      <div className="select-container">
        <label htmlFor="year-select">Year</label>
        <select
          id="year-select"
          className="select-field"
          value={selectedYear}
          onChange={(e) => setSelectedYear(e.target.value)}
          disabled={loading || !selectedCompany || years.length === 0}
        >
          <option value="">All Years</option>
          {years.map((year) => (
            <option key={year} value={year}>
              {year}
            </option>
          ))}
        </select>
      </div>
      
      {/* Section dropdown */}
      <div className="select-container">
        <label htmlFor="section-select">Section</label>
        <select
          id="section-select"
          className="select-field"
          value={selectedSection}
          onChange={(e) => setSelectedSection(e.target.value)}
          disabled={loading || !selectedCompany || sections.length === 0}
        >
          <option value="">All Sections</option>
          {sections.map((section) => (
            <option key={section.name} value={section.name}>
              {section.name} ({section.count})
            </option>
          ))}
        </select>
      </div>
      
      {/* Clear filters button */}
      {(selectedCompany || selectedYear || selectedSection) && (
        <button 
          className="clear-button"
          onClick={clearFilters}
          disabled={loading}
        >
          Clear Filters
        </button>
      )}
      
      {/* Error message */}
      {error && <div className="error-message">{error}</div>}
      
      <style jsx>{`
        .company-select {
          display: flex;
          gap: 12px;
          align-items: flex-end;
          flex-wrap: wrap;
        }
        
        .select-container {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        
        label {
          font-size: 0.8rem;
          color: var(--text-light);
        }
        
        .select-field {
          padding: 8px 12px;
          border: 1px solid var(--border-color);
          border-radius: var(--border-radius);
          background-color: white;
          min-width: 150px;
        }
        
        .select-field:focus {
          outline: none;
          border-color: var(--primary-color);
          box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
        }
        
        .select-field:disabled {
          background-color: #f5f5f5;
          cursor: not-allowed;
        }
        
        .clear-button {
          padding: 8px 12px;
          background-color: transparent;
          border: 1px solid var(--border-color);
          color: var(--text-light);
          border-radius: var(--border-radius);
          cursor: pointer;
          transition: all 0.2s;
          align-self: flex-end;
          height: 34px;
        }
        
        .clear-button:hover {
          background-color: #f5f5f5;
        }
        
        .error-message {
          color: var(--error-color);
          font-size: 0.9em;
          margin-left: 12px;
        }
      `}</style>
    </div>
  );
};

export default CompanySelect;