/**
 * Translate flexibility level from English to Hebrew
 * @param {string} flexibility - Flexibility level: 'very_flexible', 'flexible', or 'exact'
 * @returns {string} Hebrew translation
 */
export function translateFlexibility(flexibility) {
  switch (flexibility) {
    case 'exact':
      return 'מדויק';
    case 'flexible':
      return 'גמיש';
    case 'very_flexible':
      return 'גמיש מאוד';
    default:
      return 'גמיש'; // Default fallback
  }
}

/**
 * Get color classes for flexibility badge
 * @param {string} flexibility - Flexibility level
 * @returns {string} Tailwind CSS classes
 */
export function getFlexibilityColorClasses(flexibility) {
  switch (flexibility) {
    case 'exact':
      return 'bg-orange-100 text-orange-700';
    case 'flexible':
      return 'bg-green-100 text-green-700';
    case 'very_flexible':
      return 'bg-blue-100 text-blue-700';
    default:
      return 'bg-green-100 text-green-700'; // Default fallback
  }
}



