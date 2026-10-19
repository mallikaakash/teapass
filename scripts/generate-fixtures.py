#!/usr/bin/env python3
"""Repeatable, entirely fictional TeaPass data. Never represents real growers or lab findings."""
import csv
import json
import random
from pathlib import Path

rng = random.Random(20261019)
root = Path(__file__).resolve().parents[1] / "fixtures"
root.mkdir(exist_ok=True)


def write(name, value):
    (root / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def table(name, rows):
    with (root / name).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


actors = [{"id": f"GROWER-{i:02}", "name": f"Fictional grower {i}", "role": "grower", "synthetic": True}
          for i in range(1, 6)]
actors += [{"id": "FACTORY-01", "role": "factory", "synthetic": True},
           {"id": "LAB-01", "role": "lab", "synthetic": True},
           {"id": "BLENDER-01", "role": "blender", "synthetic": True}]
write("actors.json", actors)
write("facilities.json", [{"id": f"FACILITY-{i}", "type": "FICTIONAL_PROCESSING", "synthetic": True}
                          for i in range(1, 3)])
lots = [{"id": f"LEAF-{i:02}", "grower": f"GROWER-{1+(i-1)%5:02}",
         "material": "GREEN_LEAF", "quantity_g": 400000 if i%2 else 320000,
         "synthetic": True} for i in range(1, 21)]
table("green_leaf_lots.csv", lots)
manufacturing=[]
for i, lot in enumerate(lots[:10],1):
    mass=lot["quantity_g"]; made=mass//4; waste=mass//10
    manufacturing.append({"id":f"PROCESS-{i:02}","input":lot["id"],"input_g":mass,
        "output":f"MADE-{i:02}","output_g":made,"waste_g":waste,"loss_g":mass-made-waste,
        "policy":"SYNTHETIC_YIELD_15_35_PERCENT","synthetic":True})
(root/"manufacturing_events.jsonl").write_text("".join(json.dumps(x,sort_keys=True)+"\n" for x in manufacturing))
blends=[{"id":f"BLEND-{i:02}","inputs":[f"MADE-{2*i-1:02}",f"MADE-{2*i:02}"],
         "input_g":[100000,80000],"contributions_g":[60000,40000],"remainders_g":[40000,40000],
         "output_g":100000,"synthetic":True} for i in range(1,5)]
write("blend_recipes_PRIVATE.json",blends)
table("lab_results_synthetic.csv",[{"batch":b["id"],"lab":"LAB-01","measurement_demo_units":7 if i==3 else rng.randint(1,4),
    "threshold_demo_units":5,"policy":"SYNTHETIC_RESIDUE_V1_NOT_REGULATORY","synthetic":True} for i,b in enumerate(blends)])
table("auction_transactions_synthetic.csv",[{"id":f"AUCTION-{i}","lot":f"MADE-{i:02}","synthetic":True} for i in range(1,7)])
write("simulated_exports.json",[{"id":f"EXPORT-{i}","batch":f"BLEND-{i:02}","synthetic":True} for i in range(1,3)])
write("public_product_passports.json",[{"alias":b["id"],"material":"BLENDED_TEA","synthetic":True,
    "verification_status":"NOT_VERIFIED","note":"Fixture only; no proof created by this generator."} for b in blends])
(root/"README.md").write_text("# Synthetic fixtures\n\nGenerated with seed 20261019 by `scripts/generate-fixtures.py`. All parties, quantities, auctions, exports and measurements are fictional. Files ending PRIVATE contain synthetic recipe examples; never place participant secrets or real recipes in Git. Generating these fixtures does not issue notes or create valid claims.\n")
print("Generated deterministic synthetic fixtures (no keys, personal data or verified claims).")
