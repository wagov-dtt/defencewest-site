import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

// Use base path for GitHub Pages subdirectory deployment
const isGitHubPages = process.env.GITHUB_ACTIONS === 'true';

export default defineConfig({
  site: isGitHubPages 
    ? 'https://wagov-dtt.github.io' 
    : 'https://deed.wa.gov.au',
  base: isGitHubPages ? '/defencewest-site/' : '/',
  output: 'static',
  build: {
    format: 'directory',
  },
  integrations: [
    sitemap({
      filter: (page) => !page.includes('/admin'),
    }),
  ],
  devToolbar: {
    enabled: false,
  },
});
