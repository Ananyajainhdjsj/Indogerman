import pandas as pd
from gurobipy import *

def read_excel_data(filepath='supply_chain_data.xlsx'):
    """
    Read all supply chain parameters from Excel file.
    Returns a dictionary containing all model parameters.
    """
    data = {}
    
    # ============================================================================
    # SHEET 1: PLANTS
    # ============================================================================
    df_plants = pd.read_excel(filepath, sheet_name='Plants', header=3)
    df_plants = df_plants.dropna(subset=['Plant Code'])
    
    data['P'] = df_plants['Plant Code'].tolist()
    data['PC'] = dict(zip(df_plants['Plant Code'], df_plants['Production Cost (€/KWp)']))
    data['CAP_p'] = dict(zip(df_plants['Plant Code'], df_plants['Capacity (KWp)']))
    data['E_p'] = dict(zip(df_plants['Plant Code'], df_plants['Emissions Factor (kg CO2e/KWp)']))
    
    # ============================================================================
    # SHEET 2: CUSTOMERS
    # ============================================================================
    df_customers = pd.read_excel(filepath, sheet_name='Customers', header=3)
    df_customers = df_customers.dropna(subset=['Customer Code'])
    
    data['C'] = df_customers['Customer Code'].unique().tolist()
    data['K'] = df_customers['Product Type'].unique().tolist()
    
    data['DEM'] = {}
    data['RET'] = {}
    for _, row in df_customers.iterrows():
        data['DEM'][(row['Customer Code'], row['Product Type'])] = float(row['Demand (KWp)'])
        data['RET'][(row['Customer Code'], row['Product Type'])] = float(row['Returns (KWp)'])
    
    # ============================================================================
    # SHEET 3: COLLECTION CENTERS
    # ============================================================================
    df_collection = pd.read_excel(filepath, sheet_name='Collection_Centers', header=3)
    df_collection = df_collection.dropna(subset=['Code'])
    
    data['O'] = df_collection['Code'].tolist()
    data['CC'] = dict(zip(df_collection['Code'], df_collection['Collection Cost (€/KWp)']))
    data['FixO'] = dict(zip(df_collection['Code'], df_collection['Fixed Cost (€)']))
    data['CAP_o'] = dict(zip(df_collection['Code'], df_collection['Capacity (kg)']))
    data['E_o'] = dict(zip(df_collection['Code'], df_collection['Emissions Factor (kg CO2e/KWp)']))
    
    # ============================================================================
    # SHEET 4: REFURBISHMENT CENTERS
    # ============================================================================
    df_refurb = pd.read_excel(filepath, sheet_name='Refurbishment_Centers', header=3)
    df_refurb = df_refurb.dropna(subset=['Code'])
    
    data['F'] = df_refurb['Code'].tolist()
    data['FC'] = dict(zip(df_refurb['Code'], df_refurb['Refurbishing Cost (€/KWp)']))
    data['FixF'] = dict(zip(df_refurb['Code'], df_refurb['Fixed Cost (€)']))
    data['CAP_f'] = dict(zip(df_refurb['Code'], df_refurb['Capacity (kg)']))
    data['alpha'] = dict(zip(df_refurb['Code'], df_refurb['Yield (%)']))
    data['E_f'] = dict(zip(df_refurb['Code'], df_refurb['Emissions Factor (kg CO2e/KWp)']))
    
    # ============================================================================
    # SHEET 5: RECYCLING CENTERS
    # ============================================================================
    df_recycle = pd.read_excel(filepath, sheet_name='Recycling_Centers', header=3)
    df_recycle = df_recycle.dropna(subset=['Code'])
    
    data['R'] = df_recycle['Code'].tolist()
    data['RC'] = dict(zip(df_recycle['Code'], df_recycle['Recycling Cost (€/kg)']))
    data['FixR'] = dict(zip(df_recycle['Code'], df_recycle['Fixed Cost (€)']))
    data['CAP_r'] = dict(zip(df_recycle['Code'], df_recycle['Capacity (kg)']))
    data['beta'] = dict(zip(df_recycle['Code'], df_recycle['Efficiency (%)']))
    data['E_r'] = dict(zip(df_recycle['Code'], df_recycle['Emissions Factor (kg CO2e/kg)']))
    
    # ============================================================================
    # SHEET 6: LANDFILLS
    # ============================================================================
    df_landfill = pd.read_excel(filepath, sheet_name='Landfills', header=3)
    df_landfill = df_landfill.dropna(subset=['Code'])
    
    data['L'] = df_landfill['Code'].tolist()
    data['DC'] = dict(zip(df_landfill['Code'], df_landfill['Disposal Cost (€/kg)']))
    data['E_l'] = dict(zip(df_landfill['Code'], df_landfill['Emissions Factor (kg CO2e/kg)']))
    
    # ============================================================================
    # SHEET 7: SECONDARY MARKETS
    # ============================================================================
    df_secondary = pd.read_excel(filepath, sheet_name='Secondary_Markets', header=3)
    df_secondary = df_secondary.dropna(subset=['Code'])
    
    data['S'] = df_secondary['Code'].tolist()
    
    # ============================================================================
    # SHEET 8: DISTANCE MATRIX
    # ============================================================================
    df_dist = pd.read_excel(filepath, sheet_name='Distance_Matrix', header=3)
    df_dist = df_dist.dropna(subset=['From'])
    
    data['DIST'] = {}
    for _, row in df_dist.iterrows():
        data['DIST'][(row['From'], row['To'])] = float(row['Distance (km)'])
    
    # ============================================================================
    # SHEET 9: REVENUES
    # ============================================================================
    df_rev = pd.read_excel(filepath, sheet_name='Revenues')
    
    # Product revenues
    product_rev_start = df_rev[df_rev.iloc[:, 0] == 'Product Type'].index[0]
    material_rev_start = df_rev[df_rev.iloc[:, 0] == 'Material'].index[0]
    
    df_product_rev = df_rev.iloc[product_rev_start+1:material_rev_start-2]
    data['Rev_reuse'] = {}
    data['Rev_refurb'] = {}
    for _, row in df_product_rev.iterrows():
        if pd.notna(row.iloc[0]):
            product = row.iloc[0]
            rev_type = row.iloc[1]
            revenue = float(row.iloc[2])
            if rev_type == 'Reuse':
                data['Rev_reuse'][product] = revenue
            elif rev_type == 'Refurbished':
                data['Rev_refurb'][product] = revenue
    
    # Material revenues
    df_material_rev = df_rev.iloc[material_rev_start+1:]
    df_material_rev = df_material_rev.dropna(subset=[df_material_rev.columns[0]])
    data['Rev_recycle'] = {}
    for _, row in df_material_rev.iterrows():
        if pd.notna(row.iloc[0]):
            data['Rev_recycle'][row.iloc[0]] = float(row.iloc[1])
    
    # ============================================================================
    # SHEET 10: MATERIALS
    # ============================================================================
    df_materials = pd.read_excel(filepath, sheet_name='Materials', header=3)
    df_materials = df_materials.dropna(subset=['Material'])
    
    data['M'] = df_materials['Material'].tolist()
    data['gamma'] = {}
    for _, row in df_materials.iterrows():
        for k in data['K']:
            data['gamma'][(k, row['Material'])] = float(row['Quantity (kg/KWp)'])
    
    # ============================================================================
    # SHEET 11: PARAMETERS
    # ============================================================================
    df_params = pd.read_excel(filepath, sheet_name='Parameters', header=2)
    
    param_dict = dict(zip(df_params['Parameter'], df_params['Value']))
    
    data['T'] = float(param_dict['Transport Cost'])
    data['Penalty'] = float(param_dict['Penalty Cost'])
    data['E_T'] = float(param_dict['Transport Emissions'])
    data['omega'] = {k: float(param_dict['Panel Weight']) for k in data['K']}
    data['Quality_Mix'] = {
        'Reuse_Cap': float(param_dict['Reuse Capacity']),
        'Refurb_Cap': float(param_dict['Refurbishment Capacity'])
    }
    data['epsilon_limit'] = float(param_dict['Epsilon Limit'])
    minimize_str = str(param_dict['Minimize Emissions Only']).upper()
    data['minimize_emissions_only'] = minimize_str == 'TRUE'
    
    return data


def solve_circular_supply_chain_model(epsilon_limit=None, minimize_emissions_only=False, excel_file='supply_chain_data.xlsx'):
    """
    Solve the circular supply chain optimization model.
    Can read from Excel or use provided parameters.
    """
    
    print("="*70)
    print("CIRCULAR SUPPLY CHAIN OPTIMIZATION MODEL")
    print("="*70)
    
    # Read data from Excel
    if excel_file:
        print(f"Reading data from: {excel_file}")
        data = read_excel_data(excel_file)
        
        # Override with function parameters if provided
        if epsilon_limit is not None:
            data['epsilon_limit'] = epsilon_limit
        if minimize_emissions_only is not None:
            data['minimize_emissions_only'] = minimize_emissions_only
        
        print(f"✓ Data loaded successfully")
        print(f"  - Plants: {len(data['P'])}")
        print(f"  - Customers: {len(data['C'])}")
        print(f"  - Collection Centers: {len(data['O'])}")
        print(f"  - Refurbishment Centers: {len(data['F'])}")
        print(f"  - Recycling Centers: {len(data['R'])}")
        print(f"  - Landfills: {len(data['L'])}")
        print(f"  - Secondary Markets: {len(data['S'])}")
        print(f"  - Product Types: {len(data['K'])}")
        print(f"  - Materials: {len(data['M'])}")
    
    # Extract all parameters
    P = data['P']
    C = data['C']
    O = data['O']
    F = data['F']
    R = data['R']
    L = data['L']
    S = data['S']
    K = data['K']
    M = data['M']
    
    PC = data['PC']
    CC = data['CC']
    FC = data['FC']
    RC = data['RC']
    DC = data['DC']
    
    T = data['T']
    Penalty = data['Penalty']
    
    FixO = data['FixO']
    FixF = data['FixF']
    FixR = data['FixR']
    
    DEM = data['DEM']
    RET = data['RET']
    
    omega = data['omega']
    alpha = data['alpha']
    beta = data['beta']
    
    Quality_Mix = data['Quality_Mix']
    gamma = data['gamma']
    
    CAP_p = data['CAP_p']
    CAP_o = data['CAP_o']
    CAP_f = data['CAP_f']
    CAP_r = data['CAP_r']
    
    Rev_reuse = data['Rev_reuse']
    Rev_refurb = data['Rev_refurb']
    Rev_recycle = data['Rev_recycle']
    
    DIST = data['DIST']
    def get_dist(i, j):
        return DIST.get((i, j), 50.0)
    
    E_p = data['E_p']
    E_o = data['E_o']
    E_f = data['E_f']
    E_r = data['E_r']
    E_l = data['E_l']
    E_T = data['E_T']
    
    epsilon_limit = data['epsilon_limit']
    minimize_emissions_only = data['minimize_emissions_only']
    
    print("\n" + "="*70)
    print("BUILDING OPTIMIZATION MODEL...")
    print("="*70)
    
    # --- 3. MODEL ---
    m = Model("Circular_Supply_Chain_Germany")
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
        sum(Rev_reuse[k] * Y_ock[o, c, k] for o in O for c in C for k in K if k in Rev_reuse) +
        sum(Rev_refurb[k] * Y_fpk[f, p, k] for f in F for p in P for k in K if k in Rev_refurb) +
        sum(Rev_recycle[mat] * Z_rsm[r, s, mat] for r in R for s in S for mat in M if mat in Rev_recycle)
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
        print("\n→ Objective: MINIMIZE EMISSIONS")
        m.setObjective(Env_Total, GRB.MINIMIZE)
    else:
        print("\n→ Objective: MINIMIZE COST")
        print(f"→ Emission Constraint: ≤ {epsilon_limit:,.0f} kg CO2e")
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
    for o in O: 
        m.addConstr(sum(Y_cok[c, o, k] for c in C for k in K) * omega[K[0]] <= CAP_o[o] * W_o[o])
    for f in F: 
        m.addConstr(sum(Y_ofk[o, f, k] for o in O for k in K) * omega[K[0]] <= CAP_f[f] * W_f[f])
    for r in R: 
        m.addConstr(sum(Y_ork[o, r, k] * omega[K[0]] for o in O for k in K) <= CAP_r[r] * W_r[r])

    print(f"✓ Total constraints: {m.NumConstrs}")
    print(f"✓ Total variables: {m.NumVars}")
    
    print("\n" + "="*70)
    print("SOLVING...")
    print("="*70)
    
    m.optimize()

    # --- OUTPUT ---
    print("\n" + "="*70)
    print("OPTIMIZATION RESULTS")
    print("="*70)
    
    if m.status == GRB.OPTIMAL:
        print("✓ STATUS: OPTIMAL SOLUTION FOUND\n")
        
        cost_val = Z_Cost.getValue()
        env_val = Env_Total.getValue()
        
        print(f"→ Total Cost: €{cost_val:,.2f}")
        print(f"→ Total Emissions: {env_val:,.2f} kg CO2e")
        print(f"\nCost Breakdown:")
        print(f"  - Fixed Costs: €{Fixed_Cost.getValue():,.2f}")
        print(f"  - Operational Costs: €{Op_Cost.getValue():,.2f}")
        print(f"  - Transport Costs: €{Transport_Cost.getValue():,.2f}")
        print(f"  - Shortage Penalty: €{Shortage_Cost.getValue():,.2f}")
        print(f"  - Revenue: €{Revenue.getValue():,.2f}")
        
        print("\n" + "="*70)
        
        return "Optimal", cost_val, env_val
    else:
        if m.status == GRB.INFEASIBLE:
            print("✗ STATUS: INFEASIBLE")
            return "Infeasible", None, None
        print(f"✗ STATUS: {m.status}")
        return "Other", None, None


if __name__ == '__main__':
    # Run with Excel file
    result = solve_circular_supply_chain_model(excel_file='supply_chain_data.xlsx')
    print(f"\nFinal Result: {result}")