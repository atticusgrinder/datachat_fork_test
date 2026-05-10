/**
 * Date/time formatting utilities
 *
 * formatThreadTime - Relative timestamps for thread list ("2h ago", "Nov 18")
 */

export function formatThreadTime(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  // Less than 1 minute
  if (diffMins < 1) {
    return 'Just now';
  }

  // Less than 1 hour
  if (diffMins < 60) {
    return `${diffMins}m ago`;
  }

  // Less than 24 hours
  if (diffHours < 24) {
    return `${diffHours}h ago`;
  }

  // Less than 7 days
  if (diffDays < 7) {
    return `${diffDays}d ago`;
  }

  // Less than 30 days
  if (diffDays < 30) {
    const weeks = Math.floor(diffDays / 7);
    return `${weeks}w ago`;
  }

  // Format as date
  const month = date.toLocaleDateString('en-US', { month: 'short' });
  const day = date.getDate();

  // Same year - just show month and day
  if (date.getFullYear() === now.getFullYear()) {
    return `${month} ${day}`;
  }

  // Different year - show month, day, and year
  return `${month} ${day}, ${date.getFullYear()}`;
}
