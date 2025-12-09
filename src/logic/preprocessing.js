/**
 * Preprocessing utilities for canvas data
 * 
 * These functions prepare the handwritten input for recognition
 * by performing geometric transformations and normalization.
 */

/**
 * Preprocess canvas data for recognition
 * @param {HTMLCanvasElement} canvas - The canvas element containing the drawing
 * @returns {Array<Array<number>>} - Normalized 2D matrix representation
 */
export function preprocessCanvas(canvas) {
  const ctx = canvas.getContext('2d');
  const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
  
  // Convert to grayscale matrix
  const matrix = convertToMatrix(imageData, canvas.width, canvas.height);
  
  // Find bounding box of the drawing
  const boundingBox = findBoundingBox(matrix);
  
  // Crop to bounding box
  const cropped = cropMatrix(matrix, boundingBox);
  
  // Normalize to fixed size (e.g., 28x28)
  const normalized = normalizeSize(cropped, 28, 28);
  
  return normalized;
}

/**
 * Convert ImageData to a binary matrix
 * @param {ImageData} imageData - Canvas image data
 * @param {number} width - Image width
 * @param {number} height - Image height
 * @returns {Array<Array<number>>} - Binary matrix (0 for white, 1 for drawn)
 */
function convertToMatrix(imageData, width, height) {
  const matrix = [];
  const threshold = 128;
  
  for (let y = 0; y < height; y++) {
    const row = [];
    for (let x = 0; x < width; x++) {
      const index = (y * width + x) * 4;
      // Average RGB values for grayscale
      const gray = (imageData.data[index] + imageData.data[index + 1] + imageData.data[index + 2]) / 3;
      // Binary threshold: white (255) = 0, drawn (dark) = 1
      row.push(gray < threshold ? 1 : 0);
    }
    matrix.push(row);
  }
  
  return matrix;
}

/**
 * Find the bounding box of non-zero pixels
 * @param {Array<Array<number>>} matrix - Binary matrix
 * @returns {Object} - {minX, minY, maxX, maxY}
 */
function findBoundingBox(matrix) {
  let minX = matrix[0].length;
  let minY = matrix.length;
  let maxX = 0;
  let maxY = 0;
  let hasContent = false;
  
  for (let y = 0; y < matrix.length; y++) {
    for (let x = 0; x < matrix[y].length; x++) {
      if (matrix[y][x] === 1) {
        minX = Math.min(minX, x);
        minY = Math.min(minY, y);
        maxX = Math.max(maxX, x);
        maxY = Math.max(maxY, y);
        hasContent = true;
      }
    }
  }
  
  // If no content found, return full canvas bounds
  if (!hasContent) {
    return { minX: 0, minY: 0, maxX: matrix[0].length - 1, maxY: matrix.length - 1 };
  }
  
  return { minX, minY, maxX, maxY };
}

/**
 * Crop matrix to bounding box
 * @param {Array<Array<number>>} matrix - Binary matrix
 * @param {Object} boundingBox - {minX, minY, maxX, maxY}
 * @returns {Array<Array<number>>} - Cropped matrix
 */
function cropMatrix(matrix, { minX, minY, maxX, maxY }) {
  const cropped = [];
  
  for (let y = minY; y <= maxY; y++) {
    const row = [];
    for (let x = minX; x <= maxX; x++) {
      row.push(matrix[y][x]);
    }
    cropped.push(row);
  }
  
  return cropped;
}

/**
 * Normalize matrix to target size using nearest neighbor interpolation
 * @param {Array<Array<number>>} matrix - Input matrix
 * @param {number} targetWidth - Target width
 * @param {number} targetHeight - Target height
 * @returns {Array<Array<number>>} - Normalized matrix
 */
function normalizeSize(matrix, targetWidth, targetHeight) {
  const sourceHeight = matrix.length;
  const sourceWidth = matrix[0].length;
  const normalized = [];
  
  for (let y = 0; y < targetHeight; y++) {
    const row = [];
    const sourceY = Math.min(Math.floor((y / targetHeight) * sourceHeight), sourceHeight - 1);
    
    for (let x = 0; x < targetWidth; x++) {
      const sourceX = Math.min(Math.floor((x / targetWidth) * sourceWidth), sourceWidth - 1);
      row.push(matrix[sourceY][sourceX]);
    }
    
    normalized.push(row);
  }
  
  return normalized;
}
