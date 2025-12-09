// Main entry point for the Tigraphy library
import TigraphyComponent from './components/TigraphyComponent.jsx'
import { formatTitle, generateId } from './logic/utils.js'
import { defaultConfig, sampleData } from './data/constants.js'

// Export the main component as default
export default TigraphyComponent

// Export named exports for utilities and data
export {
  TigraphyComponent,
  formatTitle,
  generateId,
  defaultConfig,
  sampleData
}
