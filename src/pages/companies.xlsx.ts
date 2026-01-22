import type { APIRoute } from "astro";
import * as XLSX from "xlsx";
import {
  exportFields,
  exportHeaders,
  getExportData,
  getRowData,
} from "../lib/export";

export const GET: APIRoute = async ({ site }) => {
  const companies = await getExportData();
  const baseUrl = site!.href.replace(/\/$/, "");

  // Create worksheet data with headers
  const wsData = [
    [...exportHeaders],
    ...companies.map((c) => getRowData(c, baseUrl)),
  ];

  // Create workbook and worksheet
  const wb = XLSX.utils.book_new();
  const ws = XLSX.utils.aoa_to_sheet(wsData);

  // Set column widths based on field type
  ws["!cols"] = exportFields.map((f) => {
    if (["overview", "capabilities", "discriminators"].includes(f.key)) {
      return { wch: 50 };
    }
    if (["address", "website", "url"].includes(f.key)) {
      return { wch: 40 };
    }
    if (f.key.includes("capability") || f.key === "industrial_capabilities") {
      return { wch: 30 };
    }
    return { wch: 18 };
  });

  // Freeze first row (header)
  ws["!freeze"] = { xSplit: 0, ySplit: 1 };

  // Add auto-filter to header row
  const lastCol = XLSX.utils.encode_col(exportHeaders.length - 1);
  const lastRow = companies.length + 1;
  ws["!autofilter"] = { ref: `A1:${lastCol}${lastRow}` };

  XLSX.utils.book_append_sheet(wb, ws, "Companies");

  // Generate buffer
  const buf = XLSX.write(wb, { type: "buffer", bookType: "xlsx" });

  return new Response(buf, {
    headers: {
      "Content-Type":
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "Content-Disposition": 'attachment; filename="wa-defence-directory.xlsx"',
    },
  });
};
