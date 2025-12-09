/**
 * Tibetan character templates in matrix format
 * 
 * Each template represents a Tibetan character as a 28x28 binary matrix
 * where 0 = background (white) and 1 = character stroke (black)
 */

/**
 * Get all Tibetan character templates
 * @returns {Array<Object>} - Array of template objects
 */
export function getTibetanTemplates() {
  return [
    {
      character: 'ka',
      unicode: 'ཀ',
      description: 'Tibetan letter KA',
      matrix: createSampleMatrix(28, 28, 'ka')
    },
    {
      character: 'kha',
      unicode: 'ཁ',
      description: 'Tibetan letter KHA',
      matrix: createSampleMatrix(28, 28, 'kha')
    },
    {
      character: 'ga',
      unicode: 'ག',
      description: 'Tibetan letter GA',
      matrix: createSampleMatrix(28, 28, 'ga')
    },
    {
      character: 'nga',
      unicode: 'ང',
      description: 'Tibetan letter NGA',
      matrix: createSampleMatrix(28, 28, 'nga')
    },
    {
      character: 'ca',
      unicode: 'ཅ',
      description: 'Tibetan letter CA',
      matrix: createSampleMatrix(28, 28, 'ca')
    }
  ];
}

/**
 * Create a sample template matrix
 * This is a placeholder - in production, these would be actual
 * digitized samples of handwritten Tibetan characters
 * 
 * @param {number} width - Matrix width
 * @param {number} height - Matrix height
 * @param {string} seed - Seed for pattern generation
 * @returns {Array<Array<number>>} - Binary matrix
 */
function createSampleMatrix(width, height, seed) {
  const matrix = [];
  
  // Create empty matrix
  for (let y = 0; y < height; y++) {
    const row = [];
    for (let x = 0; x < width; x++) {
      row.push(0);
    }
    matrix.push(row);
  }
  
  // Create a simple placeholder pattern based on seed
  // This should be replaced with actual Tibetan character templates
  const centerX = Math.floor(width / 2);
  const centerY = Math.floor(height / 2);
  const hashCode = seed.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  
  // Draw a simple pattern as placeholder
  for (let y = 5; y < height - 5; y++) {
    for (let x = 5; x < width - 5; x++) {
      const dx = x - centerX;
      const dy = y - centerY;
      const distance = Math.sqrt(dx * dx + dy * dy);
      
      // Create different patterns based on hashCode
      if (hashCode % 3 === 0) {
        // Vertical line pattern
        if (Math.abs(dx) < 3 || (Math.abs(dx) < 8 && y > centerY)) {
          matrix[y][x] = 1;
        }
      } else if (hashCode % 3 === 1) {
        // Circular pattern
        if (distance > 5 && distance < 12) {
          matrix[y][x] = 1;
        }
      } else {
        // Mixed pattern
        if (Math.abs(dx) < 3 || (y === centerY && Math.abs(dx) < 10)) {
          matrix[y][x] = 1;
        }
      }
    }
  }
  
  return matrix;
}

/**
 * Add a new template to the collection
 * This function can be used to programmatically add templates
 * 
 * @param {string} character - Character name
 * @param {string} unicode - Unicode representation
 * @param {Array<Array<number>>} matrix - Character matrix
 * @returns {Object} - Template object
 */
export function createTemplate(character, unicode, matrix) {
  return {
    character,
    unicode,
    matrix
  };
}

/**
 * Load templates from external source (placeholder)
 * In a production system, this could load from a JSON file or database
 * 
 * @returns {Promise<Array<Object>>} - Promise resolving to templates array
 */
export async function loadTemplatesFromSource() {
  // Placeholder for loading templates from external source
  return Promise.resolve(getTibetanTemplates());
}
