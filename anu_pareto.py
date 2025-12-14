import pandas as pd
import matplotlib.pyplot as plt

def plot_cost_min_curve(csv_file):
    df = pd.read_csv(csv_file)

    plt.figure(figsize=(7,5))
    plt.plot(df["env"], df["cost"], marker="o", linewidth=2, label="Cost-min Frontier")

    plt.xlabel("Environmental Impact (Z_env)")
    plt.ylabel("Cost (Z_cost)")
    plt.title("Pareto Curve A – Minimize Cost (Env ≤ ε)")
    plt.grid(True)
    plt.legend()

    outname = csv_file.replace(".csv", ".png")
    plt.savefig(outname, dpi=300)
    plt.close()

    print("Saved:", outname)


def plot_env_min_curve(csv_file):
    df = pd.read_csv(csv_file)

    plt.figure(figsize=(7,5))
    plt.plot(df["env"], df["cost"], marker="s", linewidth=2, color="green",
             label="Env-min Frontier")

    plt.xlabel("Environmental Impact (Z_env)")
    plt.ylabel("Cost (Z_cost)")
    plt.title("Pareto Curve B – Minimize Env (Cost ≤ ε)")
    plt.grid(True)
    plt.legend()

    outname = csv_file.replace(".csv", ".png")
    plt.savefig(outname, dpi=300)
    plt.close()

    print("Saved:", outname)


def plot_combined_frontier(csv_cost_min, csv_env_min):

    dfA = pd.read_csv(csv_cost_min)
    dfB = pd.read_csv(csv_env_min)

    plt.figure(figsize=(7,5))

    plt.plot(dfA["env"], dfA["cost"], marker="o", linewidth=2,
             label="Curve A: Min Cost (Env ≤ ε)")

    plt.plot(dfB["env"], dfB["cost"], marker="s", linewidth=2,
             label="Curve B: Min Env (Cost ≤ ε)")

    plt.xlabel("Environmental Impact (Z_env)")
    plt.ylabel("Cost (Z_cost)")
    plt.title("Full Pareto Frontier (Bidirectional ε-Constraint)")
    plt.grid(True)
    plt.legend()

    plt.savefig("pareto_frontier_full.png", dpi=300)
    plt.close()

    print("Saved: pareto_frontier_full.png")


if __name__ == "__main__":
    # Modify filenames based on your timestamp
    cost_min_csv = input("Enter CSV for cost-min curve: ")
    env_min_csv  = input("Enter CSV for env-min curve: ")

    plot_cost_min_curve(cost_min_csv)
    plot_env_min_curve(env_min_csv)
    plot_combined_frontier(cost_min_csv, env_min_csv)
