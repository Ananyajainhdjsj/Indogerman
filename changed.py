from gurobipy import *

def solve_circular_supply_chain_model(epsilon_limit, minimize_emissions_only=False):
    # --- 1. SETS ---
    P = ['P1']       # Production Plants
    # Market Zones (Combining Distributors & Customers)
    C = ['C1', 'C2']    #Customer Zones  
    O = ['O1']            # Collection Centers
    F = ['F1']            # Refurbishing Facilities
    R = ['R1']            # Recycling Facilities
    L = ['L1']            # Landfill Sites
    S = ['S1']            # Suppliers
    K = ['Monocrystalline'] #type of PV module
    M = ['Glass', 'Aluminum', 'Silicon', 'Plastic', 'Copper'] 

    # --- 2. PARAMETERS (Values in Euros €) ---
    
    # Operational Costs (per KWp or kg)
    PC = {p: 126.0 for p in P}      # Production Cost (€/KWp)
    CC = {o: 8.0 for o in O}        # Collection Cost (€/KWp)
    FC = {f: 25.0 for f in F}       # Refurbishing Cost (€/KWp)
    RC = {r: 0.60 for r in R}       # Recycling Cost (€/kg) - processing cost
    DC = {l: 0.15 for l in L}       # Disposal/Landfill Cost (€/kg)
    
    # Transport Cost
    T = 0.0001                       # Transport Cost (€ per kg-km)
    
    # Penalty Cost (Shortage)
    Penalty = 500.0                 # Penalty for unmet demand (€/KWp)

    # Fixed Costs (Opening Facilities)
    FixO = {o: 15000.0 for o in O}    
    FixF = {f: 25000.0 for f in F}     
    FixR = {r: 30000.0 for r in R}     

    # Demand & Returns (KWp)
    DEM = {(c, k):80000.0 for c in C for k in K}  
    RET = {(c, k): 80000.0 for c in C for k in K} 

    # Technical Factors
    omega = {'Monocrystalline': 49.3}   # Weight (kg/KWp)
    alpha = {f: 0.90 for f in F}        # Refurbish Yield
    beta = {r: 0.95 for r in R}         # Recycling Efficiency

    # Quality Mix (Constraints on flow)
    Quality_Mix = {
        'Reuse_Cap': 0.20,   # Max 20% of returns can be reused directly
        'Refurb_Cap': 0.40,  # Max 40% can be refurbished
    }

    # Bill of Materials (kg per KWp)
    gamma = {
        ('Monocrystalline', 'Glass'): 8.0, 
        ('Monocrystalline', 'Aluminum'): 1.5, 
        ('Monocrystalline', 'Silicon'): 0.5, 
        ('Monocrystalline', 'Plastic'): 0.8, 
        ('Monocrystalline', 'Copper'): 0.2
    }

    # Capacities (KWp or kg)
    CAP_p = {p: 10000.0 for p in P}     
    CAP_o = {o: 100000.0 for o in O}  
    CAP_f = {f: 50000.0 for f in F}      
    CAP_r = {r: 50000.0 for r in R}     

    # Revenues (€)
    Rev_reuse = {'Monocrystalline': 90.0}   # Selling used module (€/KWp)
    Rev_refurb = {'Monocrystalline': 110.0} # Selling refurbished module (€/KWp)
    
    # Revenue from Materials (€/kg)
    Rev_recycle = {
        'Glass': 0.08, 
        'Aluminum': 1.80, 
        'Silicon': 12.0, 
        'Plastic': 0.15, 
        'Copper': 6.50
    }

    # Distance (km)
    DIST = 50.0 
    def get_dist(i, j): return DIST

    # Emissions Factors (kg CO2e) values from excel
    E_p = {p: 580.0 for p in P}     # Production
    E_o = {o: 10.0 for o in O}       # Collection
    E_f = {f: 150.0 for f in F}      # Refurbishing
    E_r = {r: 60 for r in R}       # Recycling (per kg)
    E_l = {l: 5 for l in L}       # Disposal (per kg)
    E_T =0.1                  # Transport (per kg-km)

    # --- 3. MODEL ---
    m = Model("Circular_Supply_Chain_Euro")
    m.setParam('OutputFlag', 0) 

    # Variables
    X_pk = m.addVars(P, K, name="X_pk", vtype=GRB.CONTINUOUS, lb=0) 
    X_pck = m.addVars(P, C, K, name="X_pck", vtype=GRB.CONTINUOUS, lb=0) 
    Y_cok = m.addVars(C, O, K, name="Y_cok", vtype=GRB.CONTINUOUS, lb=0) 
    Y_ock = m.addVars(O, C, K, name="Y_ock", vtype=GRB.CONTINUOUS, lb=0) 
    Y_ofk = m.addVars(O, F, K, name="Y_ofk", vtype=GRB.CONTINUOUS, lb=0) 
    Y_ork = m.addVars(O, R, K, name="Y_ork", vtype=GRB.CONTINUOUS, lb=0) 
    Y_olk = m.addVars(O, L, K, name="Y_olk", vtype=GRB.CONTINUOUS, lb=0) 
    Y_fpk = m.addVars(F, P, K, name="Y_fpk", vtype=GRB.CONTINUOUS, lb=0) 
    S_ck = m.addVars(C, K, name="S_ck", vtype=GRB.CONTINUOUS, lb=0) 
    Z_rsm = m.addVars(R, S, M, name="Z_rsm", vtype=GRB.CONTINUOUS, lb=0) 
    W_o = m.addVars(O, vtype=GRB.BINARY)
    W_f = m.addVars(F, vtype=GRB.BINARY)
    W_r = m.addVars(R, vtype=GRB.BINARY)

    # --- ARC-LEVEL ROUTING VARIABLES (per customer->collection batch) ---
    Y_c_o_c2k = m.addVars(C, O, C, K, name="Y_c_o_c2k", vtype=GRB.CONTINUOUS, lb=0)  # c -> o -> reuse -> c2
    Y_c_o_fk  = m.addVars(C, O, F, K, name="Y_c_o_fk",  vtype=GRB.CONTINUOUS, lb=0)     # c -> o -> f
    Y_c_o_rk  = m.addVars(C, O, R, K, name="Y_c_o_rk",  vtype=GRB.CONTINUOUS, lb=0)     # c -> o -> r
    Y_c_o_lk  = m.addVars(C, O, L, K, name="Y_c_o_lk",  vtype=GRB.CONTINUOUS, lb=0)     # c -> o -> l

    m.update()

    # --- OBJECTIVE ---
    Fixed_Cost = (quicksum(FixO[o]*W_o[o] for o in O) + quicksum(FixF[f]*W_f[f] for f in F) + sum(FixR[r]*W_r[r] for r in R))
    
    Op_Cost = (
        quicksum(PC[p] * X_pk[p, k] for p in P for k in K) + 
        quicksum(CC[o] * Y_cok[c, o, k] for c in C for o in O for k in K) +
        quicksum(FC[f] * Y_ofk[o, f, k] for o in O for f in F for k in K) +
        quicksum(RC[r] * Y_ork[o, r, k] * omega[k] for o in O for r in R for k in K) + 
        quicksum(DC[l] * Y_olk[o, l, k] * omega[k] for o in O for l in L for k in K)
    )
    
    Transport_Cost = (
        quicksum(T * get_dist(p, c) * X_pck[p, c, k] * omega[k] for p in P for c in C for k in K) +
        quicksum(T * get_dist(c, o) * Y_cok[c, o, k] * omega[k] for c in C for o in O for k in K) +
        quicksum(T * get_dist(o, c) * Y_ock[o, c, k] * omega[k] for o in O for c in C for k in K) + 
        quicksum(T * get_dist(o, f) * Y_ofk[o, f, k] * omega[k] for o in O for f in F for k in K) +
        quicksum(T * get_dist(o, r) * Y_ork[o, r, k] * omega[k] for o in O for r in R for k in K) +
        quicksum(T * get_dist(o, l) * Y_olk[o, l, k] * omega[k] for o in O for l in L for k in K) +
        quicksum(T * get_dist(f, p) * Y_fpk[f, p, k] * omega[k] for f in F for p in P for k in K) +
        quicksum(T * get_dist(r, s) * Z_rsm[r, s, mat] for r in R for s in S for mat in M)
    )
    
    Revenue = (
        quicksum(Rev_reuse[k] * Y_ock[o, c, k] for o in O for c in C for k in K) +
        quicksum(Rev_refurb[k] * Y_fpk[f, p, k] for f in F for p in P for k in K) +
        quicksum(Rev_recycle[mat] * Z_rsm[r, s, mat] for r in R for s in S for mat in M)
    )
    
    Shortage_Cost = quicksum(Penalty * S_ck[c, k] for c in C for k in K)
    
    Z_Cost = Fixed_Cost + Op_Cost + Transport_Cost + Shortage_Cost - Revenue

    # Emissions expression
    Env_Total = quicksum(E_p[p] * X_pk[p, k] for p in P for k in K)

    # Objective Setting
    if minimize_emissions_only:
        m.setObjective(Env_Total, GRB.MINIMIZE)
    else:
        m.setObjective(Z_Cost, GRB.MINIMIZE)
        m.addConstr(Env_Total <= epsilon_limit, "Env_Limit")

    # --- CONSTRAINTS ---
    # 1. Demand
    for c in C:
        for k in K:
            m.addConstr(quicksum(X_pck[p, c, k] for p in P) + quicksum(Y_ock[o, c, k] for o in O) + S_ck[c, k] == DEM[c, k])

    # 2. Returns
    for c in C:
        for k in K:
            m.addConstr(quicksum(Y_cok[c, o, k] for o in O) <= RET[c, k])

    # --- ARC-LEVEL LINKING CONSTRAINTS ---
    # Link per-customer collected batches to the routed arc variables and
    # link aggregated outbound flows to the per-arc variables.
    for c_src in C:
        for o in O:
            for k in K:
                m.addConstr(
                    Y_cok[c_src, o, k]
                    == quicksum(Y_c_o_c2k[c_src, o, c_dest, k] for c_dest in C)
                    + quicksum(Y_c_o_fk[c_src, o, f, k] for f in F)
                    + quicksum(Y_c_o_rk[c_src, o, r, k] for r in R)
                    + quicksum(Y_c_o_lk[c_src, o, l, k] for l in L)
                )

    for o in O:
        for c_dest in C:
            for k in K:
                m.addConstr(Y_ock[o, c_dest, k] == quicksum(Y_c_o_c2k[c_src, o, c_dest, k] for c_src in C))
        for f in F:
            for k in K:
                m.addConstr(Y_ofk[o, f, k] == quicksum(Y_c_o_fk[c_src, o, f, k] for c_src in C))
        for r in R:
            for k in K:
                m.addConstr(Y_ork[o, r, k] == quicksum(Y_c_o_rk[c_src, o, r, k] for c_src in C))
        for l in L:
            for k in K:
                m.addConstr(Y_olk[o, l, k] == quicksum(Y_c_o_lk[c_src, o, l, k] for c_src in C))

    # 3. Flow Balance (Collection)
    for o in O:
        for k in K:
            Total_In = quicksum(Y_cok[c, o, k] for c in C)
            Total_Out = quicksum(Y_ock[o, c, k] for c in C) + quicksum(Y_ofk[o, f, k] for f in F) + quicksum(Y_ork[o, r, k] for r in R) + quicksum(Y_olk[o, l, k] for l in L)
            m.addConstr(Total_In == Total_Out)

            # Quality Constraints
            m.addConstr(quicksum(Y_ock[o, c, k] for c in C) <= Quality_Mix['Reuse_Cap'] * Total_In)
            m.addConstr(quicksum(Y_ofk[o, f, k] for f in F) <= Quality_Mix['Refurb_Cap'] * Total_In)

    # 4. Plant Balance
    for p in P:
        for k in K:
            m.addConstr(X_pk[p, k] + quicksum(Y_fpk[f, p, k] for f in F) == quicksum(X_pck[p, c, k] for c in C))

    # Yields
    for f in F:
        for k in K:
            m.addConstr(quicksum(Y_fpk[f, p, k] for p in P) == alpha[f] * quicksum(Y_ofk[o, f, k] for o in O))
    
    for r in R:
        for mat in M:
            m.addConstr(quicksum(Z_rsm[r, s, mat] for s in S) == beta[r] * quicksum(Y_ork[o, r, k] * gamma[k, mat] for o in O for k in K))
    # Capacities
    for o in O: m.addConstr(quicksum(Y_cok[c, o, k] for c in C for k in K) * omega['Monocrystalline'] <= CAP_o[o] * W_o[o]) 
    for f in F: m.addConstr(quicksum(Y_ofk[o, f, k] for o in O for k in K) * omega['Monocrystalline'] <= CAP_f[f] * W_f[f])
    for r in R: m.addConstr(quicksum(Y_ork[o, r, k] * omega['Monocrystalline'] for o in O for k in K) <= CAP_r[r] * W_r[r])
    m.optimize()

    # --- OUTPUT ---
    if m.status == GRB.OPTIMAL:
        cost_val = Z_Cost.getValue()
        env_val = Env_Total.getValue()

        # Detailed Print for Single Run
        if not minimize_emissions_only:  # Only print trace for normal runs
            print("\n" + "="*60)
            print(f"   OPTIMAL SOLUTION FOUND (EUR)")
            print(f"   Total Cost: €{m.objVal:,.2f}")
            print("="*60)

            tol = 1e-6
            print('\n=== CUSTOMER RETURNS (c → o) ===')
            for c in C:
                for o in O:
                    val = sum(Y_cok[c, o, k].X for k in K)
                    print(f"{c} → {o}: {val:.1f}")

            print('\n=== ARC-LEVEL ROUTING (c → o → destination) ===')
            for c_src in C:
                for o in O:
                    for k in K:
                        for c_dest in C:
                            v = Y_c_o_c2k[c_src, o, c_dest, k].X
                            if v > tol:
                                print(f"{c_src} → {o} → Reuse → {c_dest}: {v:.1f}")
                        for f in F:
                            v = Y_c_o_fk[c_src, o, f, k].X
                            if v > tol:
                                print(f"{c_src} → {o} → Refurb → {f}: {v:.1f}")
                        for r in R:
                            v = Y_c_o_rk[c_src, o, r, k].X
                            if v > tol:
                                print(f"{c_src} → {o} → Recycle → {r}: {v:.1f}")
                        for l in L:
                            v = Y_c_o_lk[c_src, o, l, k].X
                            if v > tol:
                                print(f"{c_src} → {o} → Landfill → {l}: {v:.1f}")

            print('\n=== COLLECTION CENTER AGGREGATE FLOWS (O → ...) ===')
            for o in O:
                for c_dest in C:
                    v = sum(Y_c_o_c2k[c_src, o, c_dest, k].X for c_src in C for k in K)
                    if v > tol:
                        print(f"Reuse: {o} → {c_dest}: {v:.1f}")
                for f in F:
                    v = sum(Y_c_o_fk[c_src, o, f, k].X for c_src in C for k in K)
                    if v > tol:
                        print(f"Refurb: {o} → {f}: {v:.1f}")
                for r in R:
                    v = sum(Y_c_o_rk[c_src, o, r, k].X for c_src in C for k in K)
                    if v > tol:
                        print(f"Recycle: {o} → {r}: {v:.1f}")
                for l in L:
                    v = sum(Y_c_o_lk[c_src, o, l, k].X for c_src in C for k in K)
                    if v > tol:
                        print(f"Landfill: {o} → {l}: {v:.1f}")

            print('\n=== REFURB → PLANT ===')
            for f in F:
                for p in P:
                    v = sum(Y_fpk[f, p, k].X for k in K)
                    if v > tol:
                        print(f"{f} → {p}: {v:.1f}")

            print('\n=== PRODUCTION ===')
            for p in P:
                prod = sum(X_pk[p, k].X for k in K)
                print(f"{p} Production: {prod:.1f}")
                for c in C:
                    shipped = sum(X_pck[p, c, k].X for k in K)
                    if shipped > tol:
                        print(f"{p} → {c}: {shipped:.1f}")

            print('\n=== SHORTAGE ===')
            for c in C:
                for k in K:
                    sh = S_ck[c, k].X
                    print(f"{c} shortage: {sh:.1f}")

            print('\n=== OBJECTIVE ===')
            print(f"Total Cost: €{cost_val:,.2f}")
            print(f"Total Emissions: {env_val:,.2f} kg CO2e")

        return "Optimal", cost_val, env_val
    else:
        if m.status == GRB.INFEASIBLE:
            return "Infeasible", None, None
        return "Other", None, None

if __name__ == '__main__':
    solve_circular_supply_chain_model(50000)