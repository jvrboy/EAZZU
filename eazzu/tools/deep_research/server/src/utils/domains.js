// Domain-authority scoring. Higher = more trustworthy. Used both to rank
// sources and to gate claim acceptance during verification.

const CURATED = {
  // Encyclopedic
  'wikipedia.org': 0.85,
  'britannica.com': 0.8,
  // Scientific
  'nature.com': 0.95,
  'science.org': 0.95,
  'sciencedirect.com': 0.9,
  'arxiv.org': 0.85,
  'pubmed.ncbi.nlm.nih.gov': 0.95,
  'ncbi.nlm.nih.gov': 0.9,
  'nih.gov': 0.95,
  'crossref.org': 0.85,
  'doi.org': 0.85,
  'plos.org': 0.85,
  'ieee.org': 0.9,
  'acm.org': 0.9,
  // News (mainstream)
  'reuters.com': 0.9,
  'apnews.com': 0.9,
  'bbc.com': 0.85,
  'bbc.co.uk': 0.85,
  'nytimes.com': 0.8,
  'washingtonpost.com': 0.8,
  'theguardian.com': 0.8,
  'economist.com': 0.85,
  'ft.com': 0.85,
  'bloomberg.com': 0.8,
  'wsj.com': 0.8,
  // Tech / industry
  'arstechnica.com': 0.75,
  'wired.com': 0.7,
  'technologyreview.com': 0.8,
  // Government
  'nasa.gov': 0.95,
  'cdc.gov': 0.95,
  'who.int': 0.9,
  'europa.eu': 0.85,
};

export function hostOf(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, '').toLowerCase();
  } catch {
    return '';
  }
}

export function domainAuthority(url) {
  const host = hostOf(url);
  if (!host) return 0.3;

  // Exact / suffix match against curated list
  for (const [d, score] of Object.entries(CURATED)) {
    if (host === d || host.endsWith('.' + d)) return score;
  }

  // TLD heuristics
  if (host.endsWith('.gov') || host.endsWith('.mil')) return 0.9;
  if (host.endsWith('.edu')) return 0.8;
  if (host.endsWith('.ac.uk') || host.endsWith('.edu.au')) return 0.8;
  if (host.endsWith('.org')) return 0.55;

  return 0.4;
}

export function recencyScore(publishedAt) {
  if (!publishedAt) return 0.5;
  const t = Date.parse(publishedAt);
  if (Number.isNaN(t)) return 0.5;
  const years = (Date.now() - t) / (365 * 24 * 3600 * 1000);
  if (years < 0) return 0.9;
  if (years < 1) return 1.0;
  if (years < 3) return 0.85;
  if (years < 5) return 0.7;
  if (years < 10) return 0.5;
  return 0.3;
}

export function combinedSourceScore(url, publishedAt) {
  const da = domainAuthority(url);
  const rs = recencyScore(publishedAt);
  return +(0.7 * da + 0.3 * rs).toFixed(3);
}
