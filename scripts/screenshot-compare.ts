/**
 * Screenshot comparison script using Playwright
 * Compares old site (deed.wa.gov.au) with new rebuilt site (localhost)
 * 
 * Generates both screenshots AND a text-based report for LLM analysis
 */

import { chromium, Browser, Page } from 'playwright';
import * as fs from 'fs';
import * as path from 'path';

const OLD_SITE = 'https://www.deed.wa.gov.au/wa-defence-industry-and-science-capability-directory';
const NEW_SITE = 'http://localhost:4321';

const SCREENSHOT_DIR = path.join(process.cwd(), 'screenshots');

// Use smaller viewport to keep file sizes down
const VIEWPORT = { width: 1280, height: 900 };

interface PageAnalysis {
  url: string;
  title: string;
  headerText: string;
  navLinks: string[];
  mainHeadings: string[];
  buttonCount: number;
  imageCount: number;
  formElements: { inputs: number; selects: number; buttons: number };
  cardCount: number;
  badges: string[];
  colors: { background: string; headerBg: string };
}

interface Screenshot {
  name: string;
  description: string;
  oldPath: string;
  newPath: string;
  oldAnalysis?: PageAnalysis;
  newAnalysis?: PageAnalysis;
}

async function ensureDir(dir: string) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

async function analyzePage(page: Page): Promise<PageAnalysis> {
  return await page.evaluate(() => {
    const headerEl = document.querySelector('header') || document.querySelector('[class*="header"]');
    const navLinks = Array.from(document.querySelectorAll('nav a, header a')).map(el => el.textContent?.trim() || '');
    const headings = Array.from(document.querySelectorAll('h1, h2')).map(el => el.textContent?.trim() || '').slice(0, 10);
    const badges = Array.from(document.querySelectorAll('[class*="badge"], [class*="tag"]'))
      .map(el => el.textContent?.trim() || '')
      .filter(t => t.length > 0 && t.length < 20)
      .slice(0, 10);

    return {
      url: window.location.href,
      title: document.title,
      headerText: headerEl?.textContent?.trim()?.slice(0, 200) || '',
      navLinks: navLinks,
      mainHeadings: headings,
      buttonCount: document.querySelectorAll('button, [type="button"]').length,
      imageCount: document.querySelectorAll('img').length,
      formElements: {
        inputs: document.querySelectorAll('input').length,
        selects: document.querySelectorAll('select').length,
        buttons: document.querySelectorAll('button').length,
      },
      cardCount: document.querySelectorAll('[class*="card"], [class*="tile"], .result-tile, article').length,
      badges: badges,
      colors: {
        background: '',
        headerBg: '',
      }
    };
  });
}

async function takeScreenshot(page: Page, name: string, site: 'old' | 'new'): Promise<string> {
  const filename = `${name}-${site}.png`;
  const filepath = path.join(SCREENSHOT_DIR, filename);
  await page.screenshot({ path: filepath, fullPage: false });
  console.log(`  Saved: ${filename}`);
  return filepath;
}

async function captureOldSite(browser: Browser): Promise<Screenshot[]> {
  console.log('\n=== Capturing OLD site (deed.wa.gov.au) ===\n');
  const screenshots: Screenshot[] = [];
  const context = await browser.newContext({ viewport: VIEWPORT });
  const page = await context.newPage();

  try {
    // 1. Landing page
    console.log('1. Landing page...');
    await page.goto(OLD_SITE, { waitUntil: 'networkidle', timeout: 60000 });
    const landingOld = await takeScreenshot(page, '01-landing', 'old');
    const landingAnalysis = await analyzePage(page);
    screenshots.push({ 
      name: '01-landing', 
      description: 'Landing page before opening directory',
      oldPath: landingOld, 
      newPath: '',
      oldAnalysis: landingAnalysis
    });

    // 2. Open the directory modal
    console.log('2. Opening directory modal...');
    await page.click('#activeModal');
    await page.waitForSelector('.modal-container', { state: 'visible', timeout: 10000 });
    await page.waitForTimeout(2000);
    const directoryOld = await takeScreenshot(page, '02-directory', 'old');
    const directoryAnalysis = await analyzePage(page);
    screenshots.push({ 
      name: '02-directory', 
      description: 'Directory view with filters and company cards',
      oldPath: directoryOld, 
      newPath: '',
      oldAnalysis: directoryAnalysis
    });

    // 3. Scroll to show cards better
    console.log('3. Company cards...');
    await page.evaluate(() => {
      const results = document.querySelector('.result-tiles-wrapper');
      if (results) results.scrollIntoView();
    });
    await page.waitForTimeout(500);
    const cardsOld = await takeScreenshot(page, '03-cards', 'old');
    screenshots.push({ 
      name: '03-cards', 
      description: 'Company card grid view',
      oldPath: cardsOld, 
      newPath: '',
      oldAnalysis: await analyzePage(page)
    });

    // 4. Click first company for detail view
    console.log('4. Company detail (in modal)...');
    const companyCard = page.locator('.result-tile').first();
    if (await companyCard.isVisible()) {
      await companyCard.click();
      await page.waitForTimeout(2000);
      const detailOld = await takeScreenshot(page, '04-detail', 'old');
      screenshots.push({ 
        name: '04-detail', 
        description: 'Company detail view',
        oldPath: detailOld, 
        newPath: '',
        oldAnalysis: await analyzePage(page)
      });
    }

  } catch (error) {
    console.error('Error capturing old site:', error);
  }

  await context.close();
  return screenshots;
}

async function captureNewSite(browser: Browser, screenshots: Screenshot[]): Promise<void> {
  console.log('\n=== Capturing NEW site (localhost:4321) ===\n');
  const context = await browser.newContext({ viewport: VIEWPORT });
  const page = await context.newPage();

  try {
    // 1. Landing/Directory page
    console.log('1. Landing/Directory page...');
    await page.goto(NEW_SITE, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(1000);
    const landingNew = await takeScreenshot(page, '01-landing', 'new');
    screenshots[0].newPath = landingNew;
    screenshots[0].newAnalysis = await analyzePage(page);

    // 2. Same as landing for new site (no modal)
    console.log('2. Directory view...');
    const directoryNew = await takeScreenshot(page, '02-directory', 'new');
    screenshots[1].newPath = directoryNew;
    screenshots[1].newAnalysis = await analyzePage(page);

    // 3. Scroll to cards
    console.log('3. Company cards...');
    await page.evaluate(() => {
      const grid = document.querySelector('#company-grid');
      if (grid) grid.scrollIntoView();
    });
    await page.waitForTimeout(500);
    const cardsNew = await takeScreenshot(page, '03-cards', 'new');
    screenshots[2].newPath = cardsNew;
    screenshots[2].newAnalysis = await analyzePage(page);

    // 4. Navigate directly to a company detail page
    console.log('4. Company detail page...');
    await page.goto(`${NEW_SITE}/company/4z-pty.-ltd`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);
    const detailNew = await takeScreenshot(page, '04-detail', 'new');
    if (screenshots[3]) {
      screenshots[3].newPath = detailNew;
      screenshots[3].newAnalysis = await analyzePage(page);
    }

  } catch (error) {
    console.error('Error capturing new site:', error);
  }

  await context.close();
}

function generateTextReport(screenshots: Screenshot[]): string {
  let report = `# Visual Comparison Report
Generated: ${new Date().toISOString()}

## Summary
Comparing old site (deed.wa.gov.au) with new Astro rebuild (localhost:4321)

`;

  for (const s of screenshots) {
    report += `---
## ${s.name}: ${s.description}

### Old Site Analysis
`;
    if (s.oldAnalysis) {
      report += `- URL: ${s.oldAnalysis.url}
- Title: ${s.oldAnalysis.title}
- Images: ${s.oldAnalysis.imageCount}
- Cards/Tiles: ${s.oldAnalysis.cardCount}
- Form elements: ${s.oldAnalysis.formElements.inputs} inputs, ${s.oldAnalysis.formElements.selects} selects
- Headings: ${s.oldAnalysis.mainHeadings.slice(0, 5).join(', ')}
- Badges found: ${s.oldAnalysis.badges.join(', ') || 'none'}
`;
    }

    report += `
### New Site Analysis
`;
    if (s.newAnalysis) {
      report += `- URL: ${s.newAnalysis.url}
- Title: ${s.newAnalysis.title}
- Images: ${s.newAnalysis.imageCount}
- Cards/Tiles: ${s.newAnalysis.cardCount}
- Form elements: ${s.newAnalysis.formElements.inputs} inputs, ${s.newAnalysis.formElements.selects} selects
- Headings: ${s.newAnalysis.mainHeadings.slice(0, 5).join(', ')}
- Badges found: ${s.newAnalysis.badges.join(', ') || 'none'}
`;
    }

    report += `
### Comparison
`;
    if (s.oldAnalysis && s.newAnalysis) {
      const imgDiff = s.newAnalysis.imageCount - s.oldAnalysis.imageCount;
      const cardDiff = s.newAnalysis.cardCount - s.oldAnalysis.cardCount;
      report += `- Image count: ${imgDiff >= 0 ? '+' : ''}${imgDiff} (old: ${s.oldAnalysis.imageCount}, new: ${s.newAnalysis.imageCount})
- Card count: ${cardDiff >= 0 ? '+' : ''}${cardDiff} (old: ${s.oldAnalysis.cardCount}, new: ${s.newAnalysis.cardCount})
`;
    }
    report += '\n';
  }

  report += `---
## Screenshots Generated
`;
  for (const s of screenshots) {
    report += `- ${s.name}-old.png / ${s.name}-new.png
`;
  }

  return report;
}

function generateHtmlReport(screenshots: Screenshot[]): void {
  let html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Visual Comparison Report</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: system-ui, sans-serif; background: #f5f5f5; padding: 20px; }
    h1 { text-align: center; margin-bottom: 30px; color: #017183; }
    .comparison { 
      display: grid; 
      grid-template-columns: 1fr 1fr; 
      gap: 20px; 
      margin-bottom: 40px;
      background: white;
      padding: 20px;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .comparison h3 { grid-column: 1 / -1; border-bottom: 2px solid #017183; padding-bottom: 10px; color: #017183; }
    .screenshot { text-align: center; }
    .screenshot img { max-width: 100%; border: 1px solid #ddd; border-radius: 4px; }
    .screenshot p { margin-top: 10px; font-weight: 600; color: #666; }
  </style>
</head>
<body>
  <h1>WA Defence Directory - Visual Comparison</h1>
`;

  for (const s of screenshots) {
    const oldFile = path.basename(s.oldPath);
    const newFile = s.newPath ? path.basename(s.newPath) : '';
    html += `
  <div class="comparison">
    <h3>${s.name}: ${s.description}</h3>
    <div class="screenshot">
      <img src="${oldFile}" alt="Old site">
      <p>Original (deed.wa.gov.au)</p>
    </div>
    <div class="screenshot">
      ${newFile ? `<img src="${newFile}" alt="New site">` : '<p>Not captured</p>'}
      <p>New (Astro rebuild)</p>
    </div>
  </div>
`;
  }

  html += `</body></html>`;
  fs.writeFileSync(path.join(SCREENSHOT_DIR, 'comparison.html'), html);
}

async function main() {
  console.log('Screenshot Comparison Tool');
  console.log('==========================\n');
  
  await ensureDir(SCREENSHOT_DIR);
  
  const browser = await chromium.launch({ headless: true });
  
  try {
    const screenshots = await captureOldSite(browser);
    
    console.log('\nChecking if new site is running on localhost:4321...');
    const context = await browser.newContext();
    const testPage = await context.newPage();
    
    try {
      await testPage.goto(NEW_SITE, { timeout: 5000 });
      await context.close();
      await captureNewSite(browser, screenshots);
    } catch {
      console.log('\nNew site not running. Start with: just dev or just preview');
    }
    
    // Generate reports
    const textReport = generateTextReport(screenshots);
    fs.writeFileSync(path.join(SCREENSHOT_DIR, 'report.md'), textReport);
    console.log('\nText report saved: screenshots/report.md');
    
    generateHtmlReport(screenshots);
    console.log('HTML report saved: screenshots/comparison.html');
    
  } finally {
    await browser.close();
  }
  
  console.log('\nDone!');
}

main().catch(console.error);
