from gurobipy import *

def solve_circular_supply_chain_model(epsilon_limit):
    """
    Implements and solves the Multi-Objective Circular Supply Chain model 
    using the epsilon-Constraint method in Gurobi.
    
    The objective is to Min Z_Cost subject to Z_Env <= epsilon_limit.
    
    Args:
        z_env<=epsilon_limit
    """

    # --- 1. SETS (Indices) ---
  
    P = ['P1', 'P2']      # Production Plants 2 plants
    D = ['D1', 'D2']      # Distributors
    C = ['C1', 'C2']      # Customer Zones
    O = ['O1', 'O2']      # Collection Centers
    F = ['F1']            # Refurbish Centers
    R = ['R1']            # Recycling Centers
    L = ['L1']            # Landfills
    K = ['TypeA', 'TypeB'] # Module Types say si based and glass based for 2 countries
    S = ['S1']            # Suppliers of Recovered Material (Sales Point for Z)

    # --- 2. PLACEHOLDER PARAMETERS 
    PC = {p: 100 for p in P}        # Production cost per KWp at plant p 
    CC = {o: 10 for o in O}         # Collection cost per KWp at center o 
    FC = {f: 20 for f in F}         # Refurbishing cost per KWp at center f 
    RC = {r: 0.7 for r in R}        # Recycling cost per kg at center r 
    DC = {l: 0.1 for l in L}        # Disposal cost per kg at landfill l 
    T = 0.01                        # Transportation cost per kg-km 

    # 2.2 Fixed Costs f
    FixO = {o: 0 for o in O}    # Fixed cost to open collection center o   
    FixF = {f: 0 for f in F}     # Fixed cost to open refurbish center f   
    FixR = {r: 0 for r in R}     # Fixed cost to open recycling center r   

    # 2.3 Demand & Returns  
    # neeche its a dictionary for demand that comes with combo of c and k.500 value we assign to every (c,k) pair
   #its like (c1/c2,'type a/b'):500,
   
    DEM = {(c, k): 500 for c in C for k in K}  # Demand for modules of type k in customer zone c (in KWp)  
    RET = {(c, k): 400 for c in C for k in K}  # Quantity of returned modules of type k from zone c (in KWp)   22]

    # 2.4 Factors  
    omega = {k: 15 for k in K}                 # Weight  per KWp of module type k   
    alpha = {f: 0.90 for f in F}               # Yield rate for refurbishing   
    beta = {r: 0.83 for r in R}                # Yield rate for recycling   

    # 2.5 Capacities   
    CAP_p = {p: 1000 for p in P}     # Production Capacity (KWp)   
    CAP_o = {o: 500 for o in O}      # Collection Capacity (KWp)
    CAP_f = {f: 400 for f in F}      # Refurbish Capacity (KWp)
    CAP_r = {r: 3000 for r in R}     # Recycling Capacity (kg)

    # Revenues 
    Rev_reuse = 90
    Rev_refurb = 95
    Rev_recycle = 1.0

    # Emissions Parameters 
    E_p = {p: 5 for p in P}          # Production Emissions (kg CO2/KWp)
    E_o = {o: 0.5 for o in O}        # Collection Emissions (kg CO2/KWp)
    E_f = {f: 1.0 for f in F}        # Refurbishing Emissions (kg CO2/KWp)
    E_r = {r: 0.1 for r in R}        # Recycling Emissions (kg CO2/kg)
    E_l = {l: 0.2 for l in L}        # Disposal Emissions (kg CO2/kg)
    E_T = 0.001                      # Transportation Emissions (kg CO2/kg-km)

    # Distances  
    DIST = 275
    def get_dist(i, j): return DIST# distance assumed b/w all facility pairs

    # --- 3. MODEL AND DECISION VARIABLES ---
    m = Model("Circular Supply Chain PV Epsilon Constraint")

    # 1 Decision Variables 
    # X_...: Quantity of new modules (in KWp)  
    X_pdk = m.addVars(P, D, K, name="X_pdk", vtype=GRB.CONTINUOUS, lb=0) # Plant to Distributor
    X_dck = m.addVars(D, C, K, name="X_dck", vtype=GRB.CONTINUOUS, lb=0) # Distributor to Customer

    # Y_...: Quantity of used/refurbished modules (in KWp) reverse logistics ]
    Y_cok = m.addVars(C, O, K, name="Y_cok", vtype=GRB.CONTINUOUS, lb=0) # Customer to Collection how many modules of k type go from c customer to collection centre o
    Y_odk = m.addVars(O, D, K, name="Y_odk", vtype=GRB.CONTINUOUS, lb=0) # Collection to Distributor (Direct Reuse)
    Y_ofk = m.addVars(O, F, K, name="Y_ofk", vtype=GRB.CONTINUOUS, lb=0) # Collection to Refurbish
    Y_ork = m.addVars(O, R, K, name="Y_ork", vtype=GRB.CONTINUOUS, lb=0) # Collection to Recycle
    Y_olk = m.addVars(O, L, K, name="Y_olk", vtype=GRB.CONTINUOUS, lb=0) # Collection to Landfill
    Y_fpk = m.addVars(F, P, K, name="Y_fpk", vtype=GRB.CONTINUOUS, lb=0) # Refurbish to Plant (Material-wise)
    Y_dck_prime = m.addVars(D, C, K, name="Y_dck_prime", vtype=GRB.CONTINUOUS, lb=0) # Distributor to Customer (Reuse/Refurbished)

    # Z_...: Quantity of raw material (in kg)  
    Z_rsk = m.addVars(R, S, K, name="Z_rsk", vtype=GRB.CONTINUOUS, lb=0) # Recycle to Supplier

    # W_...: Boolean on/off decision for opening facilities   
    W_o = m.addVars(O, name="W_o", vtype=GRB.BINARY)
    W_f = m.addVars(F, name="W_f", vtype=GRB.BINARY)
    W_r = m.addVars(R, name="W_r", vtype=GRB.BINARY)
    
    m.update()

    # --- 4. OBJECTIVE FUNCTION: MINIMIZE Z_COST  ---

    # 3.1 Fixed Costs  
    Fixed_Cost = (
        quicksum(FixO[o] * W_o[o] for o in O) +
        quicksum(FixF[f] * W_f[f] for f in F) +
        quicksum(FixR[r] * W_r[r] for r in R)
    )

    # 3.2 Variable Operating Costs  
    Op_Cost = (
        quicksum(PC[p] * X_pdk[p, d, k] for p in P for d in D for k in K) + # Production  
        quicksum(CC[o] * Y_cok[c, o, k] for c in C for o in O for k in K) + # Collection 
        quicksum(FC[f] * Y_ofk[o, f, k] for o in O for f in F for k in K) + # Refurbishing   
        quicksum(RC[r] * Y_ork[o, r, k] * omega[k] for o in O for r in R for k in K) + # Recycling   
        quicksum(DC[l] * Y_olk[o, l, k] * omega[k] for o in O for l in L for k in K)  # Disposal   
    )
    
    # 3.3 Transportation Costs 
    Transport_Cost = (
        # Forward Logistics (P-D, D-C)  
        quicksum(T * get_dist(p, d) * X_pdk[p, d, k] * omega[k] for p in P for d in D for k in K) +
        quicksum(T * get_dist(d, c) * (X_dck[d, c, k] + Y_dck_prime[d, c, k]) * omega[k] for d in D for c in C for k in K) +

        # Reverse Logistics (C-O, O-D, O-F, O-R, O-L, F-P, R-S)  
        quicksum(T * get_dist(c, o) * Y_cok[c, o, k] * omega[k] for c in C for o in O for k in K) + # C-O   
        quicksum(T * get_dist(o, d) * Y_odk[o, d, k] * omega[k] for o in O for d in D for k in K) + # O-D
        quicksum(T * get_dist(o, f) * Y_ofk[o, f, k] * omega[k] for o in O for f in F for k in K) + # O-F   
        quicksum(T * get_dist(o, r) * Y_ork[o, r, k] * omega[k] for o in O for r in R for k in K) + # O-R   
        quicksum(T * get_dist(o, l) * Y_olk[o, l, k] * omega[k] for o in O for l in L for k in K) + # O-L   
        quicksum(T * get_dist(f, p) * Y_fpk[f, p, k] * omega[k] for f in F for p in P for k in K) + # F-P   
        quicksum(T * get_dist(r, s) * Z_rsk[r, s, k] for r in R for s in S for k in K)              # R-S   
    )

    # 3.4 Revenues (Subtracted)   
    Revenue = (
        quicksum(Rev_reuse * Y_dck_prime[d, c, k] for d in D for c in C for k in K) +
        quicksum(Rev_refurb * Y_fpk[f, p, k] for f in F for p in P for k in K) +
        quicksum(Rev_recycle * Z_rsk[r, s, k] for r in R for s in S for k in K)
    )

    # Total Cost Objective   
    Z_Cost = Fixed_Cost + Op_Cost + Transport_Cost - Revenue
    m.setObjective(Z_Cost, GRB.MINIMIZE)

    # --- 5. ENVIRONMENTAL CONSTRAINT (Z_Env <= epsilon) 

    # 4.1 Production Emissions   
    Env_Prod = quicksum(E_p[p] * X_pdk[p, d, k] for p in P for d in D for k in K) 

    # 4.2 Operating Emissions   
    Env_Op = (
        quicksum(E_o[o] * Y_cok[c, o, k] for c in C for o in O for k in K) +
        quicksum(E_f[f] * Y_ofk[o, f, k] for o in O for f in F for k in K) +
        quicksum(E_r[r] * Y_ork[o, r, k] * omega[k] for o in O for r in R for k in K) +
        quicksum(E_l[l] * Y_olk[o, l, k] * omega[k] for o in O for l in L for k in K)
    )

    # 4.3 Transportation Emissions   57]
    Env_Transport = (
        # P-D, D-C   58]
        quicksum(E_T * get_dist(p, d) * X_pdk[p, d, k] * omega[k] for p in P for d in D for k in K) +
        quicksum(E_T * get_dist(d, c) * (X_dck[d, c, k] + Y_dck_prime[d, c, k]) * omega[k] for d in D for c in C for k in K) +
        
        # Reverse Logistics 
        quicksum(E_T * get_dist(c, o) * Y_cok[c, o, k] * omega[k] for c in C for o in O for k in K) +
        quicksum(E_T * get_dist(o, d) * Y_odk[o, d, k] * omega[k] for o in O for d in D for k in K) +
        quicksum(E_T * get_dist(o, f) * Y_ofk[o, f, k] * omega[k] for o in O for f in F for k in K) +
        quicksum(E_T * get_dist(o, r) * Y_ork[o, r, k] * omega[k] for o in O for r in R for k in K) +
        quicksum(E_T * get_dist(o, l) * Y_olk[o, l, k] * omega[k] for o in O for l in L for k in K) +
        quicksum(E_T * get_dist(f, p) * Y_fpk[f, p, k] * omega[k] for f in F for p in P for k in K) +
        quicksum(E_T * get_dist(r, s) * Z_rsk[r, s, k] for r in R for s in S for k in K)
    )

    Z_Env = Env_Prod + Env_Op + Env_Transport

    # Epsilon-Constraint: Environmental goal must be below the limit
    m.addConstr(Z_Env <= epsilon_limit, "Environmental_Limit")

    # --- 6. KEY CONSTRAINTS
    # 5.1 1. Demand Satisfaction   
    for c in C:
        for k in K:
            m.addConstr(quicksum(X_dck[d, c, k] for d in D) + quicksum(Y_dck_prime[d, c, k] for d in D) >= DEM[c, k],
                        f"Demand_Sat_{c}_{k}")

    # Customer Returns Constraint (Ensuring Y_cok is limited by RET)
    for c in C:
        for k in K:
            m.addConstr(quicksum(Y_cok[c, o, k] for o in O) <= RET[c, k],
                        f"Returns_Limit_{c}_{k}")


    # 5.2 2. Flow Balance   
    # Inflow (Returns) = Outflow (Reuse, Refurbish, Recycle, Landfill)
    for o in O:
        for k in K:
            m.addConstr(quicksum(Y_cok[c, o, k] for c in C) ==
                        quicksum(Y_odk[o, d, k] for d in D) +
                        quicksum(Y_ofk[o, f, k] for f in F) +
                        quicksum(Y_ork[o, r, k] for r in R) +
                        quicksum(Y_olk[o, l, k] for l in L),
                        f"Flow_Balance_O_{o}_{k}")

    # Distributor (d) Balance (Forward Flow)   68]
    # Inflow (New from Plants) = Outflow (New to Customers)
    for d in D:
        for k in K:
            m.addConstr(quicksum(X_pdk[p, d, k] for p in P) == quicksum(X_dck[d, c, k] for c in C),
                        f"Flow_Balance_D_Forward_{d}_{k}")

    # Distributor (d) Balance (Reuse Flow)
    # Inflow (Reuse from Collection) = Outflow (Reuse to Customers)
    for d in D:
        for k in K:
            m.addConstr(quicksum(Y_odk[o, d, k] for o in O) == quicksum(Y_dck_prime[d, c, k] for c in C),
                        f"Flow_Balance_D_Reuse_{d}_{k}")

    # Production Plant (p) Balance   72]
    # Inflow (Refurbished Material + New Production) = Outflow (New to Distributors)
    # Note: We must define the amount of new production, which is implicitly X_pk in the source.
    # $X_{pk}$ is the total new production at p for k.
    X_pk_total = m.addVars(P, K, name="X_pk_total", vtype=GRB.CONTINUOUS, lb=0)
    for p in P:
        for k in K:
            m.addConstr(X_pk_total[p, k] == quicksum(X_pdk[p, d, k] for d in D), "Def_Xpk_Total")

    for p in P:
        for k in K:
            m.addConstr(quicksum(Y_fpk[f, p, k] for f in F) + X_pk_total[p, k] == quicksum(X_pdk[p, d, k] for d in D),
                        f"Flow_Balance_P_{p}_{k}")
    

    # 5.3 3. Yield Factors  

    # Refurbishing Yield  
    # Outflow (to Plant) = Yield * Inflow (from Collection)
    for f in F:
        for k in K:
            m.addConstr(quicksum(Y_fpk[f, p, k] for p in P) == alpha[f] * quicksum(Y_ofk[o, f, k] for o in O),
                        f"Yield_Refurb_{f}_{k}")

    # Recycling Yield   79]
    # Outflow (to Supplier, in kg) = Yield * Inflow (from Collection, in kg)
    for r in R:
        for k in K:
            m.addConstr(quicksum(Z_rsk[r, s, k] for s in S) == beta[r] * quicksum(Y_ork[o, r, k] * omega[k] for o in O),
                        f"Yield_Recycle_{r}_{k}")


    # 5.4 4. Capacity Constraints   82]

    # Production Capacity (KWp)   83]
    for p in P:
        m.addConstr(quicksum(X_pk_total[p, k] for k in K) <= CAP_p[p],
                f"Cap_Prod_{p}")

    # Reverse Facilities Capacities (Activated by W variables)   89]

    # Collection Capacity (KWp)   90]
    # $\sum_{c\in C,k\in K} Y_{cok}$ is used in source, but $Y_{cok}$ is inflow (Returns). Use $\sum_{c\in C,k\in K} Y_{cok}$ for consistency.
    for o in O:
        m.addConstr(quicksum(Y_cok[c, o, k] for c in C for k in K) * omega[k] <= CAP_o[o] * W_o[o],
                f"Cap_Collect_{o}")

    # Refurbish Capacity (KWp)
    for f in F:
        m.addConstr(quicksum(Y_ofk[o, f, k] for o in O for k in K) <= CAP_f[f] * W_f[f],
                f"Cap_Refurb_{f}")

    # Recycling Capacity (kg)
    for r in R:
        m.addConstr(quicksum(Y_ork[o, r, k] * omega[k] for o in O for k in K) <= CAP_r[r] * W_r[r],
                f"Cap_Recycle_{r}")
    

    # --- 7. OPTIMIZE AND REPORT ---
    
    m.optimize()

    # --- PRINT RESULTS ---
    if m.status == GRB.OPTIMAL:
        print("\n--- OPTIMAL SOLUTION FOUND (Epsilon-Constraint Method) ---")
        print(f"**Target Environmental Limit ($\epsilon$): {epsilon_limit:,.2f} kg CO2e**")
        print(f"**Minimum Total Cost ($Z_{{Cost}}$): ${m.objVal:,.2f}**")
        
        # Verify Environmental Cost
        env_val = Z_Env.getValue()
        print(f"Total Environmental Footprint ($Z_{{Env}}$): {env_val:,.2f} kg CO2e")

        print("\n--- Decision Variables ---")
        print("\nFacility Opening Decisions:")
        
        # Collect and print opening decisions
        opened_facilities = []
        for o in O:
            if W_o[o].X > 0.5: opened_facilities.append(f"Collection Center {o}")
        for f in F:
            if W_f[f].X > 0.5: opened_facilities.append(f"Refurbish Center {f}")
        for r in R:
            if W_r[r].X > 0.5: opened_facilities.append(f"Recycling Center {r}")
            
        if opened_facilities:
            print("Opened Facilities:")
            for f_name in opened_facilities:
                print(f"* {f_name}")
        else:
            print("No new facilities were opened in this solution.")

        # Example flow variable (X_dck)
        print("\nNew Module Flow (Distributor to Customer, X_dck > 0):")
        for d in D:
            for c in C:
                for k in K:
                    if X_dck[d, c, k].X > 0.1:
                        print(f"  {d} -> {c} ({k}): {X_dck[d, c, k].X:,.2f} KWp")
        
        # Example flow variable (Y_dck')
        print("\nReused/Refurbished Module Flow (Distributor to Customer, Y_dck' > 0):")
        for d in D:
            for c in C:
                for k in K:
                    if Y_dck_prime[d, c, k].X > 0.1:
                        print(f"  {d} -> {c} ({k}): {Y_dck_prime[d, c, k].X:,.2f} KWp")

    elif m.status == GRB.INFEASIBLE:
        print("\nModel is INFEASIBLE. The environmental limit ($\epsilon$) may be too strict.")
        m.computeIIS() # Compute Irreducible Inconsistent System (IIS)
        m.write("infeasible_model.ilp")
    else:
        print(f"\nModel not solved to optimal status. Status code: {m.status}")


if __name__ == '__main__':
    # Define the environmental limit (epsilon) for the single run.
    # The value is an estimate based on placeholder data (50000 kg CO2e)
    target_epsilon = 500000.0
    solve_circular_supply_chain_model(target_epsilon)