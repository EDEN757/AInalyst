import React from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom';
import './App.css';

// Import components
import ChatInterface from './components/ChatInterface';
import CompanyManagement from './components/CompanyManagement';
import { AppProvider } from './context/AppContext';

// Main App component
function App() {
  return (
    <AppProvider>
      <Router>
        <div className="App">
          <header className="header">
            <h1>AInalyst</h1>
            <nav className="navbar">
              <NavLink to="/" end>Chat</NavLink>
              <NavLink to="/companies">Company Database</NavLink>
            </nav>
          </header>

          <main className="main-content">
            <Routes>
              <Route path="/" element={<ChatInterface />} />
              <Route path="/companies" element={<CompanyManagement />} />
            </Routes>
          </main>
        </div>
      </Router>
    </AppProvider>
  );
}


export default App;