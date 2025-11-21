# model_from_excel.py
import pandas as pd
import gurobipy as gp
from gurobipy import GRB

from math import isfinite

EXCEL_PATH = "supply_chain_table_2.ods"

bS_df = pd.read_excel(EXCEL_PATH, sheet_name="bS_supply_capacity", engine='odf')        # supplier, product, capacity
bMH_df = pd.read_excel(EXCEL_PATH, sheet_name="bMH_facility_capacity", engine='odf')   # facility, capacity
demand_df = pd.read_excel(EXCEL_PATH, sheet_name="demand", engine='odf')               # customer, product, demand
bom_df = pd.read_excel(EXCEL_PATH, sheet_name="BOM", engine='odf')                     # material_q, product_p, amount
r_df = pd.read_excel(EXCEL_PATH, sheet_name="r", engine='odf')                     # facility, product, r
transport_df = pd.read_excel(EXCEL_PATH, sheet_name="transport_cost", engine='odf')    # i, j, product, cost
proc_df = pd.read_excel(EXCEL_PATH, sheet_name="procurement_cost", engine='odf')       # supplier, product, cost
manu_df = pd.read_excel(EXCEL_PATH, sheet_name="manufacturing_cost", engine='odf')     # facility, product, cost
fixed_df = pd.read_excel(EXCEL_PATH, sheet_name="fixed_cost", engine='odf')           # facility, fixed_cost


### Build sets
S = sorted(proc_df["supplier"].unique().astype(str).tolist())

facilities_from_bMH = sorted(bMH_df["facility"].astype(str).tolist())

M = facilities_from_bMH.copy()

C = sorted(demand_df["customer"].unique().astype(str).tolist())

prods = set()
if "product" in proc_df.columns: prods.update(proc_df["product"].astype(str).unique())
if "product" in demand_df.columns: prods.update(demand_df["product"].astype(str).unique())
if "product" in transport_df.columns: prods.update(transport_df["product"].astype(str).unique())
if "product_p" in bom_df.columns: prods.update(bom_df["product_p"].astype(str).unique())
P = sorted([p for p in prods if pd.notna(p)])

materials = []
if "material_q" in bom_df.columns:
    materials = sorted(bom_df["material_q"].astype(str).unique().tolist())

### Determine warehouses W and arcs from transport sheet
transport_df["i"] = transport_df["i"].astype(str)
transport_df["j"] = transport_df["j"].astype(str)
transport_df["product"] = transport_df["product"].astype(str)

arcs = set( (row.i, row.j, row[3]) for row in transport_df.itertuples() )

src_nodes = sorted(transport_df["i"].unique())
dst_nodes = sorted(transport_df["j"].unique())

W_candidates = [n for n in dst_nodes if (n not in S) and (n not in C) and (n not in M)]
W = sorted(list(set(W_candidates)))

M = [m for m in M if m not in W]


### Parameter
# b_{j p}^S : supplier-product capacities
b_s_p = { (row.supplier, row["product"]): row.capacity
          for _, row in bS_df.iterrows() }

# b_j^{M/H} : facility capacity units
b_MH = { row.facility: row.capacity for _, row in bMH_df.iterrows() }

# d_{j p} demand
d = { (row.customer, row["product"]): row.demand for _, row in demand_df.iterrows() }

a_qp = {}
if {"material_q","product_p","amount"}.issubset(bom_df.columns):
    for _, row in bom_df.iterrows():
        a_qp[(str(row.material_q), str(row.product_p))] = float(row.amount)

# r_{j p}
r = { (row.facility, row["product"]): row.r for _, row in r_df.iterrows() }

# transport cost c_{i j p}^T
cT = { (row.i, row.j, row["product"]): float(row.cost) for _, row in transport_df.iterrows() }

# procurement cost c_{j p}^P
cP = { (row.supplier, row["product"]): float(row.cost) for _, row in proc_df.iterrows() }

# manufacturing cost c_{j p}^M
cM = { (row.facility, row["product"]): float(row.cost) for _, row in manu_df.iterrows() }

# fixed facility cost c_j^F
cF = { row.facility: float(row.fixed_cost) for _, row in fixed_df.iterrows() }

supplier_items = set([k[1] for k in b_s_p.keys()])

if len(a_qp)==0 or not (set(materials) & supplier_items):
    print("Warning: BOM materials not matching supplier items or BOM empty. Falling back to identity-BOM.")
    a_qp = { (p,p): 1.0 for p in P }
    materials = sorted(P)
else:
    materials = sorted(list(set(materials)))







m = gp.Model("SupplyChain_MultiProduct")

# Das sind alle Pfeile x
arcs = sorted(arcs)

# Decision variables
x = m.addVars(arcs, lb=0.0, name="x")                      # flow on arcs (i,j,p)
z = m.addVars([(j,p) for j in (M + W) for p in P], lb=0.0, name="z")  # produced/handled at M and W
y = m.addVars((M + W), vtype=GRB.BINARY, name="y")         # open facility

# Objective components
C_P = gp.quicksum( cP.get((i,p), 0.0) * x[i,j,p]
                   for (i,j,p) in arcs
                   if i in S and j in (M+W) )

# C^M: manufacturing/handling cost 
C_M = gp.quicksum( cM.get((j,p), 0.0) * z[j,p] for j in (M+W) for p in P )

# C^T: transport cost on arcs 
C_T = gp.quicksum( cT.get((i,j,p), 0.0) * x[i,j,p] for (i,j,p) in arcs )

# C^F: fixed facility cost
C_F = gp.quicksum( cF.get(j, 0.0) * y[j] for j in (M+W) )

m.setObjective(C_P + C_M + C_T + C_F, GRB.MINIMIZE)





### Constraints

# 1. Demand Fulfillment
# $\sum_{i \in W} x_{ijp} = d_{jp} \quad \forall j \in C, p \in P$
for j in C:
    for p in P:
        m.addConstr(gp.quicksum(
            x[(i, j, p)]
            for i in W
            ) 
            == 
            d.get((j,p), 0.0),name=f"demand_{j}_{p}")

# 2. Flow Conservation in Warehouses
# $\sum_{i \in (S \cup M)} x_{ijp} = z_{jp} \quad \forall j \in W, p \in P$
# $z_{jp} = \sum_{k \in C} x_{jkp} \quad \forall j \in W, p \in P$
for j in W:
    for p in P:
        m.addConstr(
            gp.quicksum(x[(i,j,p)] for i in (S+M)) 
            == 
            z[(j,p)]
            , name=f"wh_in_{j}_{p}")
        m.addConstr(
            z[(j,p)] 
            == 
            gp.quicksum(x[(j,k,p)] for k in C)
            , name=f"wh_out_{j}_{p}")

# 3. Flow Conservation in Manufacturing Plants
# $\sum_{i \in S} x_{ijq} = \sum_{p \in P} a_{qp} \cdot z_{jp} \quad \forall j \in M, q \in P$
# $z_{jp} = \sum_{k \in W} x_{jkp} \quad \forall j \in M, p \in P$
for j in M:
    ## TODO !!! implement bill of materials 
    # for q in P:
    #     m.addConstr(
    #         gp.quicksum(x[(i, j, q)] for i in S)
    #         ==
    #         gp.quicksum(a[q, p] * z[(j, p)] for p in P),
    #         name=f"mf_inout_{j}_{q}"
    #     )
    for p in P:
        m.addConstr(
            z[(j, p)]
            == gp.quicksum(x[(j, k, p)] for k in W),
            name=f"mf_out_{j}_{p}"
        )

# 4. Manufacturing/Handling Capacity
# $\sum_{p \in P} r_{jp} \cdot z_{jp} \leq b_j^{M/H} \cdot y_j \quad \forall j \in (M \cup W)$
for j in M + W:
    m.addConstr(
        gp.quicksum(r[(j, p)] * z[(j, p)] for p in P)
        <= b_MH[j] * y[j],
        name=f"cap_{j}"
    )

# Add Big-M: z_{j p} <= M_{j p} * y_j for tightening
for j in (M + W):
    for p in P:
        r_jp = r.get((j,p), None)
        Mjp = b_MH.get(j, 1e6) / r_jp
        m.addConstr(z[j,p] <= Mjp * y[j], name=f"bigM_{j}_{p}")

# 5. Supply Capacity
# $\sum_{k \in (M \cup W)} x_{jkp} \leq b_{jp}^S \quad \forall j \in S, p \in P$
for j in S:
    for p in P:
        m.addConstr(
            gp.quicksum(x[(j, k, p)] for k in M + W)
            <= b_s_p[j, p],
            name=f"supp_{j}_{p}"
        )


m.optimize()

