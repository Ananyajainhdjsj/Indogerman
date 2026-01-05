import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# ==========================================
# 1. SETUP: INPUT FILES
# ==========================================
files = {
    "A": {
        "name": "Scenario A: Linear (Baseline)",
        "color": "#d62728", # Red
        "cost_min_csv": "Pareto_Linear_Like_CostMin.csv",
        "env_min_csv":  "Pareto_Linear_Like_EnvMin.csv"
    },
    "B": {
        "name": "Scenario B: Industrial Refurb",
        "color": "#1f77b4", # Blue
        "cost_min_csv": "Pareto_Industrial_Refurb_CostMin.csv",
        "env_min_csv":  "Pareto_Industrial_Refurb_EnvMin.csv"
    },
    "C": {
        "name": "Scenario C: Consumer Reuse",
        "color": "#2ca02c", # Green
        "cost_min_csv": "Pareto_Consumer_Reuse_CostMin.csv",
        "env_min_csv":  "Pareto_Consumer_Reuse_EnvMin.csv"
    }
}

def load_data():
    """Reads all CSVs."""
    data_store = {}
    print("--- Loading Data ---")
    for key, info in files.items():
        try:
            df_cost_min = pd.read_csv(info["cost_min_csv"]) # Curve A
            df_env_min = pd.read_csv(info["env_min_csv"])   # Curve B
            data_store[key] = {"c_min": df_cost_min, "e_min": df_env_min, "meta": info}
            print(f"Loaded Scenario {key}")
        except FileNotFoundError as e:
            print(f"Error: Missing {e.filename}")
            return None
    return data_store

def format_billions(x, pos):
    return f'{x*1e-9:.1f}B'

# ==========================================
# 2. PLOTTING FUNCTIONS
# ==========================================

def plot_perspective_env_on_x(data):
    """
    Research Question: "If we enforce an emission limit (X), what is the cost (Y)?"
    Data Source: Cost-Minimization Curves (Curve A)
    """
    plt.figure(figsize=(10, 7))
    ax = plt.gca()
    
    # Use global min/max for scaling if desired, or let matplotlib scale naturally
    
    for key, val in data.items():
        df = val["c_min"] # Use Cost-Min data
        meta = val["meta"]
        
        # Sort by Env (X-axis) to ensure clean line
        df = df.sort_values("epsilon_env")
        
        plt.plot(df["epsilon_env"], df["cost"], 
                 marker='o', linewidth=2.5, markersize=6,
                 label=meta["name"], color=meta["color"])

    # Formatting
    ax.xaxis.set_major_formatter(plt.FuncFormatter(format_billions))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(format_billions))
    
    plt.xlabel("Emission Limit (kg CO2e) [Constraint]", fontsize=12, fontweight='bold')
    plt.ylabel("Minimum Total Cost (€) [Objective]", fontsize=12, fontweight='bold')
    plt.title("Comparison 1: Cost of Sustainability\n(Minimizing Cost subject to Environmental Constraints)", fontsize=14)
    plt.legend(fontsize=11)
    plt.grid(True, linestyle='--', alpha=0.6)
    
    plt.savefig("Comparison_1_Env_on_X.png", dpi=300)
    print("Saved: Comparison_1_Env_on_X.png")


def plot_perspective_cost_on_x(data):
    """
    Research Question: "If we have a budget limit (X), what is the environmental impact (Y)?"
    Data Source: Env-Minimization Curves (Curve B)
    """
    plt.figure(figsize=(10, 7))
    ax = plt.gca()
    
    for key, val in data.items():
        df = val["e_min"] # Use Env-Min data
        meta = val["meta"]
        
        # Sort by Cost (X-axis)
        df = df.sort_values("epsilon_cost")
        
        plt.plot(df["epsilon_cost"], df["env"], 
                 marker='s', linewidth=2.5, markersize=6,
                 label=meta["name"], color=meta["color"])

    # Formatting
    ax.xaxis.set_major_formatter(plt.FuncFormatter(format_billions))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(format_billions))
    
    plt.xlabel("Budget Limit (€) [Constraint]", fontsize=12, fontweight='bold')
    plt.ylabel("Minimum Emissions (kg CO2e) [Objective]", fontsize=12, fontweight='bold')
    plt.title("Comparison 2: Environmental Efficiency of Budget\n(Minimizing Emissions subject to Cost Constraints)", fontsize=14)
    plt.legend(fontsize=11)
    plt.grid(True, linestyle='--', alpha=0.6)
    
    plt.savefig("Comparison_2_Cost_on_X.png", dpi=300)
    print("Saved: Comparison_2_Cost_on_X.png")

if __name__ == "__main__":
    sns.set_style("whitegrid")
    data = load_data()
    
    if data:
        # Plot 1: X = Env (Constraint), Y = Cost (Result)
        plot_perspective_env_on_x(data)
        
        # Plot 2: X = Cost (Constraint), Y = Env (Result)
        plot_perspective_cost_on_x(data)
