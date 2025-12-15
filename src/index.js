/**
 * Tigraphy - Tibetan Handwriting Recognition Library
 * 
 * Main entry point for the library
 */

import TibetanOCR from './components/TibetanOCR.jsx';

// Export the main component
export default TibetanOCR;

// Export named exports for flexibility
export { TibetanOCR };

// Export utility functions from logic modules
export { recognizeCharacter, extractFeatures } from './logic/recognition';
export { preprocessCanvas } from './logic/preprocessing';

// Export template utilities
export { getTibetanTemplates, createTemplate, loadTemplatesFromSource } from './data/templates';
