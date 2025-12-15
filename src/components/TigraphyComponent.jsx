import React from 'react'

/**
 * Example Tigraphy component
 * This is a starter component that can be customized based on your needs
 */
const TigraphyComponent = ({ title = 'Tigraphy', message = 'Welcome to Tigraphy!' }) => {
  return (
    <div style={{
      padding: '20px',
      border: '2px solid #4A90E2',
      borderRadius: '8px',
      backgroundColor: '#F0F8FF',
      fontFamily: 'Arial, sans-serif'
    }}>
      <h2 style={{ color: '#4A90E2', marginTop: 0 }}>{title}</h2>
      <p style={{ color: '#333' }}>{message}</p>
    </div>
  )
}

export default TigraphyComponent
