# Tigraphy

A standalone React component library designed for easy integration into any React/Vite application.

## Features

- 📦 Built with Vite in Library Mode
- ⚛️ React component ready for use
- 🎯 Clear separation of concerns (components, logic, data)
- 📤 ESM and UMD bundle support
- 🚀 Easy to integrate into any React project

## Installation

```bash
npm install tigraphy
```

## Usage

### Basic Usage

```jsx
import TigraphyComponent from 'tigraphy'

function App() {
  return (
    <TigraphyComponent 
      title="My Custom Title"
      message="Hello from Tigraphy!"
    />
  )
}
```

### Named Imports

```jsx
import { TigraphyComponent, formatTitle, generateId, defaultConfig } from 'tigraphy'

function App() {
  const formattedTitle = formatTitle('hello world')
  const uniqueId = generateId()
  
  return (
    <TigraphyComponent 
      title={formattedTitle}
      message={`ID: ${uniqueId}`}
    />
  )
}
```

## Development

### Setup

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build the library
npm run build
```

### Project Structure

```
tigraphy/
├── src/
│   ├── components/     # React components
│   ├── logic/          # Business logic and utilities
│   ├── data/           # Data management and constants
│   └── index.jsx       # Main entry point
├── dist/               # Build output (ESM and UMD)
├── package.json
└── vite.config.js      # Vite library configuration
```

## Building for Production

The library is built using Vite in library mode, generating both ESM and UMD bundles:

```bash
npm run build
```

This creates:
- `dist/tigraphy.js` - ESM bundle
- `dist/tigraphy.umd.cjs` - UMD bundle

## License

MIT