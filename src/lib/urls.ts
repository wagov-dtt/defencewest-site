/**
 * Create Google Maps URL from coordinates (for map links)
 */
export function googleMapsCoordUrl(
  latitude?: number,
  longitude?: number,
): string | null {
  if (latitude && longitude) {
    return `https://www.google.com/maps?q=${latitude},${longitude}`;
  }
  return null;
}

/**
 * Create Google Maps search URL from address text
 */
export function googleMapsSearchUrl(address?: string): string | null {
  if (address) {
    return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}`;
  }
  return null;
}

/**
 * Normalize website URL to ensure https://
 */
export function normalizeWebsiteUrl(url?: string): string | undefined {
  if (!url) return undefined;
  return url.startsWith("http") ? url : `https://${url}`;
}

/**
 * Display-friendly website (strip protocol and trailing slash)
 */
export function displayWebsite(url?: string): string {
  if (!url) return "";
  return url.replace(/^https?:\/\//, "").replace(/\/$/, "");
}
