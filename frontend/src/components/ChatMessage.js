import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';

const ChatMessage = ({ message }) => {
  const [showSources, setShowSources] = useState(false);

  const toggleSources = () => {
    setShowSources(!showSources);
  };

  return (
    <div className={`chat-message ${message.role}`}>
      <div className="message-header">
        <span className="message-role">
          {message.role === 'user' ? 'You' : 'AInalyst'}
        </span>
      </div>
      
      <div className="message-content">
        <ReactMarkdown>{message.content}</ReactMarkdown>
      </div>
      
      {message.sources && message.sources.length > 0 && (
        <div className="message-sources">
          <button 
            className="sources-toggle"
            onClick={toggleSources}
          >
            {showSources ? 'Hide Sources' : 'Show Sources'} ({message.sources.length})
          </button>
          
          {showSources && (
            <div className="sources-list">
              <h4>Sources:</h4>
              <ul>
                {message.sources.map((source, index) => (
                  <li key={index}>
                    <strong>{source.ticker} ({source.year})</strong> - {source.document_type}
                    {source.section && <span> - {source.section}</span>}
                    <div className="source-score">
                      Relevance: {(source.similarity_score * 100).toFixed(1)}%
                    </div>
                    {source.url && (
                      <a 
                        href={source.url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="source-link"
                      >
                        View Source
                      </a>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      <style jsx>{`
        .chat-message {
          padding: 16px;
          border-radius: 8px;
          max-width: 80%;
          width: fit-content;
          margin-bottom: 12px;
        }
        
        .chat-message.user {
          background-color: #e6f7ff;
          border: 1px solid #91d5ff;
          align-self: flex-end;
          margin-left: auto;
        }
        
        .chat-message.assistant {
          background-color: #f6f6f6;
          border: 1px solid #e0e0e0;
          align-self: flex-start;
        }
        
        .message-header {
          font-weight: bold;
          margin-bottom: 8px;
        }
        
        .message-role {
          font-size: 0.9em;
        }
        
        .message-content {
          white-space: pre-wrap;
          line-height: 1.5;
        }
        
        .message-sources {
          margin-top: 12px;
          font-size: 0.9em;
        }
        
        .sources-toggle {
          background: none;
          border: none;
          color: #1890ff;
          cursor: pointer;
          padding: 0;
          text-decoration: underline;
        }
        
        .sources-list {
          margin-top: 8px;
          padding: 8px;
          background-color: #fafafa;
          border: 1px solid #f0f0f0;
          border-radius: 4px;
        }
        
        .sources-list h4 {
          margin-top: 0;
          margin-bottom: 8px;
        }
        
        .sources-list ul {
          margin: 0;
          padding-left: 16px;
        }
        
        .sources-list li {
          margin-bottom: 8px;
        }
        
        .source-score {
          font-size: 0.85em;
          color: #7b7b7b;
          margin: 4px 0;
        }
        
        .source-link {
          display: inline-block;
          color: #1890ff;
          margin-top: 4px;
          text-decoration: none;
        }
        
        .source-link:hover {
          text-decoration: underline;
        }
      `}</style>
    </div>
  );
};

export default ChatMessage;