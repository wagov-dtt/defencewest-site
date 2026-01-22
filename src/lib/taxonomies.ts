import fs from "node:fs";
import path from "node:path";
import yaml from "yaml";

export interface Taxonomies {
  stakeholders: string[];
  capability_streams: Record<string, string>;
  capability_domains: string[];
  industrial_capabilities: string[];
  regions: string[];
}

let cached: Taxonomies | null = null;

export function getTaxonomies(): Taxonomies {
  if (cached) return cached;

  const taxonomiesPath = path.join(process.cwd(), "data/taxonomies.yaml");
  cached = yaml.parse(fs.readFileSync(taxonomiesPath, "utf-8"));
  return cached!;
}

export function getStreamIcons(): Record<string, string> {
  return getTaxonomies().capability_streams || {};
}
