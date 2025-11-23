import matplotlib.pyplot as plt
import numpy as np
import sys

# --- IMPORT THE MODEL ---
# Prefer the newer model file `model_anu2.py`, fall back to `model_anu.py` for compatibility.
solve_func = None
try:
    from model_anu2 import solve_circular_supply_chain_model as solve_func
except Exception:
    try:
        from model_anu import solve_circular_supply_chain_model as solve_func
    except Exception:
        print("\nCRITICAL ERROR: Could not import model function from 'model_anu2.py' or 'model_anu.py'.")
        print("Please ensure one of those files exists and defines `solve_circular_supply_chain_model` in the same folder.\n")
        sys.exit(1)
# Normalize name used below
solve_circular_supply_chain_model = solve_func

def generate_pareto_frontier(points=10):
    print("\n" + "="*60)
    print(f"   STARTING PARETO FRONTIER GENERATION (Euro €)")
    print("="*60 + "\n")

    # --- STEP 1: FIND EXTREME POINTS (RANGE) ---
    
    # 1A. Find Minimum Cost (Max Emissions)
    # We use a huge epsilon (1 Billion) to make the constraint non-binding
    print("--> Calculating Point A: Minimum Cost (Business as Usual)...")
    res = solve_circular_supply_chain_model(1_000_000_000)
    if not res or not isinstance(res, tuple) or len(res) < 3:
        print("Error: model did not return (status, cost, emissions). Got:", res)
        return
    status_max, min_cost_val, max_env_val = res

    if status_max != "Optimal":
        print("Error: Could not solve for minimum cost. Check model constraints.")
        return

    print(f"    [Point A] Cheapest Option: €{min_cost_val:,.2f} | Emissions: {max_env_val:,.0f} kg CO2e")

    # 1B. Find Minimum Emissions (Greenest Solution)
    # We use the special flag 'minimize_emissions_only=True'
    print("\n--> Calculating Point B: Minimum Emissions (Greenest Solution)...")
    res2 = solve_circular_supply_chain_model(0, minimize_emissions_only=True)
    if not res2 or not isinstance(res2, tuple) or len(res2) < 3:
        print("Error: model did not return (status, cost, emissions) for min-emissions run. Got:", res2)
        return
    status_min, max_cost_val, min_env_val = res2

    if status_min != "Optimal":
        print("Error: Could not solve for minimum emissions.")
        return

    print(f"    [Point B] Greenest Option: €{max_cost_val:,.2f} | Emissions: {min_env_val:,.0f} kg CO2e")

    # --- STEP 2: GENERATE GRID ---
    
    # Create 10 evenly spaced emission targets between Min and Max
    epsilon_grid = np.linspace(min_env_val, max_env_val, points)
    
    pareto_costs = []
    pareto_emissions = []
    
    print(f"\n--> Generating trade-off curve ({points} scenarios)...")
    
    for i, epsilon in enumerate(epsilon_grid):
        # Skip the extremes if we already calculated them, but running them ensures consistency
        print(f"    [{i+1}/{points}] Solving for Limit <= {epsilon:,.0f}...", end=" ")
        
        res_i = solve_circular_supply_chain_model(epsilon)
        if not res_i or not isinstance(res_i, tuple) or len(res_i) < 3:
            print("Infeasible or error (model did not return expected tuple)")
            continue
        status, cost, real_emission = res_i
        if status == "Optimal":
            pareto_costs.append(cost)
            pareto_emissions.append(real_emission)
            print(f"Success! Cost: €{cost:,.0f}")
        else:
            print("Infeasible (Constraint too strict)")

    # --- STEP 3: PLOTTING ---
    
    print("\n--> Plotting Pareto Frontier...")
    
    plt.figure(figsize=(10, 6))
    
    # Plot the curve
    plt.plot(pareto_emissions, pareto_costs, marker='o', linestyle='-', color='#1f77b4', linewidth=2, label='Pareto Front')
    
    # Highlight Start and End points
    plt.scatter([max_env_val], [min_cost_val], color='green', s=100, zorder=5, label='Cheapest (Max CO2)')
    plt.scatter([min_env_val], [max_cost_val], color='red', s=100, zorder=5, label='Greenest (Min CO2)')

    # Labels and Titles
    plt.title('Pareto Frontier: Supply Chain Cost vs. Carbon Footprint', fontsize=14)
    plt.xlabel('Carbon Emissions (kg CO2e)', fontsize=12)
    plt.ylabel('Total Supply Chain Cost (€)', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    
    # Annotate the cost difference
    cost_diff = max_cost_val - min_cost_val
    env_diff = max_env_val - min_env_val
    plt.text(
        (min_env_val + max_env_val)/2, 
        (min_cost_val + max_cost_val)/2, 
        f"Cost of Decarbonization:\n+€{cost_diff:,.0f}", 
        fontsize=10, bbox=dict(facecolor='white', alpha=0.8)
    )

    # Save and Show
    plt.tight_layout()
    plt.savefig('pareto_frontier_euro.png')
    print(f"    Chart saved as 'pareto_frontier_euro.png'")
    plt.show()

if __name__ == '__main__':
    generate_pareto_frontier(points=10)
