import csv

# Create CSV content for Excel template
sections = []

# 1. Sets Configuration
sections.append(["SETS CONFIGURATION"])
sections.append(["Set Type", "Code", "Description"])
sections.append(["Plants", "P1", "Main Production Plant"])
sections.append(["Customers", "C1", "Customer Zone 1"])
sections.append(["Customers", "C2", "Customer Zone 2"])
sections.append(["Collection Centers", "O1", "Collection Center 1"])
sections.append(["Refurbishment Centers", "F1", "Refurbishment Facility 1"])
sections.append(["Recycling Centers", "R1", "Recycling Center 1"])
sections.append(["Landfills", "L1", "Landfill Site 1"])
sections.append(["Secondary Markets", "S1", "Material Buyer 1"])
sections.append(["Product Types", "Monocrystalline", "Solar Panel Type"])
sections.append(["Materials", "Glass", "Panel Glass"])
sections.append(["Materials", "Aluminum", "Aluminum Frame"])
sections.append(["Materials", "Silicon", "Silicon Cells"])
sections.append(["Materials", "Plastic", "Plastic Components"])
sections.append(["Materials", "Copper", "Copper Wiring"])
sections.append([""])
sections.append([""])

# 2. Operational Costs
sections.append(["OPERATIONAL COSTS (€)"])
sections.append(["Facility", "Code", "Cost per Unit", "Unit Type"])
sections.append(["Production", "P1", 140, "€/KWp"])
sections.append(["Collection", "O1", 8, "€/KWp"])
sections.append(["Refurbishing", "F1", 25, "€/KWp"])
sections.append(["Recycling", "R1", 0.60, "€/kg"])
sections.append(["Disposal", "L1", 0.15, "€/kg"])
sections.append([""])
sections.append([""])

# 3. Transport Costs
sections.append(["TRANSPORT COST"])
sections.append(["Parameter", "Value", "Unit"])
sections.append(["Transport Cost per kg-km", 0.004, "€/kg-km"])
sections.append([""])
sections.append([""])

# 4. Penalty Costs
sections.append(["PENALTY COSTS"])
sections.append(["Type", "Value", "Unit"])
sections.append(["Unmet Demand Penalty", 20000, "€/KWp"])
sections.append([""])
sections.append([""])

# 5. Fixed Costs
sections.append(["FIXED COSTS (€)"])
sections.append(["Facility Type", "Code", "Fixed Cost"])
sections.append(["Collection Center", "O1", 15000])
sections.append(["Refurbishment Center", "F1", 25000])
sections.append(["Recycling Center", "R1", 30000])
sections.append([""])
sections.append([""])

# 6. Demand
sections.append(["DEMAND (KWp)"])
sections.append(["Customer", "Product Type", "Demand"])
sections.append(["C1", "Monocrystalline", 1000])
sections.append(["C2", "Monocrystalline", 1000])
sections.append([""])
sections.append([""])

# 7. Returns
sections.append(["RETURNS (KWp)"])
sections.append(["Customer", "Product Type", "Returns"])
sections.append(["C1", "Monocrystalline", 800])
sections.append(["C2", "Monocrystalline", 800])
sections.append([""])
sections.append([""])

# 8. Technical Parameters
sections.append(["TECHNICAL PARAMETERS"])
sections.append(["Product Type", "Weight (kg/KWp)"])
sections.append(["Monocrystalline", 11.0])
sections.append([""])
sections.append(["Facility Type", "Code", "Yield/Efficiency"])
sections.append(["Refurbishment", "F1", 0.90])
sections.append(["Recycling", "R1", 0.95])
sections.append([""])
sections.append([""])

# 9. Quality Mix Constraints
sections.append(["QUALITY MIX CONSTRAINTS"])
sections.append(["Constraint Type", "Maximum Percentage"])
sections.append(["Reuse Capacity", 0.20])
sections.append(["Refurbishment Capacity", 0.40])
sections.append([""])
sections.append([""])

# 10. Bill of Materials
sections.append(["BILL OF MATERIALS (kg per KWp)"])
sections.append(["Product Type", "Material", "Quantity"])
sections.append(["Monocrystalline", "Glass", 8.0])
sections.append(["Monocrystalline", "Aluminum", 1.5])
sections.append(["Monocrystalline", "Silicon", 0.5])
sections.append(["Monocrystalline", "Plastic", 0.8])
sections.append(["Monocrystalline", "Copper", 0.2])
sections.append([""])
sections.append([""])

# 11. Capacities
sections.append(["FACILITY CAPACITIES"])
sections.append(["Facility Type", "Code", "Capacity", "Unit"])
sections.append(["Plant", "P1", 10000, "KWp"])
sections.append(["Collection Center", "O1", 100000, "kg"])
sections.append(["Refurbishment Center", "F1", 50000, "kg"])
sections.append(["Recycling Center", "R1", 50000, "kg"])
sections.append([""])
sections.append([""])

# 12. Revenues - Products
sections.append(["PRODUCT REVENUES (€)"])
sections.append(["Product Type", "Revenue Type", "Revenue per KWp"])
sections.append(["Monocrystalline", "Reuse", 90])
sections.append(["Monocrystalline", "Refurbished", 110])
sections.append([""])
sections.append([""])

# 13. Revenues - Materials
sections.append(["MATERIAL REVENUES (€/kg)"])
sections.append(["Material", "Revenue per kg"])
sections.append(["Glass", 0.08])
sections.append(["Aluminum", 1.80])
sections.append(["Silicon", 12.0])
sections.append(["Plastic", 0.15])
sections.append(["Copper", 6.50])
sections.append([""])
sections.append([""])

# 14. Distance Matrix
sections.append(["DISTANCE MATRIX (km)"])
sections.append(["From", "To", "Distance"])
sections.append(["P1", "C1", 50])
sections.append(["P1", "C2", 50])
sections.append(["C1", "O1", 50])
sections.append(["C2", "O1", 50])
sections.append(["O1", "C1", 50])
sections.append(["O1", "C2", 50])
sections.append(["O1", "F1", 50])
sections.append(["O1", "R1", 50])
sections.append(["O1", "L1", 50])
sections.append(["F1", "P1", 50])
sections.append(["R1", "S1", 50])
sections.append([""])
sections.append([""])

# 15. Emissions Factors
sections.append(["EMISSIONS FACTORS (kg CO2e)"])
sections.append(["Activity Type", "Code", "Emissions Factor", "Unit"])
sections.append(["Production", "P1", 450, "per KWp"])
sections.append(["Collection", "O1", 5, "per KWp"])
sections.append(["Refurbishing", "F1", 30, "per KWp"])
sections.append(["Recycling", "R1", 1.5, "per kg"])
sections.append(["Disposal", "L1", 0.5, "per kg"])
sections.append(["Transport", "All", 0.00006, "per kg-km"])
sections.append([""])
sections.append([""])

# 16. Model Configuration
sections.append(["MODEL CONFIGURATION"])
sections.append(["Parameter", "Value", "Description"])
sections.append(["Epsilon Limit", 50000, "Maximum allowed emissions (kg CO2e)"])
sections.append(["Minimize Emissions Only", "FALSE", "TRUE to minimize emissions only"])

# Write to CSV
with open('circular_supply_chain_germany.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerows(sections)

print("✓ Excel template generated: circular_supply_chain_germany.csv")
print("You can now open it in Excel or any spreadsheet software!")