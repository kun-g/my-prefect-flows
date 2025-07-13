# RSS Content Enhancement Guide

This guide explains the new RSS content extraction and "Read More..." link features implemented for the RSS feed generation system.

## What's New

### 🔗 Read More Links
Every RSS item now includes a "Read More..." link that directs readers to the original article on your website. This helps drive traffic back to your site while providing content previews in RSS readers.

### 📄 Content Extraction
Instead of just using meta descriptions, the system can now extract actual content from article pages to provide richer RSS feeds with meaningful excerpts.

### 🎨 HTML Support
RSS descriptions now properly support HTML formatting with CDATA sections, allowing for rich content display in modern RSS readers.

## Configuration

### Enabling Content Extraction

To enable content extraction for a specific site, update your `deployments/sites_rss_config.yaml`:

```yaml
sites:
  example_site:
    enabled: true
    sitemap_url: "https://example.com/sitemap.xml"
    options:
      fetch_titles: true
      extract_content: true    # Enable content extraction
      content_length: 500      # Extract up to 500 characters
    # ... other config
```

### Configuration Options

- `extract_content`: Set to `true` to enable content extraction (default: `false`)
- `content_length`: Maximum number of characters to extract (default: `500`)
- `fetch_titles`: Whether to fetch page titles (existing feature)

## How It Works

### Content Extraction Process

1. **Page Fetching**: Downloads the HTML content from each URL
2. **Content Detection**: Identifies main content areas using semantic selectors:
   - `<article>` elements
   - `[role="main"]` 
   - `.content`, `.main-content`, `.post-content` classes
   - Falls back to `<main>` or `<body>`
3. **Content Filtering**: Removes unwanted elements:
   - Navigation, headers, footers
   - Sidebars and advertisements  
   - Scripts and styles
4. **Text Extraction**: Extracts paragraph content up to the specified length
5. **Link Addition**: Appends "Read More..." link to original URL

### Fallback Behavior

If content extraction fails or no suitable content is found:
- Falls back to meta description
- If no meta description exists, creates a simple "Read More..." link
- Ensures every RSS item has some description content

## Examples

### Before (Meta Description Only)
```xml
<description>Brief meta description of the article.</description>
```

### After (With Content Extraction)
```xml
<description><![CDATA[
<p>This article discusses the importance of RSS feeds in modern content distribution. RSS provides a standardized way for users to subscribe to website updates and receive notifications when new content is published.</p>

<p>The format has evolved over the years to support richer content, including HTML formatting and multimedia elements...</p>

<p><a href="https://example.com/article">Read More...</a></p>
]]></description>
```

## Benefits

### For Content Creators
- ✅ Drives traffic back to original website
- ✅ Provides content previews without giving away full articles
- ✅ Maintains SEO value of original content
- ✅ Respects copyright while improving RSS experience

### For RSS Readers
- ✅ More informative content previews
- ✅ Better decision-making about which articles to read
- ✅ Improved reading experience in RSS clients
- ✅ Clear path to full articles

## Backward Compatibility

The new features are fully backward compatible:
- Sites with `extract_content: false` work exactly as before
- Existing RSS feeds continue to function normally
- No breaking changes to RSS structure or deployment process

## Best Practices

### Content Length
- **News sites**: 200-300 characters for quick scanning
- **Blog posts**: 400-600 characters for meaningful previews  
- **Technical articles**: 500-800 characters for context

### Selective Enabling
Start by enabling content extraction for a few high-priority sites to test the feature before rolling out broadly.

### Monitoring
Monitor RSS feed generation logs to ensure content extraction is working properly and adjust `content_length` as needed.

## Troubleshooting

### Common Issues

**Content extraction fails**: 
- Check if the website blocks automated requests
- Verify the site structure uses semantic HTML
- Consider adjusting the content selectors

**Content quality is poor**:
- Increase `content_length` for more context
- Check if the site has unusual HTML structure
- The system will fall back to meta descriptions

**Performance impact**:
- Content extraction requires additional HTTP requests
- Consider reducing `max_items` if feeds take too long to generate
- Monitor server resources during RSS generation

### Log Messages
Look for these log messages to understand what's happening:
- `"获取页面内容: {url}"` - Starting content extraction
- `"内容提取失败: {error}"` - Content extraction failed
- `"创建了 {count} 个 RSS 条目"` - RSS generation completed

## Implementation Details

### Files Modified
- `lib/rss_generator.py`: Enhanced RSS generation with CDATA support
- `flows/sitemap_to_rss.py`: Added content extraction functionality
- `deployments/sites_rss_config.yaml`: Updated configuration examples
- `deployments/deploy_rss_feeds.py`: Added new parameter support

### Dependencies Added
- `beautifulsoup4`: For HTML parsing and content extraction

This enhancement makes RSS feeds more valuable for both content creators and readers while maintaining the simplicity and reliability of the existing system.