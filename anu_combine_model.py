import pandas as pd
from gurobipy import *
import numpy as np
import datetime

def solve_circular_supply_chain_epsilon_logged(num_eps_points=10):

    # Create log file
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    log_file = f"run_log_{timestamp}.txt"
    LOG = open(log_file, "w")

    def log(*msg):
        print(*msg)
        LOG.write(" ".join([str(m) for m in msg]) + "\n")

    log("====================================================")
    log(" STARTING MODEL RUN WITH FULL LOGGING ")
    log("====================================================\n")

    log("--- Loading file Germany_data_v2.xlsx ---")
    xls = pd.ExcelFile("Germany_data_v2.xlsx")

    # --------------------------
    # Helper to extract set
    # --------------------------
    def get_set(df, col):
        vals = [x for x in df[col].dropna().unique()]
        log(f"Loaded set {col}: {len(vals)} elements → {vals}")
        return vals


    # -----------------------------------------------------
    # LOAD SETS
    # -----------------------------------------------------
    df_sets = pd.read_excel(xls, '1. Sets')
    P = get_set(df_sets, 'Plants (P)')
    C = get_set(df_sets, 'Customer (C)')
    O = get_set(df_sets, 'Collection Centers (O)')
    F = get_set(df_sets, 'Refurbish Centers (F)')
    L = get_set(df_sets, 'Landfills (L)')
    S = get_set(df_sets, 'Suppliers (S)')
    K = get_set(df_sets, 'Module Types (K)')

    log("\n===== PARAMETERS LOADING =====\n")

    # -----------------------------------------------------
    # PRODUCTION COSTS
    # -----------------------------------------------------
    PC = pd.read_excel(xls, '2. Production Costs').set_index('Plant_ID')['Production_Cost_per_KWp (PC_p)'].to_dict()
    log("Production Costs (PC):", PC)

    # ----------------------------
    # OPERATIONAL COSTS (Corrected!)
    # ----------------------------
    df_ops = pd.read_excel(xls, '3. Operational Costs') \
                .set_index('Facility_ID')['Cost_per_Unit']

    CC = {o: df_ops.get(o, 0) for o in O}   # Collection per KWp
    FC = {f: df_ops.get(f, 0) for f in F}   # Refurbish per KWp
    DC = {l: df_ops.get(l, 0) for l in L}   # Disposal per kg

    print("Operational Costs loaded correctly:")
    print(" - Collection CC:", CC)
    print(" - Refurbish FC:", FC)
    print(" - Disposal DC:", DC)

    # ----------------------------
    # FIXED COSTS
    # ----------------------------
    df_fix = pd.read_excel(xls, '4. Fixed Costs') \
                .set_index('Facility_ID')['Fixed_Operational_Cost (Fix)']

    FixO = {o: df_fix.get(o, 0) for o in O}
    FixF = {f: df_fix.get(f, 0) for f in F} 

    # -----------------------------------------------------
    # PENALTY COSTS
    # -----------------------------------------------------
    Penalty = pd.read_excel(xls, "5. Penalty Costs").set_index("Module_Type_ID")["Penalty_Cost_per_KWp (Pen_k)"].to_dict()
    log("Penalty:", Penalty)

    # ----------------------------
    # DEMAND & RETURNS
    # ----------------------------
    df_dem = pd.read_excel(xls, '6. Demand & Returns')

    DEM = {(r['Customer_Zone_ID'], r['Module_Type_ID']): r['Demand_KWp (DEM_ck)']
        for _, r in df_dem.iterrows()}

    RET = {(r['Customer_Zone_ID'], r['Module_Type_ID']): r['Returns_KWp (RET_ck)']
        for _, r in df_dem.iterrows()}

    # ----------------------------
    # WEIGHTS
    # ----------------------------
    df_w = pd.read_excel(xls, '7. Module Weights')
    omega = {r['Module_Type_ID']: float(str(r['Weight_kg_per_KWp (omega_k)']).replace(',','.'))
            for _, r in df_w.iterrows()}

    # -----------------------------------------------------
    # YIELDS
    # -----------------------------------------------------
    df_y = pd.read_excel(xls, "8. Yield Rates").set_index("Facility_ID")["Yield_Rate"]
    alpha = {f: df_y.get(f, None) for f in F}
    log("Yield α_f:", alpha)

    # -----------------------------------------------------
    # CAPACITIES
    # -----------------------------------------------------
    CAP = pd.read_excel(xls, "9. Capacities").set_index("Facility_ID")["Capacity_Value"].to_dict()
    log("Capacity map:", CAP)

    # -----------------------------------------------------
    # REVENUES
    # -----------------------------------------------------
    df_rev = pd.read_excel(xls, "10. Revenues")
    Rev_reuse  = df_rev[df_rev["Revenue_Stream"]=="Reuse"].set_index("Item_ID")["Revenue_per_Unit (Rev)"].to_dict()
    Rev_refurb = df_rev[df_rev["Revenue_Stream"]=="Refurbish"].set_index("Item_ID")["Revenue_per_Unit (Rev)"].to_dict()
    log("Reuse revenue:", Rev_reuse)
    log("Refurb revenue:", Rev_refurb)

    # -----------------------------------------------------
    # DISTANCES
    # -----------------------------------------------------
    df_trans = pd.read_excel(xls, "11. Transportation")
    dist_map = {(r["Origin_ID"], r["Destination_ID"]): r["Distance_km"]
                for _, r in df_trans.iterrows()}

    def DIST(a,b): 
        return dist_map.get((a,b), 500)

    log("Transport entries:", len(dist_map))

    T_cost = 0.004
    log("Transport cost per kg-km =", T_cost)

    # -----------------------------------------------------
    # EMISSIONS
    # -----------------------------------------------------
    df_env = pd.read_excel(xls, "12. Environmental").set_index("Parameter_Name")["Value"]
    E_p  = df_env.get("E_p", 580)
    E_co = df_env.get("E_co", 0.4)
    E_f  = df_env.get("E_f", 1.2)
    E_l  = df_env.get("E_l", 0.3)
    T_emit = df_env.get("ET", 0.0009)

    log("Emissions loaded:", {"E_p":E_p, "E_co":E_co, "E_f":E_f, "E_l":E_l, "ET":T_emit})

    # ----------------------------
    # SUPPLIER BOM
    # ----------------------------
    df_bom = pd.read_excel(xls, '13. Supplier_BOM')

    BOM = df_bom.set_index('Supplier_ID')['Qty_per_Module'].to_dict()
    Mat_Cost = df_bom.set_index('Supplier_ID')['Cost_per_Unit'].to_dict()
    Mat_Weight = df_bom.set_index('Supplier_ID')['Weight_per_Unit_kg'].to_dict()
    Em_Supplier = df_bom.set_index('Supplier_ID')['Emission_per_Unit'].to_dict()

    print("Supplier BOM loaded:\n", BOM)
    print("Material Cost per Unit:\n", Mat_Cost)
    print("Material Weight per Unit:\n", Mat_Weight)
    print("Supplier Emission per Unit:\n", Em_Supplier)

    # ===================================================================
    #   PART 1 — BUILD BASE MODEL (VARIABLES + CONSTRAINTS)
    # ===================================================================
    log("\n===== BUILDING MODEL =====\n")

    m = Model("Circular_Logged")
    m.setParam("OutputFlag",0)

    # --- Variables ---
    X_pk  = m.addVars(P, K, name="X_pk", lb=0)
    X_pck = m.addVars(P, C, K, name="X_pck", lb=0)
    Y_cok = m.addVars(C, O, K, lb=0)
    Y_ock = m.addVars(O, C, K, lb=0)
    Y_ofk = m.addVars(O, F, K, lb=0)
    Y_olk = m.addVars(O, L, K, lb=0)
    Y_fpk = m.addVars(F, P, K, lb=0)
    S_ck  = m.addVars(C, K, lb=0)

    W_o = m.addVars(O, vtype=GRB.BINARY)
    W_f = m.addVars(F, vtype=GRB.BINARY)

    Z_sp = m.addVars(S, P, lb=0)

    m.update()

    log("Variables Created:")
    log(" - X_pk:", len(X_pk))
    log(" - X_pck:", len(X_pck))
    log(" - Y flows:", len(Y_cok)+len(Y_ock)+len(Y_ofk)+len(Y_olk)+len(Y_fpk))
    log(" - Shortage:", len(S_ck))
    log(" - Supplier flows:", len(Z_sp))
    log("\n===== ADDING CONSTRAINTS =====\n")


    # ======================================================
    # CONSTRAINTS (with logging)
    # ======================================================

    # Supplier BOM
    for p in P:
        for s in S:
            m.addConstr(Z_sp[s,p] == quicksum(X_pk[p,k] for k in K)*BOM[s])
    log("Added Supplier BOM constraints:", len(P)*len(S))

    # Demand
    m.update()
    count=0
    for c in C:
        for k in K:
            m.addConstr(
                quicksum(X_pck[p,c,k] for p in P)
              + quicksum(Y_ock[o,c,k] for o in O)
              + S_ck[c,k]
              == DEM.get((c,k),0)
            )
            count+=1
    log("Added Demand constraints:", count)

    # Returns
    for c in C:
        for k in K:
            m.addConstr(quicksum(Y_cok[c,o,k] for o in O) == RET.get((c,k),0))
    log("Added Return constraints:", len(C)*len(K))

    # Collection center balance + quality
    count=0
    for o in O:
        for k in K:
            In  = quicksum(Y_cok[c,o,k] for c in C)
            Out = quicksum(Y_ock[o,c,k] for c in C) \
                + quicksum(Y_ofk[o,f,k] for f in F) \
                + quicksum(Y_olk[o,l,k] for l in L)

            m.addConstr(In == Out)
            m.addConstr(quicksum(Y_ock[o,c,k] for c in C) <= 0.30 * In)
            m.addConstr(quicksum(Y_ofk[o,f,k] for f in F) <= 0.50 * In)
            count+=3
    log("Added collection balance + quality:", count)

    # Plant balance
    count=0
    for p in P:
        for k in K:
            m.addConstr(
                X_pk[p,k] + quicksum(Y_fpk[f,p,k] for f in F)
                == quicksum(X_pck[p,c,k] for c in C)
            )
            count+=1
    log("Added plant balance constraints:", count)

    # Refurb yield
    for f in F:
        for k in K:
            m.addConstr(
                quicksum(Y_fpk[f,p,k] for p in P)
                == alpha[f] * quicksum(Y_ofk[o,f,k] for o in O)
            )
    log("Added refurb yield constraints:", len(F)*len(K))

    # Capacity
    for p in P:
        m.addConstr(quicksum(X_pk[p,k] for k in K) <= CAP.get(p,1e12))
    for o in O:
        m.addConstr(quicksum(Y_cok[c,o,k]*omega[k] for c in C for k in K) <= CAP.get(o,1e12)*W_o[o])
    for f in F:
        m.addConstr(quicksum(Y_ofk[o,f,k]*omega[k] for o in O for k in K) <= CAP.get(f,1e12)*W_f[f])

    log("Added Capacity constraints.")
    log("\n===== DEFINING OBJECTIVES =====\n")

    # ======================================================
    # COST OBJECTIVE
    # ======================================================

    Expr_Fixed = quicksum(FixO[o]*W_o[o] for o in O) + \
                 quicksum(FixF[f]*W_f[f] for f in F)

    Expr_Ops = (
        quicksum(PC[p]*X_pk[p,k] for p in P for k in K) +
        quicksum(CC[o]*Y_cok[c,o,k] for c in C for o in O for k in K) +
        quicksum(FC[f]*Y_ofk[o,f,k] for o in O for f in F for k in K) +
        quicksum(DC[l]*Y_olk[o,l,k]*omega[k] for o in O for l in L for k in K) +
        quicksum(Mat_Cost[s]*Z_sp[s,p] for s in S for p in P)
    )

    Expr_Trans = (
        quicksum(T_cost * DIST(p,c) * X_pck[p,c,k] * omega[k] for p in P for c in C for k in K) +
        quicksum(T_cost * DIST(c,o) * Y_cok[c,o,k] * omega[k] for c in C for o in O for k in K) +
        quicksum(T_cost * DIST(o,c) * Y_ock[o,c,k] * omega[k] for o in O for c in C for k in K) +
        quicksum(T_cost * DIST(o,f) * Y_ofk[o,f,k] * omega[k] for o in O for f in F for k in K) +
        quicksum(T_cost * DIST(o,l) * Y_olk[o,l,k] * omega[k] for o in O for l in L for k in K) +
        quicksum(T_cost * DIST(f,p) * Y_fpk[f,p,k] * omega[k] for f in F for p in P for k in K)
    )

    Expr_Short = quicksum(Penalty[k]*S_ck[c,k] for c in C for k in K)

    Expr_Revenue = (
        quicksum(Rev_reuse.get(k,0)  * Y_ock[o,c,k] for o in O for c in C for k in K) +
        quicksum(Rev_refurb.get(k,0) * Y_fpk[f,p,k] for f in F for p in P for k in K)
    )

    Expr_Cost = Expr_Fixed + Expr_Ops + Expr_Trans + Expr_Short - Expr_Revenue

    log("Cost objective defined. Components:")
    log(" - Fixed:", Expr_Fixed)
    log(" - Ops:", Expr_Ops)
    log(" - Transport:", Expr_Trans)
    log(" - Shortage:", Expr_Short)
    log(" - Revenue:", Expr_Revenue)

    # ======================================================
    # ENVIRONMENTAL OBJECTIVE
    # ======================================================

    Expr_Env = (
        quicksum(E_p  * X_pk[p,k] for p in P for k in K) +
        quicksum(E_co * Y_cok[c,o,k] for c in C for o in O for k in K) +
        quicksum(E_f  * Y_ofk[o,f,k] for o in O for f in F for k in K) +
        quicksum(E_l  * Y_olk[o,l,k] * omega[k] for o in O for l in L for k in K) +
        quicksum(T_emit * DIST(p,c) * X_pck[p,c,k] * omega[k] for p in P for c in C for k in K) +
        quicksum(T_emit * DIST(c,o) * Y_cok[c,o,k] * omega[k] for c in C for o in O for k in K) +
        quicksum(T_emit * DIST(o,c) * Y_ock[o,c,k] * omega[k] for o in O for c in C for k in K) +
        quicksum(T_emit * DIST(o,f) * Y_ofk[o,f,k] * omega[k] for o in O for f in F for k in K) +
        quicksum(T_emit * DIST(o,l) * Y_olk[o,l,k] * omega[k] for o in O for l in L for k in K) +
        quicksum(T_emit * DIST(f,p) * Y_fpk[f,p,k] * omega[k] for f in F for p in P for k in K)
    )

    log("Environmental expression defined.")

    # =================================================================
    # PAYOFF TABLE
    # =================================================================
    log("\n===== COMPUTING PAYOFF TABLE =====\n")

    # ---------------------------------------------------
    # 1. MINIMIZE COST
    # ---------------------------------------------------
    m.setObjective(Expr_Cost, GRB.MINIMIZE)
    m.optimize()
    Zcost_min = m.objVal
    Zenv_at_costmin = Expr_Env.getValue()

    log(f"Min Cost Solution → Cost={Zcost_min}, Env={Zenv_at_costmin}")

    # ---------------------------------------------------
    # 2. MINIMIZE ENVIRONMENT
    # ---------------------------------------------------
    m.setObjective(Expr_Env, GRB.MINIMIZE)
    m.optimize()
    Zenv_min = m.objVal
    Zcost_at_envmin = Expr_Cost.getValue()

    log(f"Min Env Solution → Env={Zenv_min}, Cost={Zcost_at_envmin}")

    # =================================================================
    # PARETO CURVE A:
    #   Minimize COST  subject to  ENV ≤ ε
    # =================================================================

    log("\n===== STARTING EPSILON LOOP (COST-MIN CURVE) =====\n")

    eps_env_values = np.linspace(Zenv_min, Zenv_at_costmin, num_eps_points)
    results_cost_min = []

    for eps in eps_env_values:
        Con_eps = m.addConstr(Expr_Env <= eps)
        m.setObjective(Expr_Cost, GRB.MINIMIZE)
        m.optimize()

        results_cost_min.append((eps, m.objVal, Expr_Env.getValue()))
        log(f"[Curve A] ε_env={eps:.2f} → Cost={m.objVal:.2f}, Env={Expr_Env.getValue():.2f}")

        m.remove(Con_eps)
        m.update()

    df_A = pd.DataFrame(results_cost_min, columns=["epsilon_env", "cost", "env"])
    df_A.to_csv(f"pareto_curve_cost_min_{timestamp}.csv", index=False)

    log(f"Saved Curve A → pareto_curve_cost_min_{timestamp}.csv")

    # =================================================================
    # PARETO CURVE B:
    #   Minimize ENV  subject to  COST ≤ ε
    # =================================================================

    log("\n===== STARTING EPSILON LOOP (ENV-MIN CURVE) =====\n")

    # Here we sweep the COST range
    # you can expand upper bound if needed
    eps_cost_values = np.linspace(Zcost_min, Zcost_at_envmin, num_eps_points)
    results_env_min = []

    for eps in eps_cost_values:
        Con_eps = m.addConstr(Expr_Cost <= eps)
        m.setObjective(Expr_Env, GRB.MINIMIZE)
        m.optimize()

        results_env_min.append((eps, Expr_Cost.getValue(), m.objVal))
        log(f"[Curve B] ε_cost={eps:.2f} → Cost={Expr_Cost.getValue():.2f}, Env={m.objVal:.2f}")

        m.remove(Con_eps)
        m.update()

    df_B = pd.DataFrame(results_env_min, columns=["epsilon_cost", "cost", "env"])
    df_B.to_csv(f"pareto_curve_env_min_{timestamp}.csv", index=False)

    log(f"Saved Curve B → pareto_curve_env_min_{timestamp}.csv")

    log("\n===== ALL RESULTS SAVED SUCCESSFULLY =====\n")
    LOG.close()

    return results_cost_min, results_env_min

# -------------------------------
# RUN THE MODEL (MAIN FUNCTION)
# -------------------------------
if __name__ == "__main__":
    print("\n========================================")
    print(" Running Circular Supply Chain Model ")
    print(" Multi-Objective Optimization (ε-Constraint)")
    print("========================================\n")

    # Run the model
    results_cost_curve, results_env_curve = solve_circular_supply_chain_epsilon_logged(
        num_eps_points=10
    )

    print("\n========================================")
    print(" Model Finished Running Successfully! ")
    print(" Generated both Pareto curves:")
    print("   1. Cost-minimizing Pareto curve")
    print("   2. Environment-minimizing Pareto curve")
    print(" CSV outputs saved with timestamp.")
    print("========================================\n")

    print("First few results from Cost-Minimizing Curve:")
    for r in results_cost_curve[:3]:
        print("  ε_env =", r[0], " cost =", r[1], " env =", r[2])

    print("\nFirst few results from Env-Minimizing Curve:")
    for r in results_env_curve[:3]:
        print("  ε_cost =", r[0], " cost =", r[1], " env =", r[2])
