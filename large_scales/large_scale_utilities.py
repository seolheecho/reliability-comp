import pyomo.environ as pyo
from pyomo.environ import value
import pandas as pd
import csv

def solve_model(m, advanced, renewable, time_limit, abs_gap):
    import time

    opt = pyo.SolverFactory('gurobi')
    
    # Set up Gurobi's log file
    # log_file = "gurobi_log.txt"
    # opt.options['logfile'] = log_file

    opt.options['TimeLimit'] = time_limit
    opt.options['MIPGap'] = abs_gap
    opt.options['Threads'] = 8

    # Solve the model and track time
    start_time = time.time()
    m.results = opt.solve(m, tee=True)
    solve_time = time.time() - start_time

    print(f"\nSolve time: {solve_time:.2f} seconds")        



    # Print results to quickly check them
    if advanced in ['no','reserve']:
        for t in m.year:
            print("Demand every year", round(sum(m.weight_time[n] * m.operation_time[b] * m.load_demand[i,t,n,b] 
                                                 for i in m.node for n in m.rpdn for b in m.sub), 3),
                  "Over generation", round(sum(m.weight_time[n] * m.operation_time[b] * m.over_gen[i,t,n,b].value 
                                               for i in m.node for n in m.rpdn for b in m.sub), 2), 
                  "Dispatch_power", round(sum(m.weight_time[n] * m.operation_time[b] * m.ppd[i,k,t,n,b].value 
                                              for i in m.node for k in m.dispatch_gen for n in m.rpdn for b in m.sub), 2)
            )

            if renewable == True:
                print("RES_power", round(sum(m.weight_time[n] * m.operation_time[b] * m.ppd[i,k,t,n,b].value 
                                             for i in m.node for k in m.renewable_gen for n in m.rpdn for b in m.sub), 2)
                )    
        
        print("CAPEX", round(pyo.value(m.capital_expenditure()), 2), 
              "| IC_Gen", round(pyo.value(m.IC_generator()), 2), 
              "| IC_Line", round(pyo.value(m.IC_line()), 2), 
              "| OPEX", round(pyo.value(m.operating_expenses()), 2), 
              "| FC_Gen", round(pyo.value(m.FOC_generator()), 2), 
              "| FC_Line", round(pyo.value(m.FOC_line()), 2),
              "| VC_Gen", round(pyo.value(m.VOC_generator()), 2), 
              "| VC_Line", round(pyo.value(m.VOC_line()), 2)
        )    


    elif advanced in ['n-1','n-2']:
        for t in m.year:
            print("Demand every year", round(sum(m.scenario_rate[sc] * m.weight_time[n] * m.operation_time[b] * m.load_demand[i,t,n,b] 
                                                 for i in m.node for n in m.rpdn for b in m.sub for sc in m.scenario), 3),
                "Over generation", round(sum(m.scenario_rate[sc] * m.weight_time[n] * m.operation_time[b] * m.over_gen[i,t,n,b,sc].value 
                                             for i in m.node for n in m.rpdn for b in m.sub for sc in m.scenario), 2),
                "Dispatch_power", round(sum(m.scenario_rate[sc] * m.weight_time[n] * m.operation_time[b] * m.ppd[i,k,t,n,b,sc].value 
                                            for i in m.node for k in m.dispatch_gen for n in m.rpdn for b in m.sub for sc in m.scenario), 2)
            )
            
            if renewable == True:
                print("RES_power", round(sum(m.scenario_rate[sc] * m.weight_time[n] * m.operation_time[b] * m.ppd[i,k,t,n,b,sc].value 
                                             for i in m.node for k in m.renewable_gen for n in m.rpdn for b in m.sub for sc in m.scenario), 2)
                )
            
        print("CAPEX", round(pyo.value(m.capital_expenditure()), 2), 
              "| IC_Gen", round(pyo.value(m.IC_generator()), 2), 
              "| IC_Line", round(pyo.value(m.IC_line()), 2), 
              "| OPEX", round(pyo.value(m.operating_expenses()), 2), 
              "| FC_Gen", round(pyo.value(m.FOC_generator()), 2), 
              "| FC_Line", round(pyo.value(m.FOC_line()), 2), 
              "| VC_Gen", round(pyo.value(m.VOC_generator()), 2), 
              "| VC_Line", round(pyo.value(m.VOC_line()), 2)
            )        


    else:
        for t in m.year:
            print("LOLE every year", round(sum(m.weight_time[n] * m.TLOLE[i,t,n,b].value 
                                               for i in m.node for n in m.rpdn for b in m.sub), 3),
                "EENS every year", round(sum(m.weight_time[n] * m.operation_time[b] * m.TEENS[i,t,n,b].value 
                                             for i in m.node for n in m.rpdn for b in m.sub), 3),
                "Demand every year", round(sum(m.weight_time[n] * m.operation_time[b] * m.load_demand[i,t,n,b] 
                                               for i in m.node for n in m.rpdn for b in m.sub), 3),
                "Over generation", round(sum(m.prob[st] * m.weight_time[n] * m.operation_time[b] * m.over_gen[i,t,n,b,st].value 
                                             for i in m.node for n in m.rpdn for b in m.sub for st in m.state), 2),
                "Dispatch_power", round(sum(m.prob[st] * m.weight_time[n] * m.operation_time[b] * m.ppd[i,k,t,n,b,st].value 
                                            for i in m.node for k in m.dispatch_gen for n in m.rpdn for b in m.sub for st in m.state), 2)
            )
            
            if renewable == True:
                print("RES_power", round(sum(m.prob[st] * m.weight_time[n] * m.operation_time[b] * m.ppd[i,k,t,n,b,st].value 
                                             for i in m.node for k in m.renewable_gen for n in m.rpdn for b in m.sub for st in m.state), 2)
                )
            
        print("CAPEX", round(pyo.value(m.capital_expenditure()), 2), 
              "| IC_Gen", round(pyo.value(m.IC_generator()), 2), 
              "| IC_Line", round(pyo.value(m.IC_line()), 2), 
              "| IC_backup", round(pyo.value(m.IC_backup()), 2),
              "| OPEX", round(pyo.value(m.operating_expenses()), 2), 
              "| FC_Gen", round(pyo.value(m.FOC_generator()), 2), 
              "| FC_Line", round(pyo.value(m.FOC_line()), 2), 
              "| FC_backup", round(pyo.value(m.FOC_backup()), 2),
              "| VC_Gen", round(pyo.value(m.VOC_generator()), 2), 
              "| VC_Line", round(pyo.value(m.VOC_line()), 2), 
              "| VC_Backup", round(pyo.value(m.VOC_backup()), 2), 
              "| EENS penalty", round(pyo.value(m.EENS_penalties()), 2)
            )

    # Read the log file and write it to a .csv file
    # csv_file = f"gurobi_log_{advanced}.csv"
    # with open(log_file, "r") as infile, open(csv_file, "w", newline="") as outfile:
    #     writer = csv.writer(outfile)
    #     for line in infile:
    #         writer.writerow([line.strip()])

    return m



def export_results(datafolder, variables_dict, advanced, renewable):

    filename = f"{datafolder}_results_{advanced}_res_{renewable}.xlsx"

    # Create a Pandas Excel writer object to handle multiple sheets
    with pd.ExcelWriter(filename, engine="xlsxwriter") as writer:
        for var_name, variable in variables_dict.items():
            # Extract data from the Pyomo variable
            rows = []
            for index, var in variable.items():
                if var.value is not None:  # Check if the variable has an optimal value
                    rows.append(list(index) + [var.value])
            
            # Determine column names dynamically based on the index structure
            column_names = [f"{i+1}" for i in range(len(index))] + ["Value"]
            
            # Create a DataFrame for the variable
            df = pd.DataFrame(rows, columns=column_names)
            
            # Write the DataFrame to a new sheet in the Excel file
            df.to_excel(writer, sheet_name=var_name, index=False)



def export_results_congestion(datafolder, variables_dict, advanced, renewable):

    filename = f"{datafolder}_congestion_results_{advanced}_res_{renewable}.xlsx"

    # Create a Pandas Excel writer object to handle multiple sheets
    with pd.ExcelWriter(filename, engine="xlsxwriter") as writer:
        for var_name, variable in variables_dict.items():
            # Extract data from the Pyomo variable
            rows = []
            for index, var in variable.items():
                if var.value is not None:  # Check if the variable has an optimal value
                    rows.append(list(index) + [var.value])
            
            # Determine column names dynamically based on the index structure
            column_names = [f"{i+1}" for i in range(len(index))] + ["Value"]
            
            # Create a DataFrame for the variable
            df = pd.DataFrame(rows, columns=column_names)
            
            # Write the DataFrame to a new sheet in the Excel file
            df.to_excel(writer, sheet_name=var_name, index=False)


def solve_prob_model(m, renewable, time_limit, abs_gap):
    opt = pyo.SolverFactory('gurobi')
    
    # Set up Gurobi's log file
    log_file = "gurobi_log.txt"
    opt.options['logfile'] = log_file

    opt.options['TimeLimit'] = time_limit
    opt.options['MIPGap'] = abs_gap
    opt.options['Threads'] = 8

    m.results = opt.solve(m, tee=True)

    for t in m.year:
        print("LOLE every year", round(sum(m.weight_time[n] * m.TLOLE[i,t,n,b].value 
                                            for i in m.node for n in m.rpdn for b in m.sub), 3),
            "EENS every year", round(sum(m.weight_time[n] * m.operation_time[b] * m.TEENS[i,t,n,b].value 
                                            for i in m.node for n in m.rpdn for b in m.sub), 3),
            "Demand every year", round(sum(m.weight_time[n] * m.operation_time[b] * m.load_demand[i,t,n,b] 
                                            for i in m.node for n in m.rpdn for b in m.sub), 3),
            "Over generation", round(sum(m.prob[st] * m.weight_time[n] * m.operation_time[b] * m.over_gen[i,t,n,b,st].value 
                                            for i in m.node for n in m.rpdn for b in m.sub for st in m.state), 2),
            "Dispatch_power", round(sum(m.prob[st] * m.weight_time[n] * m.operation_time[b] * m.ppd[i,k,t,n,b,st].value 
                                        for i in m.node for k in m.dispatch_gen for n in m.rpdn for b in m.sub for st in m.state), 2)
        )
        
        if renewable == True:
            print("RES_power", round(sum(m.prob[st] * m.weight_time[n] * m.operation_time[b] * m.ppd[i,k,t,n,b,st].value 
                                            for i in m.node for k in m.renewable_gen for n in m.rpdn for b in m.sub for st in m.state), 2)
            )
        
    print("CAPEX", round(pyo.value(m.capital_expenditure()), 2), 
            "| IC_Gen", round(pyo.value(m.IC_generator()), 2), 
            "| IC_Line", round(pyo.value(m.IC_line()), 2), 
            "| IC_backup", round(pyo.value(m.IC_backup()), 2),
            "| FC_Gen", round(pyo.value(m.FOC_generator()), 2), 
            "| FC_Line", round(pyo.value(m.FOC_line()), 2), 
            "| FC_backup", round(pyo.value(m.FOC_backup()), 2),
            "| VC_Gen", round(pyo.value(m.VOC_generator()), 2), 
            "| VC_Line", round(pyo.value(m.VOC_line()), 2), 
            "| VC_Backup", round(pyo.value(m.VOC_backup()), 2), 
            "| EENS penalty", round(pyo.value(m.EENS_penalties()), 2)
        )

    return m
