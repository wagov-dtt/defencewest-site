/**
 * Create Google Maps URL from coordinates or address
 */
export function googleMapsUrl(
  latitude?: number,
  longitude?: number,
  address?: string,
): string | null {
  if (latitude && longitude) {
    return `https://www.google.com/maps?q=${latitude},${longitude}`;
  }
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
