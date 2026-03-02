# Helium 10 Browser Automation Reference

## H10 X-Ray on Amazon Search Results

When on an Amazon search results page (amazon.com/s?k=...), the H10 Chrome extension injects:

### Summary Bar (coral/orange background)
Located between the search filter bar and results. Contains:
- "Page 1 Keyword Niche Summary for {keyword}"
- Page 1 Products count
- Search Volume
- 30-Day Revenue (blurred for non-Diamond)
- 30-Day Units Sold (blurred for non-Diamond)
- Average BSR (with Min/Max)
- Average Price (with Min/Max)
- Average Rating (with Min/Max)

### Three Action Buttons
- **"Analyze Products"** — opens analysis view
- **"Top Keywords"** — shows keyword data
- **"Download ASINs"** — opens ASIN Grabber modal

### ASIN Grabber Modal
- Shows all products in a table: Product Details, Brand, Price, BSR, Ratings, Review Count
- Top bar: Average BSR, Average Price, Average Reviews
- "Export" dropdown → "...as a CSV file" or "...as a XLSX file"
- CSV auto-downloads as `asinGrabber{date}.csv`
- Contains 100-154 products per search

### Per-Product Cards (in search results)
Each product shows an H10 overlay card with:
- ASIN (with copy button)
- BSR (category + subcategory rank)
- Variations count, Sellers count, Fulfillment type (FBA/FBM/AMZ)
- "Load 30-day Sales Data" button
- "SP" badge = Sponsored Product
- "ABA Most Clicked #N" badge (if applicable)

## H10 X-Ray on Product Detail Page

When on an Amazon product page (amazon.com/dp/ASIN), H10 injects:

### Product Summary Bar (at top of product info area)
Contains:
- BSR: "Health & Hous... #21,369" with trend chart icon
- Subcategory BSR: "Hand Sanitizers #92"
- 30-Day Revenue: "$17,612.59" with trend chart
- Unit Sales: "1,101"
- Current Rating: "4.7 (443)"
- Listing Health Score: "10" (with "Analyze LHS" link)
- Top Keywords: top 2 keywords shown, "See All Keywords" link
- All Marketplaces: country flags

### "Show Full Details" Expander
Additional data when expanded (if not already visible)

### Bottom Toolbar
H10 tools bar at bottom of page:
- Inventory Levels | Xray | Keywords | Listing Builder | Profitability Calculator | eBay Price Checker

## Amazon Page Data Extraction

### From Product Page (native Amazon)
- **Title**: In `#productTitle` or main heading
- **Brand**: "Visit the {Brand} Store" link
- **Price**: In price display area
- **Rating**: Stars display + "(N)" review count
- **BSR**: In "Product information" / "Best Sellers Rank" row
- **Monthly Bought**: "X+ bought in past month" badge
- **Fulfillment**: "Ships from" and "Sold by" section in buy box
- **Images**: Count thumbnail images on left side
- **A+ Content**: Scroll to "Product description" section, if rich HTML = A+ Content
- **Video**: Check for video thumbnails in image gallery
- **Bullet Points**: In feature bullets section

## Key DOM Patterns

### H10 Product Summary (may vary by extension version)
The H10 summary typically appears as a banner/card with:
- Text content readable via `read_page` tool
- Revenue and sales figures visible as text
- BSR shows category hierarchy

### Navigation Flow
1. Navigate to URL
2. Wait 3-5 seconds for H10 extension to inject data
3. Use `read_page` or `find` to locate H10 elements
4. Extract text data from H10 elements
5. Also read native Amazon page elements

### Rate Limiting
- Wait 3-5 seconds between product page navigations
- Amazon may show CAPTCHA if too many requests
- If CAPTCHA appears, pause and alert user
