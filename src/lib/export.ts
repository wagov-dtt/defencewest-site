import { getCollection } from "astro:content";
import { getTaxonomies } from "./taxonomies";

// Field definitions with human-readable labels
export const exportFields = [
  // Identity
  { key: "name", label: "Company Name" },
  { key: "slug", label: "Slug" },
  { key: "url", label: "Directory URL", computed: true },
  { key: "overview", label: "Overview" },
  // Contact
  { key: "website", label: "Website" },
  { key: "email", label: "Email" },
  { key: "phone", label: "Phone" },
  { key: "address", label: "Address" },
  { key: "contact_name", label: "Contact Name" },
  { key: "contact_title", label: "Contact Title" },
  // Location
  { key: "regions", label: "Regions" },
  { key: "latitude", label: "Latitude" },
  { key: "longitude", label: "Longitude" },
  // Company type
  { key: "is_prime", label: "Prime Contractor" },
  { key: "is_sme", label: "SME" },
  { key: "is_indigenous_owned", label: "Indigenous Owned" },
  { key: "is_veteran_owned", label: "Veteran Owned" },
  // Taxonomies
  { key: "stakeholders", label: "Stakeholders" },
  { key: "capability_streams", label: "Capability Streams" },
  { key: "capability_domains", label: "Capability Domains" },
  { key: "industrial_capabilities", label: "Industrial Capabilities" },
  // Details
  { key: "capabilities", label: "Capabilities" },
  { key: "discriminators", label: "Discriminators" },
  // Internal
  { key: "logo_url", label: "Logo URL" },
] as const;

export const exportHeaders = exportFields.map((f) => f.label);
export const exportKeys = exportFields.map((f) => f.key);

// Validate taxonomy values and throw if invalid (fails build)
export function validateTaxonomies(
  companies: Array<{ slug: string; [key: string]: any }>,
  taxonomies: ReturnType<typeof getTaxonomies>,
) {
  const errors: string[] = [];

  const taxonomyFields = [
    { field: "stakeholders", valid: new Set(taxonomies.stakeholders) },
    {
      field: "capability_streams",
      valid: new Set(Object.keys(taxonomies.capability_streams)),
    },
    {
      field: "capability_domains",
      valid: new Set(taxonomies.capability_domains),
    },
    {
      field: "industrial_capabilities",
      valid: new Set(taxonomies.industrial_capabilities),
    },
    { field: "regions", valid: new Set(taxonomies.regions) },
  ];

  for (const company of companies) {
    for (const { field, valid } of taxonomyFields) {
      const values = company[field] || [];
      for (const value of values) {
        if (!valid.has(value)) {
          errors.push(`${company.slug}: Invalid ${field} value "${value}"`);
        }
      }
    }

    // Check slug matches expected format
    if (!/^[a-z0-9-]+$/.test(company.slug)) {
      errors.push(
        `${company.slug}: Invalid slug format (use lowercase, numbers, hyphens only)`,
      );
    }
  }

  if (errors.length > 0) {
    throw new Error(`Validation errors:\n${errors.join("\n")}`);
  }
}

// Get validated, sorted company data for export
export async function getExportData() {
  const companyEntries = await getCollection("companies");
  const companies = companyEntries
    .map((entry) => entry.data)
    .sort((a, b) => a.name.localeCompare(b.name));

  // Validate taxonomy values (throws on error, failing the build)
  const taxonomies = getTaxonomies();
  validateTaxonomies(companies, taxonomies);

  return companies;
}

// Format a value for export (handles arrays, booleans, etc.)
export function formatValue(val: any): string {
  if (val === undefined || val === null) return "";
  if (Array.isArray(val)) return val.join("; ");
  if (typeof val === "boolean") return val ? "Yes" : "No";
  return String(val);
}

// Get row data in header order
export function getRowData(company: any, baseUrl: string): any[] {
  return exportFields.map((f) => {
    // Computed URL field
    if (f.key === "url") {
      return `${baseUrl}/company/${company.slug}/`;
    }

    const val = company[f.key];
    if (val === undefined || val === null) return "";
    if (Array.isArray(val)) return val.join("; ");
    if (typeof val === "boolean") return val ? "Yes" : "No";
    return val;
  });
}
