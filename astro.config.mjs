import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import relativeLinks from 'astro-relative-links';

export default defineConfig({
  site: 'https://deed.wa.gov.au',
  output: 'static',
  build: {
    format: 'directory',
  },
  integrations: [
    relativeLinks(),
    sitemap({
      filter: (page) => !page.includes('/admin'),
    }),
  ],
  devToolbar: {
    enabled: false,
  },
});
