import matplotlib.pyplot as plt
import numpy as np
import sys

# --- IMPORT THE MODEL ---
solve_func = None
try:
    from model_anu2 import solve_circular_supply_chain_model as solve_func
except Exception:
    try:
        from integrate import solve_circular_supply_chain_model as solve_func
    except Exception:
        print("\nCRITICAL ERROR: Could not import model function.")
        sys.exit(1)

solve_circular_supply_chain_model = solve_func


def generate_pareto_frontier(points=20):
    print("\n" + "="*70)
    print(f"   STARTING PARETO FRONTIER GENERATION (Constraint Sweep Method)")
    print("="*70 + "\n")

    # ---------------------------------------------------------------
    # STEP 1 — Get the two extreme points
    # ---------------------------------------------------------------

    print("--> Step 1: Extreme Points")

    # A — Minimum cost (maximum emissions)
    print("    Finding cheapest solution...")
    statusA, min_cost, max_emissions = solve_circular_supply_chain_model(
        epsilon_limit=1e12  # non-binding
    )
    print(f"      Cheapest Option: €{min_cost:,.2f} | Emissions {max_emissions:,.0f} kg CO2e")

    # B — Minimum emissions
    print("    Finding minimum-emission solution...")
    statusB, max_cost, min_emissions = solve_circular_supply_chain_model(
        epsilon_limit=0,
        minimize_emissions_only=True
    )
    print(f"      Greenest Option: €{max_cost:,.2f} | Emissions {min_emissions:,.0f} kg CO2e")

    # ---------------------------------------------------------------
    # STEP 2 — Generate the Pareto Curve by sweeping epsilon
    # ---------------------------------------------------------------

    print("\n--> Step 2: Generating Pareto curve...")

    # Sweep from HIGH → LOW to avoid repeated solutions
    epsilon_grid = np.linspace(max_emissions, min_emissions, points)

    pareto_costs = []
    pareto_emissions = []

    for i, eps in enumerate(epsilon_grid):
        eps_adj = eps * 0.999  # numerical slack to avoid duplicate solutions
        print(f"    [{i+1}/{points}] Solving for emissions ≤ {eps_adj:,.0f} ... ", end="")

        res = solve_circular_supply_chain_model(epsilon_limit=eps_adj)

        if not res or len(res) < 3:
            print("Error!")
            continue

        status, cost, emissions = res
        if status != "Optimal":
            print("Infeasible")
            continue

        pareto_costs.append(cost)
        pareto_emissions.append(emissions)
        print(f"OK  (Cost €{cost:,.0f})")

    # Sort points
    pareto_emissions, pareto_costs = zip(*sorted(zip(pareto_emissions, pareto_costs)))

    # ---------------------------------------------------------------
    # STEP 3 — Plot
    # ---------------------------------------------------------------

    print("\n--> Step 3: Plotting Pareto Frontier...\n")

    plt.figure(figsize=(10, 6))
    plt.plot(pareto_emissions, pareto_costs, marker='o', linewidth=2,
             label='Pareto Frontier')

    plt.scatter([max_emissions], [min_cost], s=120, color='green', label='Cheapest')
    plt.scatter([min_emissions], [max_cost], s=120, color='red', label='Greenest')

    plt.title("Pareto Frontier: Cost vs CO₂ Emissions")
    plt.xlabel("Emissions (kg CO₂e)")
    plt.ylabel("Cost (€)")
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend()

    plt.tight_layout()
    plt.savefig("pareto_frontier_constraint_sweep.png")
    plt.show()

    print("Saved as: pareto_frontier_constraint_sweep.png")


# ---------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------
if __name__ == "__main__":
    generate_pareto_frontier(points=20)
