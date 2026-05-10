/**
 * Loading message utilities
 *
 * getContextualStatus - Returns rotating status messages based on query type
 * (e.g., "Querying store data..." for store-related questions).
 * Used during API calls to give contextual loading feedback.
 */

export const getContextualStatus = (query: string): string[] => {
  const lowerQuery = query.toLowerCase();

  if (lowerQuery.includes('competitor') || lowerQuery.includes('market') || lowerQuery.includes('benchmark')) {
    return [
      'Searching market data...',
      'Pulling competitor financials...',
      'Analyzing industry benchmarks...',
      'Compiling insights...'
    ];
  }

  if (lowerQuery.includes('store') || lowerQuery.includes('revenue') || lowerQuery.includes('region')) {
    return [
      'Querying store data...',
      'Calculating revenue metrics...',
      'Analyzing performance...',
      'Preparing insights...'
    ];
  }

  if (lowerQuery.includes('product') || lowerQuery.includes('popular') || lowerQuery.includes('selling')) {
    return [
      'Analyzing product data...',
      'Calculating sales metrics...',
      'Ranking by performance...',
      'Preparing results...'
    ];
  }

  if (lowerQuery.includes('customer') || lowerQuery.includes('segment') || lowerQuery.includes('lifetime')) {
    return [
      'Analyzing customer data...',
      'Calculating behavior metrics...',
      'Segmenting by value...',
      'Preparing insights...'
    ];
  }

  if (lowerQuery.includes('trend') || lowerQuery.includes('month') || lowerQuery.includes('year')) {
    return [
      'Analyzing time series...',
      'Calculating trends...',
      'Identifying patterns...',
      'Preparing analysis...'
    ];
  }

  return [
    'Understanding your question...',
    'Analyzing data models...',
    'Running query...',
    'Preparing response...'
  ];
};
