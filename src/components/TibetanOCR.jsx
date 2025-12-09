import React, { useRef, useState, useEffect } from 'react';
import { recognizeCharacter } from '../logic/recognition';
import { preprocessCanvas } from '../logic/preprocessing';

/**
 * TibetanOCR Component
 * 
 * A standalone React component for handwritten Tibetan character recognition.
 * Uses pure JavaScript logic for OCR without external ML libraries.
 */
const TibetanOCR = ({ width = 300, height = 300, onRecognize }) => {
  const canvasRef = useRef(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [context, setContext] = useState(null);

  useEffect(() => {
    if (canvasRef.current) {
      const ctx = canvasRef.current.getContext('2d');
      ctx.strokeStyle = '#000000';
      ctx.lineWidth = 3;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      setContext(ctx);
    }
  }, []);

  const startDrawing = (e) => {
    if (!context) return;
    setIsDrawing(true);
    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    context.beginPath();
    context.moveTo(x, y);
  };

  const draw = (e) => {
    if (!isDrawing || !context) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    context.lineTo(x, y);
    context.stroke();
  };

  const stopDrawing = () => {
    if (!context) return;
    setIsDrawing(false);
    context.closePath();
  };

  const clearCanvas = () => {
    if (!context || !canvasRef.current) return;
    context.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
  };

  const handleRecognize = () => {
    if (!canvasRef.current) return;
    
    // Preprocess the canvas data
    const preprocessedData = preprocessCanvas(canvasRef.current);
    
    // Recognize the character
    const result = recognizeCharacter(preprocessedData);
    
    // Call the callback with the result
    if (onRecognize) {
      onRecognize(result);
    }
  };

  return (
    <div style={{ display: 'inline-block', border: '1px solid #ccc', padding: '10px' }}>
      <canvas
        ref={canvasRef}
        width={width}
        height={height}
        onMouseDown={startDrawing}
        onMouseMove={draw}
        onMouseUp={stopDrawing}
        onMouseLeave={stopDrawing}
        style={{ 
          border: '2px solid #333', 
          cursor: 'crosshair',
          display: 'block',
          backgroundColor: '#fff'
        }}
      />
      <div style={{ marginTop: '10px', display: 'flex', gap: '10px' }}>
        <button onClick={handleRecognize} style={{ flex: 1, padding: '8px' }}>
          Recognize
        </button>
        <button onClick={clearCanvas} style={{ flex: 1, padding: '8px' }}>
          Clear
        </button>
      </div>
    </div>
  );
};

export default TibetanOCR;
