import type { APIRoute } from 'astro';
import { getCollection } from 'astro:content';

export const GET: APIRoute = async () => {
  const companyEntries = await getCollection('companies');
  const companies = companyEntries
    .map(entry => entry.data)
    .sort((a, b) => a.name.localeCompare(b.name));

  const headers = [
    'name', 'slug', 'website', 'email', 'phone', 'address',
    'contact_name', 'contact_title', 'logo_url',
    'latitude', 'longitude', 'is_prime', 'is_sme',
    'stakeholders', 'capability_streams', 'capability_domains',
    'industrial_capabilities', 'regions', 
    'capabilities', 'discriminators', 'overview'
  ];

  function escapeCSV(val: any): string {
    if (val === undefined || val === null) return '';
    if (Array.isArray(val)) return `"${val.join('; ')}"`;
    if (typeof val === 'boolean') return val ? 'true' : 'false';
    const str = String(val);
    if (str.includes(',') || str.includes('"') || str.includes('\n')) {
      return `"${str.replace(/"/g, '""')}"`;
    }
    return str;
  }

  const rows = companies.map(c => 
    headers.map(h => escapeCSV((c as any)[h])).join(',')
  );

  const csv = [headers.join(','), ...rows].join('\n');

  return new Response(csv, {
    headers: {
      'Content-Type': 'text/csv',
      'Content-Disposition': 'attachment; filename="companies.csv"'
    }
  });
};
