import React from 'react';
import ReactMarkdown from 'react-markdown';

const ChatMessage = ({ message }) => {
  return (
    <div className={`message ${message.role}`}>
      <ReactMarkdown>{message.content}</ReactMarkdown>
      
      {/* Show sources if available */}
      {message.sources && message.sources.length > 0 && (
        <div className="sources">
          <div className="sources-title">Sources:</div>
          <ul>
            {message.sources.map((source, index) => (
              <li key={index}>{source}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default ChatMessage;
