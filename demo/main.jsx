import React, { useState } from 'react';
import ReactDOM from 'react-dom/client';
import TibetanOCR from '../src/components/TibetanOCR.jsx';

function App() {
  const [result, setResult] = useState(null);

  const handleRecognize = (recognitionResult) => {
    console.log('Recognition result:', recognitionResult);
    setResult(recognitionResult);
  };

  return (
    <div style={{ 
      fontFamily: 'Arial, sans-serif', 
      maxWidth: '600px', 
      margin: '0 auto', 
      padding: '20px' 
    }}>
      <h1>Tigraphy - Tibetan OCR Demo</h1>
      <p>Draw a Tibetan character in the canvas below and click "Recognize" to identify it.</p>
      
      <div style={{ marginTop: '20px', marginBottom: '20px' }}>
        <TibetanOCR 
          width={300} 
          height={300} 
          onRecognize={handleRecognize}
        />
      </div>

      {result && (
        <div style={{ 
          padding: '15px', 
          backgroundColor: '#f0f0f0', 
          borderRadius: '5px',
          marginTop: '20px'
        }}>
          <h3>Recognition Result:</h3>
          <p><strong>Character:</strong> {result.character}</p>
          <p><strong>Unicode:</strong> {result.unicode}</p>
          <p><strong>Confidence:</strong> {(result.confidence * 100).toFixed(2)}%</p>
        </div>
      )}

      <div style={{ marginTop: '30px', fontSize: '14px', color: '#666' }}>
        <h3>About</h3>
        <p>
          This is a standalone React component for handwritten Tibetan character recognition.
          It uses pure JavaScript logic with template matching algorithms, no external ML libraries.
        </p>
        <h4>Architecture:</h4>
        <ul>
          <li><code>src/components/</code> - React UI components (Canvas element)</li>
          <li><code>src/logic/</code> - Recognition algorithms and preprocessing</li>
          <li><code>src/data/</code> - Tibetan character templates</li>
        </ul>
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
