/** Rewrite Bilibili CDN URLs to go through the backend image proxy.
 *
 * Bilibili's CDN (i0.hdslb.com, etc.) requires Referer: bilibili.com
 * to serve images. The browser can't set that on <img> tags, so we
 * route these URLs through /api/proxy/image?url=...
 */
export function proxyImage(url: string | null | undefined): string | null {
  if (!url) return null
  // Only proxy known Bilibili CDN domains
  const needsProxy = [
    'i0.hdslb.com', 'i1.hdslb.com', 'i2.hdslb.com',
    'archive.biliimg.com',
  ].some(host => url.includes(host))
  if (!needsProxy) return url
  return `/api/proxy/image?url=${encodeURIComponent(url)}`
}
