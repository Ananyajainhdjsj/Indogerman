# paste into your script or run in a Python REPL in the same environment
import pandas as pd
from pprint import pprint
EXCEL_PATH = "supply_chain_table_2.ods"

# load sheets (engine odf)
bS_df = pd.read_excel(EXCEL_PATH, sheet_name="bS_supply_capacity", engine='odf')
bMH_df = pd.read_excel(EXCEL_PATH, sheet_name="bMH_facility_capacity", engine='odf')
demand_df = pd.read_excel(EXCEL_PATH, sheet_name="demand", engine='odf')
bom_df = pd.read_excel(EXCEL_PATH, sheet_name="BOM", engine='odf')
r_df = pd.read_excel(EXCEL_PATH, sheet_name="r", engine='odf')
transport_df = pd.read_excel(EXCEL_PATH, sheet_name="transport_cost", engine='odf')
proc_df = pd.read_excel(EXCEL_PATH, sheet_name="procurement_cost", engine='odf')
manu_df = pd.read_excel(EXCEL_PATH, sheet_name="manufacturing_cost", engine='odf')
fixed_df = pd.read_excel(EXCEL_PATH, sheet_name="fixed_cost", engine='odf')

product = "P2"   # change if your product name differs exactly (case sensitive)
nodes_of_interest = ["S1","S2","M1","M2","W1","C1","C2"]

print("\n=== DEMAND rows for P2 ===")
print(demand_df[demand_df['product'].astype(str) == product])

print("\n=== TRANSPORT arcs with P2 ===")
td = transport_df[transport_df['product'].astype(str) == product]
print("Total transport rows with P2:", len(td))
pprint(td[['i','j','product','cost']].to_dict('records'))

print("\n=== Supplier capacities (bS) for P2 ===")
bs = bS_df[(bS_df['product'].astype(str) == product)]
if bs.empty:
    print("No supplier capacity rows for product", product)
else:
    pprint(bs.to_dict('records'))

print("\n=== Procurement costs for P2 ===")
pc = proc_df[proc_df['product'].astype(str) == product]
pprint(pc.to_dict('records'))

print("\n=== Facility capacities (bMH) ===")
pprint(bMH_df.to_dict('records'))

print("\n=== Manufacturing r values for P2 ===")
rvals = r_df[r_df['product'].astype(str) == product]
pprint(rvals.to_dict('records'))

print("\n=== Manufacturing costs cM for P2 ===")
mc = manu_df[manu_df['product'].astype(str) == product]
pprint(mc.to_dict('records'))

print("\n=== BOM rows mentioning P2 (as product_p or material_q) ===")
bom_p = bom_df[(bom_df.get('product_p', bom_df.columns) .astype(str) == product) | (bom_df.get('material_q', bom_df.columns).astype(str) == product)]
pprint(bom_p.to_dict('records'))

print("\n=== Rows for nodes of interest in transport (any product) ===")
pprint(transport_df[transport_df['i'].isin(nodes_of_interest) | transport_df['j'].isin(nodes_of_interest)].to_dict('records')[:100])

print("\n=== Quick summary counts ===")
print("Unique suppliers in bS:", sorted(bS_df['supplier'].astype(str).unique().tolist()))
print("Unique products in bS:", sorted(bS_df['product'].astype(str).unique().tolist()))
print("Unique products in transport:", sorted(transport_df['product'].astype(str).unique().tolist()))
