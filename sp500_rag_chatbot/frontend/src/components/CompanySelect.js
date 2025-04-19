import React from 'react';

const CompanySelect = ({ companies, selectedCompany, onChange }) => {
  return (
    <div className="company-select">
      <label htmlFor="companySelect">Company:</label>
      <select
        id="companySelect"
        value={selectedCompany}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">All Companies</option>
        {companies.map((company) => (
          <option key={company.symbol} value={company.symbol}>
            {company.name} ({company.symbol})
          </option>
        ))}
      </select>
    </div>
  );
};

export default CompanySelect;
