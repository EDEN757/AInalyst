import React, { useState, useRef, useEffect } from 'react';
import '../App.css';

const CompanySelect = ({ companies, selectedCompanies, onChange }) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const toggleDropdown = () => {
    setIsOpen(!isOpen);
  };

  const handleCompanyToggle = (symbol) => {
    let newSelection;
    
    if (symbol === 'all') {
      // "All Companies" option - clears all selections
      newSelection = [];
    } else if (selectedCompanies.includes(symbol)) {
      // Remove company if already selected
      newSelection = selectedCompanies.filter(s => s !== symbol);
    } else {
      // Add company if not selected
      newSelection = [...selectedCompanies, symbol];
    }
    
    onChange(newSelection);
  };

  // Display text for the select box
  const getDisplayText = () => {
    if (selectedCompanies.length === 0) {
      return "All Companies";
    } else if (selectedCompanies.length === 1) {
      const company = companies.find(c => c.symbol === selectedCompanies[0]);
      return company ? `${company.name} (${company.symbol})` : selectedCompanies[0];
    } else {
      return `${selectedCompanies.length} Companies Selected`;
    }
  };

  return (
    <div className="company-select" ref={dropdownRef}>
      <label htmlFor="companySelect">Companies:</label>
      <div className="custom-select">
        <div className="select-header" onClick={toggleDropdown}>
          {getDisplayText()}
          <span className="dropdown-arrow">{isOpen ? '▲' : '▼'}</span>
        </div>
        
        {isOpen && (
          <div className="select-options">
            <div 
              className="select-option"
              onClick={() => handleCompanyToggle('all')}
            >
              <input 
                type="checkbox" 
                checked={selectedCompanies.length === 0} 
                readOnly 
              />
              <span>All Companies</span>
            </div>
            
            {companies.map((company) => (
              <div 
                key={company.symbol} 
                className="select-option"
                onClick={() => handleCompanyToggle(company.symbol)}
              >
                <input 
                  type="checkbox" 
                  checked={selectedCompanies.includes(company.symbol)} 
                  readOnly 
                />
                <span>{company.name} ({company.symbol})</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default CompanySelect;