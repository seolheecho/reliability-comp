import pyomo.environ as pyo
from pyomo.environ import value
import pandas as pd
import csv


def solve_model(m, advanced, time_limit=1000, abs_gap=0.01, threads=8):
    opt = pyo.SolverFactory('gurobi')
    
    # Set up Gurobi's log file
    log_file = "gurobi_log.txt"
    opt.options['logfile'] = log_file

    opt.options['TimeLimit'] = time_limit
    opt.options['MIPGap'] = abs_gap
    opt.options['Threads'] = threads

    m.results = opt.solve(m, tee=True)

    # Read the log file and write its contents to a .csv file
    # csv_file = "gurobi_log.csv"
    # with open(log_file, "r") as infile, open(csv_file, "w", newline="") as outfile:
    #     writer = csv.writer(outfile)
    #     for line in infile:
    #         writer.writerow([line.strip()])

    results = {}
    if advanced in [None, 'n-1', 'n-2']:
        tot_results = [m.cap_ins, m.cap_ins_line, m.cap_ava, m.cap_ava_line]

    else:
        tot_results = [m.cap_ins, m.cap_ins_line, m.cap_bn, m.cap_ava, m.cap_ava_line, m.cap_b]

    for var_group in tot_results:
        for key in var_group:
            var_name = var_group[key].name
            if var_name not in results:
                results[var_name] = []
            results[var_name].append(round(var_group[key].value, 2))
        

    df_results = pd.DataFrame(results)
    df_results_transpose = df_results.transpose()
    df_results_transpose.to_excel("opt_results.xlsx") 

    if advanced in [None, 'n-1', 'n-2']:
        for t in m.year:
            print("Demand every year", round(sum(m.weight_time[n] * m.operation_time[b] * m.load_demand[i,t,n,b] for i in m.node for n in m.rpdn for b in m.sub), 3),
                "RES_power", round(sum(m.weight_time[n] * m.operation_time[b] * m.ppd[i,k,t,n,b].value for i in m.node for k in m.renewable_gen for n in m.rpdn for b in m.sub), 2),  
                "DIS_power", round(sum(m.weight_time[n] * m.operation_time[b] * m.ppd[i,k,t,n,b].value for i in m.node for k in m.dispatch_gen for n in m.rpdn for b in m.sub), 2),
                "Over generation", round(sum(m.weight_time[n] * m.operation_time[b] * m.over_gen[i,t,n,b].value for i in m.node for n in m.rpdn for b in m.sub), 2)
            )    
        
        print("CAPEX", round(value(m.capital_expenditure()), 2), "| IC_Gen", round(value(m.IC_generator()), 2), "| IC_Line", round(value(m.IC_line()), 2), 
            "| OPEX", round(value(m.operating_expenses()), 2), "| FC_Gen", round(value(m.FOC_generator()), 2), "| FC_Line", round(value(m.FOC_line()), 2),
            "| VC_Gen", round(value(m.VOC_generator()), 2), "| VC_Line", round(value(m.VOC_line()), 2)
            )    

    else:
        for t in m.year:
            print("LOLE every year", round(sum(m.weight_time[n] * m.TLOLE[i,t,n,b].value for i in m.node for n in m.rpdn for b in m.sub), 3),
                "EENS every year", round(sum(m.weight_time[n] * m.operation_time[b] * m.TEENS[i,t,n,b].value for i in m.node for n in m.rpdn for b in m.sub), 3),
                "Demand every year", round(sum(m.weight_time[n] * m.operation_time[b] * m.load_demand[i,t,n,b] for i in m.node for n in m.rpdn for b in m.sub), 3),
                "Over generation", round(sum(m.prob[st] * m.weight_time[n] * m.operation_time[b] * m.over_gen[i,t,n,b,st].value for i in m.node for n in m.rpdn for b in m.sub for st in m.state), 2),
                "Dispatch_power", round(sum(m.prob[1] * m.weight_time[n] * m.operation_time[b] * m.ppd[i,k,t,n,b,1].value for i in m.node for k in m.dispatch_gen for n in m.rpdn for b in m.sub), 2),
                "RES_power", round(sum(m.prob[1] * m.weight_time[n] * m.operation_time[b] * m.ppd[i,k,t,n,b,1].value for i in m.node for k in m.renewable_gen for n in m.rpdn for b in m.sub), 2)
            )
            
        print("CAPEX", round(value(m.capital_expenditure()), 2), "| IC_Gen", round(value(m.IC_generator()), 2), "| IC_Line", round(value(m.IC_line()), 2), "| IC_backup", round(value(m.IC_backup()), 2),
            "| OPEX", round(value(m.operating_expenses()), 2), "| FC_Gen", round(value(m.FOC_generator()), 2), "| FC_Line", round(value(m.FOC_line()), 2), "| FC_backup", round(value(m.FOC_backup()), 2),
            "| VC_Gen", round(value(m.VOC_generator()), 2), "| VC_Line", round(value(m.VOC_line()), 2), "| VC_Backup", round(value(m.VOC_backup()), 2), "| EENS penalty", round(value(m.EENS_penalties()), 2)
            )

    return m