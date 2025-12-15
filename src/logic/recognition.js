/**
 * Character recognition logic using template matching
 * 
 * This module implements pure JavaScript recognition algorithms
 * without external ML libraries.
 */

import { getTibetanTemplates } from '../data/templates';

/**
 * Recognize a character from preprocessed data
 * @param {Array<Array<number>>} inputMatrix - Preprocessed character matrix
 * @returns {Object} - Recognition result with character and confidence
 */
export function recognizeCharacter(inputMatrix) {
  const templates = getTibetanTemplates();
  
  let bestMatch = null;
  let bestScore = -Infinity;
  
  // Compare input with each template
  for (const template of templates) {
    const score = calculateSimilarity(inputMatrix, template.matrix);
    
    if (score > bestScore) {
      bestScore = score;
      bestMatch = {
        character: template.character,
        unicode: template.unicode,
        confidence: normalizeConfidence(score)
      };
    }
  }
  
  return bestMatch || {
    character: '?',
    unicode: '?',
    confidence: 0
  };
}

/**
 * Calculate similarity between input and template using template matching
 * @param {Array<Array<number>>} input - Input matrix
 * @param {Array<Array<number>>} template - Template matrix
 * @returns {number} - Similarity score (higher is better)
 */
function calculateSimilarity(input, template) {
  if (input.length !== template.length || input[0].length !== template[0].length) {
    return -Infinity;
  }
  
  let matches = 0;
  let total = 0;
  
  for (let y = 0; y < input.length; y++) {
    for (let x = 0; x < input[y].length; x++) {
      // Count matching pixels
      if (input[y][x] === template[y][x]) {
        matches++;
      }
      total++;
    }
  }
  
  // Calculate similarity percentage
  return matches / total;
}

/**
 * Normalize confidence score to 0-1 range
 * @param {number} rawScore - Raw similarity score
 * @returns {number} - Normalized confidence (0-1)
 */
function normalizeConfidence(rawScore) {
  // Raw score is already between 0 and 1
  return Math.max(0, Math.min(1, rawScore));
}

/**
 * Extract features from the input matrix for enhanced matching
 * This can be extended with more sophisticated feature extraction
 * @param {Array<Array<number>>} matrix - Input matrix
 * @returns {Object} - Feature vector
 */
export function extractFeatures(matrix) {
  return {
    density: calculateDensity(matrix),
    horizontalProjection: calculateHorizontalProjection(matrix),
    verticalProjection: calculateVerticalProjection(matrix),
    aspectRatio: matrix[0].length / matrix.length
  };
}

/**
 * Calculate pixel density
 * @param {Array<Array<number>>} matrix - Input matrix
 * @returns {number} - Density value
 */
function calculateDensity(matrix) {
  let total = 0;
  let filled = 0;
  
  for (let y = 0; y < matrix.length; y++) {
    for (let x = 0; x < matrix[y].length; x++) {
      total++;
      if (matrix[y][x] === 1) {
        filled++;
      }
    }
  }
  
  return filled / total;
}

/**
 * Calculate horizontal projection (sum of pixels in each row)
 * @param {Array<Array<number>>} matrix - Input matrix
 * @returns {Array<number>} - Horizontal projection
 */
function calculateHorizontalProjection(matrix) {
  return matrix.map(row => row.reduce((sum, val) => sum + val, 0));
}

/**
 * Calculate vertical projection (sum of pixels in each column)
 * @param {Array<Array<number>>} matrix - Input matrix
 * @returns {Array<number>} - Vertical projection
 */
function calculateVerticalProjection(matrix) {
  const projection = [];
  for (let x = 0; x < matrix[0].length; x++) {
    let sum = 0;
    for (let y = 0; y < matrix.length; y++) {
      sum += matrix[y][x];
    }
    projection.push(sum);
  }
  return projection;
}
