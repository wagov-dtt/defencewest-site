#!/usr/bin/env python3
"""Export company data as CSV for spreadsheet editing."""

import csv
import yaml
from pathlib import Path

data_dir = Path("data/companies")
output = Path("data/companies.csv")

companies = []
for f in sorted(data_dir.glob("*.yaml")):
    with open(f) as fh:
        companies.append(yaml.safe_load(fh))

with open(output, "w", newline="", encoding="utf-8") as csvfile:
    fieldnames = [
        "slug",
        "name",
        "website",
        "overview",
        "email",
        "phone",
        "address",
        "is_prime",
        "is_sme",
        "is_featured",
        "stakeholders",
        "capability_streams",
        "capability_domains",
        "industrial_capabilities",
        "regions",
    ]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    for c in companies:
        writer.writerow(
            {
                "slug": c.get("slug", ""),
                "name": c.get("name", ""),
                "website": c.get("website", ""),
                "overview": c.get("overview", "")[:500],
                "email": c.get("email", ""),
                "phone": c.get("phone", ""),
                "address": c.get("address", ""),
                "is_prime": c.get("is_prime", False),
                "is_sme": c.get("is_sme", False),
                "is_featured": c.get("is_featured", False),
                "stakeholders": "; ".join(c.get("stakeholders", [])),
                "capability_streams": "; ".join(c.get("capability_streams", [])),
                "capability_domains": "; ".join(c.get("capability_domains", [])),
                "industrial_capabilities": "; ".join(
                    c.get("industrial_capabilities", [])
                ),
                "regions": "; ".join(c.get("regions", [])),
            }
        )

print(f"Exported {len(companies)} companies to {output}")
