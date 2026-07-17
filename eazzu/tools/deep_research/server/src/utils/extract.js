// Convert raw HTML into clean text + basic metadata. This is intentionally
// conservative — we prefer <article>/<main>, drop nav/footer/script/style,
// and try to pull publication dates from common meta tags.

import * as cheerio from 'cheerio';

const DROP = 'script,style,noscript,iframe,svg,form,nav,footer,aside,header';

export function extractFromHtml(html, url) {
  const $ = cheerio.load(html);

  const title =
    $('meta[property="og:title"]').attr('content')?.trim() ||
    $('title').first().text().trim() ||
    '';

  const description =
    $('meta[property="og:description"]').attr('content')?.trim() ||
    $('meta[name="description"]').attr('content')?.trim() ||
    '';

  const publishedAt =
    $('meta[property="article:published_time"]').attr('content') ||
    $('meta[name="date"]').attr('content') ||
    $('meta[name="pubdate"]').attr('content') ||
    $('time[datetime]').first().attr('datetime') ||
    null;

  $(DROP).remove();

  const container =
    $('article').first().length ? $('article').first() :
    $('main').first().length ? $('main').first() :
    $('body');

  // Collapse whitespace and drop obvious boilerplate lines.
  const rawText = container
    .find('h1,h2,h3,h4,p,li,blockquote')
    .map((_, el) => $(el).text().replace(/\s+/g, ' ').trim())
    .get()
    .filter((line) => line.length > 20)
    .join('\n');

  return {
    url,
    title,
    description,
    publishedAt,
    text: rawText.slice(0, 20000), // hard cap so LLM context stays sane
    wordCount: rawText.split(/\s+/).length,
  };
}
