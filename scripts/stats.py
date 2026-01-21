#!/usr/bin/env python3
"""Show statistics about the directory data."""

import yaml
from pathlib import Path
from collections import Counter

data_dir = Path("data/companies")
if not data_dir.exists():
    print("No data found.")
    exit(1)

companies = list(data_dir.glob("*.yaml"))
print(f"Total companies: {len(companies)}")

primes = smes = featured = 0
streams: Counter[str] = Counter()
stakeholders: Counter[str] = Counter()

for f in companies:
    with open(f) as fh:
        c = yaml.safe_load(fh)
        if c.get("is_prime"):
            primes += 1
        if c.get("is_sme"):
            smes += 1
        if c.get("is_featured"):
            featured += 1
        for s in c.get("capability_streams", []):
            streams[s] += 1
        for s in c.get("stakeholders", []):
            stakeholders[s] += 1

print(f"  Primes: {primes}")
print(f"  SMEs: {smes}")
print(f"  Featured: {featured}")
print(f"\nStakeholder types:")
for s, count in stakeholders.most_common():
    print(f"  {s}: {count}")
print(f"\nTop capability streams:")
for s, count in streams.most_common(10):
    print(f"  {s}: {count}")
