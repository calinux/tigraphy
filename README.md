# Tigraphy

A standalone React component for handwritten Tibetan character recognition (OCR) using pure JavaScript logic without external Machine Learning libraries.

![Tigraphy Demo](https://github.com/user-attachments/assets/cd830ee1-c3d8-485f-8976-60c213de054f)

## Features

- 🎨 **Interactive Canvas** - Draw Tibetan characters with mouse/touch input
- 🔍 **Pure JavaScript OCR** - Recognition using template matching algorithms (no TensorFlow.js or external ML libraries)
- 📦 **NPM Package Ready** - Compiled as ESM and UMD bundles for easy integration
- ⚡ **React + Vite** - Modern tooling with fast development and optimized builds
- 🏗️ **Modular Architecture** - Clear separation between UI, logic, and data layers

## Installation

```bash
npm install tigraphy
```

## Usage

### Basic Example

```jsx
import React, { useState } from 'react';
import TibetanOCR from 'tigraphy';

function App() {
  const [result, setResult] = useState(null);

  const handleRecognize = (recognitionResult) => {
    console.log('Recognized:', recognitionResult);
    setResult(recognitionResult);
  };

  return (
    <div>
      <h1>Tibetan OCR Demo</h1>
      <TibetanOCR 
        width={300} 
        height={300} 
        onRecognize={handleRecognize}
      />
      
      {result && (
        <div>
          <p>Character: {result.character}</p>
          <p>Unicode: {result.unicode}</p>
          <p>Confidence: {(result.confidence * 100).toFixed(2)}%</p>
        </div>
      )}
    </div>
  );
}

export default App;
```

### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `width` | number | 300 | Canvas width in pixels |
| `height` | number | 300 | Canvas height in pixels |
| `onRecognize` | function | - | Callback function called with recognition result |

### Recognition Result Object

```javascript
{
  character: 'ka',      // Character name
  unicode: 'ཀ',         // Unicode representation
  confidence: 0.85      // Confidence score (0-1)
}
```

## Architecture

The project follows a clean, modular architecture:

```
tigraphy/
├── src/
│   ├── components/       # React UI components
│   │   └── TibetanOCR.jsx   # Main canvas component
│   ├── logic/           # Pure JavaScript recognition algorithms
│   │   ├── recognition.js    # Template matching logic
│   │   └── preprocessing.js  # Image preprocessing utilities
│   ├── data/            # Tibetan character templates
│   │   └── templates.js      # Character templates in matrix format
│   └── index.js         # Main entry point
├── demo/                # Demo application
│   └── main.jsx
├── vite.config.js       # Vite library mode configuration
└── package.json         # NPM package configuration
```

### Key Components

- **`src/components/TibetanOCR.jsx`** - React component with canvas drawing functionality
- **`src/logic/preprocessing.js`** - Geometric preprocessing and normalization
- **`src/logic/recognition.js`** - Template matching and character recognition
- **`src/data/templates.js`** - Tibetan character templates stored as binary matrices

## Development

### Prerequisites

- Node.js >= 16
- npm or yarn

### Setup

```bash
# Clone the repository
git clone https://github.com/calinux/tigraphy.git
cd tigraphy

# Install dependencies
npm install

# Start development server
npm run dev

# Build the library
npm run build
```

### Build Output

The build process generates two bundle formats in the `dist/` directory:

- **ESM** (ES Module): `dist/tigraphy.js` - For modern bundlers
- **UMD** (Universal Module Definition): `dist/tigraphy.umd.cjs` - For older environments

## How It Works

### 1. Canvas Input
The user draws a Tibetan character on the HTML5 canvas element.

### 2. Preprocessing
The canvas data is converted to a normalized binary matrix:
- Convert to grayscale
- Find bounding box
- Crop to content
- Normalize to 28x28 pixels

### 3. Template Matching
The preprocessed matrix is compared against stored templates:
- Calculate pixel-by-pixel similarity
- Find the best matching template
- Return character with confidence score

### 4. Result Display
The recognized character, its Unicode representation, and confidence score are returned.

![Recognition Result](https://github.com/user-attachments/assets/aac5eadd-d13a-4717-bc0f-9242fe285341)

## API Reference

### Exported Functions

```javascript
import { 
  TibetanOCR,              // Main component (default export)
  recognizeCharacter,       // Recognition function
  extractFeatures,          // Feature extraction
  preprocessCanvas,         // Preprocessing utilities
  getTibetanTemplates,      // Get all templates
  createTemplate,           // Create new template
  loadTemplatesFromSource   // Load templates externally
} from 'tigraphy';
```

## Contributing

Contributions are welcome! Areas for improvement:

- Add more Tibetan character templates
- Implement advanced feature extraction algorithms
- Improve recognition accuracy
- Add support for character combinations
- Optimize performance

## License

MIT

## Acknowledgments

This project implements pure JavaScript OCR algorithms for Tibetan script recognition, designed for educational purposes and easy integration into web applications.