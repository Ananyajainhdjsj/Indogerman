from gurobipy import *

def solve_circular_supply_chain_model(epsilon_limit, minimize_emissions_only=False):
    # --- 1. SETS ---
    P = ['P1']
    # Market Zones (Combining Distributors & Customers)
    C = ['C1', 'C2']
    O = ['O1']
    F = ['F1']
    R = ['R1']
    L = ['L1']
    S = ['S1']
    K = ['Monocrystalline']
    M = ['Glass', 'Aluminum', 'Silicon', 'Plastic', 'Copper']

    # --- 2. PARAMETERS (Values in Euros €) ---

    # Operational Costs (per KWp or kg)
    PC = {p: 140.0 for p in P}      # Production Cost (€/KWp)
    CC = {o: 8.0 for o in O}        # Collection Cost (€/KWp)
    FC = {f: 25.0 for f in F}       # Refurbishing Cost (€/KWp)
    RC = {r: 0.60 for r in R}       # Recycling Cost (€/kg) - processing cost
    DC = {l: 0.15 for l in L}       # Disposal/Landfill Cost (€/kg)

    # Transport Cost
    T = 0.004                       # Transport Cost (€ per kg-km)

    # Penalty Cost (Shortage)
    Penalty = 20000.0                # Penalty for unmet demand (€/KWp)

    # Fixed Costs (Opening Facilities)
    FixO = {o: 15000.0 for o in O}
    FixF = {f: 25000.0 for f in F}
    FixR = {r: 30000.0 for r in R}

    # Demand & Returns (KWp)
    DEM = {(c, k): 1000.0 for c in C for k in K}
    RET = {(c, k): 800.0 for c in C for k in K}

    # Technical Factors
    omega = {'Monocrystalline': 11.0}   # Weight (kg/KWp)
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

    # Emissions Factors (kg CO2e)
    E_p = {p: 450.0 for p in P}     # Production
    E_o = {o: 5.0 for o in O}       # Collection
    E_f = {f: 30.0 for f in F}      # Refurbishing
    E_r = {r: 1.5 for r in R}       # Recycling (per kg)
    E_l = {l: 0.5 for l in L}       # Disposal (per kg)
    E_T = 0.00006                   # Transport (per kg-km)

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

    m.update()

    # --- OBJECTIVE ---
    Fixed_Cost = (sum(FixO[o]*W_o[o] for o in O) + sum(FixF[f]*W_f[f] for f in F) + sum(FixR[r]*W_r[r] for r in R))

    Op_Cost = (
        sum(PC[p] * X_pk[p, k] for p in P for k in K) +
        sum(CC[o] * Y_cok[c, o, k] for c in C for o in O for k in K) +
        sum(FC[f] * Y_ofk[o, f, k] for o in O for f in F for k in K) +
        sum(RC[r] * Y_ork[o, r, k] * omega[k] for o in O for r in R for k in K) +
        sum(DC[l] * Y_olk[o, l, k] * omega[k] for o in O for l in L for k in K)
    )

    Transport_Cost = (
        sum(T * get_dist(p, c) * X_pck[p, c, k] * omega[k] for p in P for c in C for k in K) +
        sum(T * get_dist(c, o) * Y_cok[c, o, k] * omega[k] for c in C for o in O for k in K) +
        sum(T * get_dist(o, c) * Y_ock[o, c, k] * omega[k] for o in O for c in C for k in K) +
        sum(T * get_dist(o, f) * Y_ofk[o, f, k] * omega[k] for o in O for f in F for k in K) +
        sum(T * get_dist(o, r) * Y_ork[o, r, k] * omega[k] for o in O for r in R for k in K) +
        sum(T * get_dist(o, l) * Y_olk[o, l, k] * omega[k] for o in O for l in L for k in K) +
        sum(T * get_dist(f, p) * Y_fpk[f, p, k] * omega[k] for f in F for p in P for k in K) +
        sum(T * get_dist(r, s) * Z_rsm[r, s, mat] for r in R for s in S for mat in M)
    )

    Revenue = (
        sum(Rev_reuse[k] * Y_ock[o, c, k] for o in O for c in C for k in K) +
        sum(Rev_refurb[k] * Y_fpk[f, p, k] for f in F for p in P for k in K) +
        sum(Rev_recycle[mat] * Z_rsm[r, s, mat] for r in R for s in S for mat in M)
    )

    Shortage_Cost = sum(Penalty * S_ck[c, k] for c in C for k in K)

    Z_Cost = Fixed_Cost + Op_Cost + Transport_Cost + Shortage_Cost - Revenue

    # --- EMISSIONS (INCLUDE ALL MAJOR SOURCES) ---
    Env_Total = 0

    # Production emissions (kg CO2e)
    Env_Total += sum(E_p[p] * X_pk[p, k] for p in P for k in K)

    # Collection emissions (per KWp moved through collection)
    Env_Total += sum(E_o[o] * Y_cok[c, o, k] for c in C for o in O for k in K)

    # Refurbishing emissions (per KWp refurbished)
    Env_Total += sum(E_f[f] * Y_ofk[o, f, k] for o in O for f in F for k in K)

    # Recycling emissions (per kg recycled -> multiply by weight omega[k])
    Env_Total += sum(E_r[r] * Y_ork[o, r, k] * omega[k] for o in O for r in R for k in K)

    # Landfill / Disposal emissions (per kg)
    Env_Total += sum(E_l[l] * Y_olk[o, l, k] * omega[k] for o in O for l in L for k in K)

    # Transport emissions (applies to material flows scaled by weight)
    Env_Total += sum(E_T * get_dist(p, c) * X_pck[p, c, k] * omega[k] for p in P for c in C for k in K)
    Env_Total += sum(E_T * get_dist(c, o) * Y_cok[c, o, k] * omega[k] for c in C for o in O for k in K)
    Env_Total += sum(E_T * get_dist(o, c) * Y_ock[o, c, k] * omega[k] for o in O for c in C for k in K)
    Env_Total += sum(E_T * get_dist(o, f) * Y_ofk[o, f, k] * omega[k] for o in O for f in F for k in K)
    Env_Total += sum(E_T * get_dist(o, r) * Y_ork[o, r, k] * omega[k] for o in O for r in R for k in K)
    Env_Total += sum(E_T * get_dist(o, l) * Y_olk[o, l, k] * omega[k] for o in O for l in L for k in K)
    Env_Total += sum(E_T * get_dist(f, p) * Y_fpk[f, p, k] * omega[k] for f in F for p in P for k in K)
    # transport for material flows from recycling centers
    Env_Total += sum(E_T * get_dist(r, s) * Z_rsm[r, s, mat] for r in R for s in S for mat in M)

    # Objective Setting
    if minimize_emissions_only:
        m.setObjective(Env_Total, GRB.MINIMIZE)
    else:
        m.setObjective(Z_Cost, GRB.MINIMIZE)
        # Add environmental limit constraint (user provided)
        m.addConstr(Env_Total <= epsilon_limit, "Env_Limit")

    # --- CONSTRAINTS ---
    # 1. Demand
    for c in C:
        for k in K:
            m.addConstr(sum(X_pck[p, c, k] for p in P) + sum(Y_ock[o, c, k] for o in O) + S_ck[c, k] == DEM[c, k])

    # 2. Returns
    for c in C:
        for k in K:
            m.addConstr(sum(Y_cok[c, o, k] for o in O) <= RET[c, k])

    # 3. Flow Balance (Collection)
    for o in O:
        for k in K:
            Total_In = sum(Y_cok[c, o, k] for c in C)
            Total_Out = sum(Y_ock[o, c, k] for c in C) + sum(Y_ofk[o, f, k] for f in F) + sum(Y_ork[o, r, k] for r in R) + sum(Y_olk[o, l, k] for l in L)
            m.addConstr(Total_In == Total_Out)

            # Quality Constraints
            m.addConstr(sum(Y_ock[o, c, k] for c in C) <= Quality_Mix['Reuse_Cap'] * Total_In)
            m.addConstr(sum(Y_ofk[o, f, k] for f in F) <= Quality_Mix['Refurb_Cap'] * Total_In)

    # 4. Plant Balance
    for p in P:
        for k in K:
            m.addConstr(X_pk[p, k] + sum(Y_fpk[f, p, k] for f in F) == sum(X_pck[p, c, k] for c in C))

    # Yields
    for f in F:
        for k in K:
            m.addConstr(sum(Y_fpk[f, p, k] for p in P) == alpha[f] * sum(Y_ofk[o, f, k] for o in O))

    for r in R:
        for mat in M:
            m.addConstr(sum(Z_rsm[r, s, mat] for s in S) == beta[r] * sum(Y_ork[o, r, k] * gamma[k, mat] for o in O for k in K))

    # Capacities
    for o in O: m.addConstr(sum(Y_cok[c, o, k] for c in C for k in K) * omega['Monocrystalline'] <= CAP_o[o] * W_o[o])
    for f in F: m.addConstr(sum(Y_ofk[o, f, k] for o in O for k in K) * omega['Monocrystalline'] <= CAP_f[f] * W_f[f])
    for r in R: m.addConstr(sum(Y_ork[o, r, k] * omega['Monocrystalline'] for o in O for k in K) <= CAP_r[r] * W_r[r])

    m.optimize()

    # --- OUTPUT ---
    if m.status == GRB.OPTIMAL:
        # Detailed Print for Single Run
        if not minimize_emissions_only: # Only print trace for normal runs
            print("\n" + "="*60)
            print(f"   OPTIMAL SOLUTION FOUND (EUR)")
            print(f"   Total Cost: €{m.objVal:,.2f}")
            print("="*60)
            # ... (Add your trace print code here if you want to see it every time) ...

        cost_val = Z_Cost.getValue()
        env_val = Env_Total.getValue()
        return "Optimal", cost_val, env_val
    else:
        if m.status == GRB.INFEASIBLE:
            return "Infeasible", None, None
        return "Other", None, None

if __name__ == '__main__':
    # quick sanity run
    print(solve_circular_supply_chain_model(50000))
