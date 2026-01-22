import { defineConfig } from "astro/config";
import sitemap from "@astrojs/sitemap";
import relativeLinks from "astro-relative-links";

export default defineConfig({
  site: "https://wagov-dtt.github.io/defencewest-site/",
  output: "static",
  build: {
    format: "directory",
  },
  integrations: [
    relativeLinks(),
    sitemap({
      filter: (page) => !page.includes("/edit/"),
    }),
  ],
  devToolbar: {
    enabled: false,
  },
});
