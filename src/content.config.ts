import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

// Company schema matching the YAML structure
const companySchema = z.object({
  name: z.string(),
  slug: z.string(),
  overview: z.string().optional(),
  website: z.string().optional(),
  logo_url: z.string().optional(),

  // Contact info
  contact_name: z.string().optional(),
  contact_title: z.string().optional(),
  address: z.string().optional(),
  phone: z
    .union([z.string(), z.number()])
    .transform((v) => String(v))
    .optional(),
  email: z.string().optional(),

  // Location
  latitude: z.number().optional(),
  longitude: z.number().optional(),

  // Company type flags
  is_prime: z.boolean().optional().default(false),
  is_sme: z.boolean().optional().default(false),

  // Taxonomy arrays
  stakeholders: z.array(z.string()).optional().default([]),
  capability_streams: z.array(z.string()).optional().default([]),
  capability_domains: z.array(z.string()).optional().default([]),
  industrial_capabilities: z.array(z.string()).optional().default([]),
  regions: z.array(z.string()).optional().default([]),

  // Extended content
  capabilities: z.string().optional(),
  discriminators: z.string().optional(),
});

const companies = defineCollection({
  loader: glob({ pattern: "**/*.yaml", base: "./data/companies" }),
  schema: companySchema,
});

export const collections = { companies };

// Export types for use in components
export type Company = z.infer<typeof companySchema>;
