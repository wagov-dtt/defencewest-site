import type { APIRoute } from "astro";
import Papa from "papaparse";
import { exportFields, exportHeaders, getExportData } from "../lib/export";

export const GET: APIRoute = async ({ site }) => {
  const companies = await getExportData();
  const baseUrl = site!.href.replace(/\/$/, "");

  // Transform data for CSV
  const rows = companies.map((c) => {
    const row: Record<string, string> = {};
    for (const f of exportFields) {
      // Computed URL field
      if (f.key === "url") {
        row[f.label] = `${baseUrl}/company/${(c as any).slug}/`;
        continue;
      }

      const val = (c as any)[f.key];
      if (val === undefined || val === null) {
        row[f.label] = "";
      } else if (Array.isArray(val)) {
        row[f.label] = val.join("; ");
      } else if (typeof val === "boolean") {
        row[f.label] = val ? "Yes" : "No";
      } else {
        row[f.label] = String(val);
      }
    }
    return row;
  });

  const csv = Papa.unparse(rows, {
    columns: [...exportHeaders],
  });

  return new Response(csv, {
    headers: {
      "Content-Type": "text/csv",
      "Content-Disposition": 'attachment; filename="wa-defence-directory.csv"',
    },
  });
};
