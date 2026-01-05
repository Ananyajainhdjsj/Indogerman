import pandas as pd
from gurobipy import *
import numpy as np
import datetime
import os

# ==========================================
# 1. DEFINE SCENARIOS
# ==========================================
scenarios = {
    "A": {
        "name": "Linear_Like",
        "reuse_limit": 0.10,   # 10% Reuse
        "refurb_yield": 0.30   # 30% Yield (70% Waste)
    },
    "B": {
        "name": "Industrial_Refurb",
        "reuse_limit": 0.20,   # 20% Reuse
        "refurb_yield": 0.85   # 85% Yield (15% Waste)
    },
    "C": {
        "name": "Consumer_Reuse",
        "reuse_limit": 0.60,   # 60% Reuse
        "refurb_yield": 0.50   # 50% Yield (50% Waste)
    }
}

# Number of steps for the Pareto Curve
NUM_STEPS = 10

def log(msg):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")

def solve_scenario_pareto(scenario_key, scenario_data):
    s_name = scenario_data["name"]
    reuse_lim = scenario_data["reuse_limit"]
    refurb_yld = scenario_data["refurb_yield"]
    
    log(f"--- STARTING SCENARIO {scenario_key}: {s_name} ---")
    log(f"    Params: Reuse Limit={reuse_lim*100}%, Refurb Yield={refurb_yld*100}%")

    # -----------------------------------------------------
    # LOAD DATA (Standard)
    # -----------------------------------------------------
    filename = "Germany_data_v2_1512.xlsx"
    xls = pd.ExcelFile(filename)
    
    # Sets
    df_sets = pd.read_excel(xls, '1. Sets')
    def get_set(df, col): return [x for x in df[col].dropna().unique()]
    
    P = get_set(df_sets, 'Plants (P)')
    C = get_set(df_sets, 'CustomerZones/Market (C)')
    O = get_set(df_sets, 'Collection Centers (O)')
    F = get_set(df_sets, 'Refurbish Centers (F)')
    L = get_set(df_sets, 'Landfills (L)')
    S = get_set(df_sets, 'Suppliers (S)')
    
    df_w_raw = pd.read_excel(xls, '7. Module Weights')
    K = [x for x in df_w_raw['Module_Type_ID'].dropna().unique()]

    # Parameters
    sheet_prod = '2. Production Costs' if '2. Production Costs' in xls.sheet_names else 'Prod'
    if 'Prod' not in xls.sheet_names and '2. Production Costs' not in xls.sheet_names:
         possible = [s for s in xls.sheet_names if "Prod" in s]
         if possible: sheet_prod = possible[0]
    PC = pd.read_excel(xls, sheet_prod).set_index('Plant_ID')['Production_Cost_per_KWp (PC_p)'].to_dict()

    df_ops = pd.read_excel(xls, '3. Operational Costs').set_index('Facility_ID')['Cost_per_Unit (CC_o/FC_f for KWp)']
    CC = {o: df_ops.get(o, 0) for o in O}
    FC = {f: df_ops.get(f, 0) for f in F}
    DC = {l: df_ops.get(l, 0) for l in L}

    df_fix = pd.read_excel(xls, '4. Fixed Costs').set_index('Facility_ID')['Fixed_Operational_Cost (Fix)']
    FixO = {o: df_fix.get(o, 0) for o in O}
    FixF = {f: df_fix.get(f, 0) for f in F} 

    Penalty = pd.read_excel(xls, "5. Penalty Costs").set_index("Module_Type_ID")["Penalty_Cost_per_KWp (Pen_k)"].to_dict()

    df_dem = pd.read_excel(xls, '6. Demand & Returns')
    DEM = {(r['Customer_Zone_ID'], r['Module_Type_ID']): r['Demand_KWp (DEM_ck)'] for _, r in df_dem.iterrows()}
    RET = {(r['Customer_Zone_ID'], r['Module_Type_ID']): r['Returns_KWp (RET_ck)'] for _, r in df_dem.iterrows()}

    df_w = pd.read_excel(xls, '7. Module Weights')
    omega = {r['Module_Type_ID']: float(str(r['Weight_kg_per_KWp (omega_k)']).replace(',','.')) for _, r in df_w.iterrows()}

    CAP = pd.read_excel(xls, "9. Capacities").set_index("Facility_ID")["Capacity_Value_kWp"].to_dict()

    df_rev = pd.read_excel(xls, "10. Revenues")
    Rev_reuse  = df_rev[df_rev["Revenue_Stream"]=="Reuse"].set_index("Item_ID")["Revenue_per_Unit (Rev)_€"].to_dict()
    Rev_refurb = df_rev[df_rev["Revenue_Stream"]=="Refurbish"].set_index("Item_ID")["Revenue_per_Unit (Rev)_€"].to_dict()

    df_trans = pd.read_excel(xls, "11. Transportation")
    dist_map = {(r["Origin_ID"], r["Destination_ID"]): r["Distance_km"] for _, r in df_trans.iterrows()}
    def DIST(a,b): return dist_map.get((a,b), 500)
    T_cost = df_trans['Cost_per_kg_km'].iloc[0]
    T_emit = df_trans['Emission_per_kg_km'].iloc[0]

    df_env = pd.read_excel(xls, "12. Environmental").set_index("Parameter_Name")["Value_kg_CO2e"]
    E_p, E_co, E_f, E_l = df_env.get("E_p", 580), df_env.get("E_o", 0.4), df_env.get("E_f", 1.2), df_env.get("E_l", 0.3)

    df_bom = pd.read_excel(xls, '13. Supplier_BOM')
    BOM = df_bom.set_index('Supplier_ID')['Qty_per_Module'].to_dict()
    Mat_Cost = df_bom.set_index('Supplier_ID')['Cost_per_Unit'].to_dict()
    Em_Supplier = df_bom.set_index('Supplier_ID')['Emission_per_kWp'].fillna(0).to_dict()

    # -----------------------------------------------------
    # OVERRIDE PARAMETERS
    # -----------------------------------------------------
    alpha = {f: refurb_yld for f in F} # Apply scenario yield to all F centers

    # -----------------------------------------------------
    # BUILD MODEL
    # -----------------------------------------------------
    m = Model(f"Pareto_{s_name}")
    m.setParam("OutputFlag", 0)

    # Variables
    X_pk = m.addVars(P, K, lb=0)
    X_pck = m.addVars(P, C, K, lb=0)
    Y_cok = m.addVars(C, O, K, lb=0)
    Y_ock = m.addVars(O, C, K, lb=0)
    Y_ofk = m.addVars(O, F, K, lb=0)
    Y_olk = m.addVars(O, L, K, lb=0)
    Y_fpk = m.addVars(F, P, K, lb=0)
    Y_flk = m.addVars(F, L, K, lb=0) # Refurb Waste Flow
    
    S_ck = m.addVars(C, K, lb=0)
    W_o = m.addVars(O, vtype=GRB.BINARY)
    W_f = m.addVars(F, vtype=GRB.BINARY)
    Z_sp = m.addVars(S, P, lb=0)

    # Constraints
    for p in P:
        for s in S: m.addConstr(Z_sp[s,p] == quicksum(X_pk[p,k] for k in K)*BOM[s])
    for c in C:
        for k in K: m.addConstr(quicksum(X_pck[p,c,k] for p in P) + quicksum(Y_ock[o,c,k] for o in O) + S_ck[c,k] == DEM.get((c,k),0))
    for c in C:
        for k in K: m.addConstr(quicksum(Y_cok[c,o,k] for o in O) == RET.get((c,k),0))
    for p in P:
        for k in K: m.addConstr(X_pk[p,k] + quicksum(Y_fpk[f,p,k] for f in F) == quicksum(X_pck[p,c,k] for c in C))

    # --- SENSITIVITY CONSTRAINTS ---
    # Collection Center Balance
    for o in O:
        for k in K:
            In  = quicksum(Y_cok[c,o,k] for c in C)
            Out = quicksum(Y_ock[o,c,k] for c in C) + quicksum(Y_ofk[o,f,k] for f in F) + quicksum(Y_olk[o,l,k] for l in L)
            m.addConstr(In == Out)
            
            # Reuse Limit (Scenario Parameter)
            m.addConstr(quicksum(Y_ock[o,c,k] for c in C) <= reuse_lim * In)

    # SCENARIO YIELD & WASTE GENERATION
    for f in F:
        for k in K:
            In_Refurb = quicksum(Y_ofk[o,f,k] for o in O)
            # Success
            m.addConstr(quicksum(Y_fpk[f,p,k] for p in P) == alpha[f] * In_Refurb)
            # Waste (Scenario Calculated)
            m.addConstr(quicksum(Y_flk[f,l,k] for l in L) == (1 - alpha[f]) * In_Refurb)

    # Capacities (UNIT FIXED: No Omega)
    for p in P: m.addConstr(quicksum(X_pk[p,k] for k in K) <= CAP.get(p,1e12))
    for o in O: m.addConstr(quicksum(Y_cok[c,o,k] for c in C for k in K) <= CAP.get(o,1e12)*W_o[o])
    for f in F: m.addConstr(quicksum(Y_ofk[o,f,k] for o in O for k in K) <= CAP.get(f,1e12)*W_f[f])

    # Objectives
    Expr_Cost = (
        quicksum(FixO[o]*W_o[o] for o in O) + quicksum(FixF[f]*W_f[f] for f in F) +
        quicksum(PC[p]*X_pk[p,k] for p in P for k in K) +
        quicksum(CC[o]*Y_cok[c,o,k] for c in C for o in O for k in K) +
        quicksum(FC[f]*Y_ofk[o,f,k] for o in O for f in F for k in K) +
        quicksum(DC[l]*Y_olk[o,l,k]*omega[k] for o in O for l in L for k in K) +
        # Refurb Waste Cost
        quicksum(DC[l]*Y_flk[f,l,k]*omega[k] for f in F for l in L for k in K) +
        
        quicksum(Mat_Cost[s]*Z_sp[s,p] for s in S for p in P) +
        quicksum(T_cost * DIST(p,c) * X_pck[p,c,k] * omega[k] for p in P for c in C for k in K) +
        quicksum(T_cost * DIST(c,o) * Y_cok[c,o,k] * omega[k] for c in C for o in O for k in K) +
        quicksum(T_cost * DIST(o,c) * Y_ock[o,c,k] * omega[k] for o in O for c in C for k in K) +
        quicksum(T_cost * DIST(o,f) * Y_ofk[o,f,k] * omega[k] for o in O for f in F for k in K) +
        quicksum(T_cost * DIST(o,l) * Y_olk[o,l,k] * omega[k] for o in O for l in L for k in K) +
        
        # Refurb Waste Transport
        quicksum(T_cost * 50 * Y_flk[f,l,k] * omega[k] for f in F for l in L for k in K) +

        quicksum(T_cost * DIST(f,p) * Y_fpk[f,p,k] * omega[k] for f in F for p in P for k in K) +
        quicksum(Penalty[k]*S_ck[c,k] for c in C for k in K) - 
        (quicksum(Rev_reuse.get(k,0)*Y_ock[o,c,k] for o in O for c in C for k in K) +
         quicksum(Rev_refurb.get(k,0)*Y_fpk[f,p,k] for f in F for p in P for k in K))
    )
    
    Expr_Env = (
        quicksum(E_p  * X_pk[p,k] for p in P for k in K) +
        quicksum(E_co * Y_cok[c,o,k] for c in C for o in O for k in K) +
        quicksum(E_f  * Y_ofk[o,f,k] for o in O for f in F for k in K) +
        quicksum(E_l  * Y_olk[o,l,k] * omega[k] for o in O for l in L for k in K) +
        # Refurb Waste Emissions
        quicksum(E_l  * Y_flk[f,l,k] * omega[k] for f in F for l in L for k in K) +

        quicksum(T_emit * DIST(p,c) * X_pck[p,c,k] * omega[k] for p in P for c in C for k in K) +
        quicksum(T_emit * DIST(c,o) * Y_cok[c,o,k] * omega[k] for c in C for o in O for k in K) +
        quicksum(T_emit * DIST(o,c) * Y_ock[o,c,k] * omega[k] for o in O for c in C for k in K) +
        quicksum(T_emit * DIST(o,f) * Y_ofk[o,f,k] * omega[k] for o in O for f in F for k in K) +
        quicksum(T_emit * DIST(o,l) * Y_olk[o,l,k] * omega[k] for o in O for l in L for k in K) +
        
        # Refurb Waste Transport Emissions
        quicksum(T_emit * 50 * Y_flk[f,l,k] * omega[k] for f in F for l in L for k in K) +

        quicksum(T_emit * DIST(f,p) * Y_fpk[f,p,k] * omega[k] for f in F for p in P for k in K)
    )

    # -----------------------------------------------------
    # 1. COMPUTE EXTREMES (PAYOFF TABLE)
    # -----------------------------------------------------
    # Min Cost
    m.setObjective(Expr_Cost, GRB.MINIMIZE)
    m.optimize()
    if m.Status != GRB.OPTIMAL:
        log(f"  [Error] Infeasible model for {s_name} (Cost Min)")
        return
    
    Zcost_min = m.ObjVal
    Zenv_at_costmin = Expr_Env.getValue()
    
    # Min Env
    m.setObjective(Expr_Env, GRB.MINIMIZE)
    m.optimize()
    if m.Status != GRB.OPTIMAL:
        log(f"  [Error] Infeasible model for {s_name} (Env Min)")
        return
    
    Zenv_min = m.ObjVal
    Zcost_at_envmin = Expr_Cost.getValue()
    
    log(f"    Payoff Table: Cost Range=[{Zcost_min:,.0f}, {Zcost_at_envmin:,.0f}]")
    log(f"                  Env Range =[{Zenv_min:,.0f}, {Zenv_at_costmin:,.0f}]")

    # -----------------------------------------------------
    # 2. GENERATE CURVE A (Min Cost, Vary Env)
    # -----------------------------------------------------
    eps_env_values = np.linspace(Zenv_min, Zenv_at_costmin, NUM_STEPS)
    results_A = []
    
    for eps in eps_env_values:
        Con_eps = m.addConstr(Expr_Env <= eps)
        m.setObjective(Expr_Cost, GRB.MINIMIZE)
        m.optimize()
        
        if m.Status == GRB.OPTIMAL:
            results_A.append((eps, m.ObjVal, Expr_Env.getValue()))
        m.remove(Con_eps)
        m.update()
        
    df_A = pd.DataFrame(results_A, columns=["epsilon_env", "cost", "env"])
    file_A = f"Pareto_{s_name}_CostMin.csv"
    df_A.to_csv(file_A, index=False)
    log(f"    Saved Curve A to {file_A}")

    # -----------------------------------------------------
    # 3. GENERATE CURVE B (Min Env, Vary Cost)
    # -----------------------------------------------------
    eps_cost_values = np.linspace(Zcost_min, Zcost_at_envmin, NUM_STEPS)
    results_B = []
    
    for eps in eps_cost_values:
        Con_eps = m.addConstr(Expr_Cost <= eps)
        m.setObjective(Expr_Env, GRB.MINIMIZE)
        m.optimize()
        
        if m.Status == GRB.OPTIMAL:
            results_B.append((eps, Expr_Cost.getValue(), m.ObjVal))
        m.remove(Con_eps)
        m.update()
        
    df_B = pd.DataFrame(results_B, columns=["epsilon_cost", "cost", "env"])
    file_B = f"Pareto_{s_name}_EnvMin.csv"
    df_B.to_csv(file_B, index=False)
    log(f"    Saved Curve B to {file_B}")

# ==========================================
# MAIN EXECUTION LOOP
# ==========================================
if __name__ == "__main__":
    print("\n=== STARTING MULTI-SCENARIO PARETO GENERATION ===\n")
    
    for key, data in scenarios.items():
        solve_scenario_pareto(key, data)
        
    print("\n=== ALL SCENARIOS COMPLETED ===")
    print("Check your folder for the 6 CSV files.")
