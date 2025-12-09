/**
 * Example utility functions for business logic
 * Add your custom logic functions here
 */

/**
 * Format a string to title case
 * @param {string} str - The string to format
 * @returns {string} - The formatted string
 */
export const formatTitle = (str) => {
  if (!str) return ''
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase()
}

/**
 * Generate a unique ID
 * @returns {string} - A unique identifier
 */
export const generateId = () => {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}
