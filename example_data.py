import os
import pandas as pd

def read_data(datafolder, n_k=None, failure=None):
    curPath = os.path.join(os.path.abspath(os.path.curdir), 'data2', datafolder)

    # Read CSV files after defining file paths
    capacity_factor = pd.read_csv(os.path.join(curPath, 'capacity_factor.csv'), header=0)
    demand = pd.read_csv(os.path.join(curPath, 'demand.csv'), header=0)
    fc_gen = pd.read_csv(os.path.join(curPath, 'fc_gen.csv'), header=0)
    fc_line = pd.read_csv(os.path.join(curPath, 'fc_line.csv'), header=0)
    ic_gen = pd.read_csv(os.path.join(curPath, 'ic_gen.csv'), header=0)
    ic_line = pd.read_csv(os.path.join(curPath, 'ic_line.csv'), header=0)
    vc_gen = pd.read_csv(os.path.join(curPath, 'vc_gen.csv'), header=0)
    vc_line = pd.read_csv(os.path.join(curPath, 'vc_line.csv'), header=0)
    max_cap_line = pd.read_csv(os.path.join(curPath, 'max_cap_line.csv'), header=0)
    max_cap_gen = pd.read_csv(os.path.join(curPath, 'max_cap_gen.csv'), header=0)
    min_cap_line = pd.read_csv(os.path.join(curPath, 'min_cap_line.csv'), header=0)
    min_cap_gen = pd.read_csv(os.path.join(curPath, 'min_cap_gen.csv'), header=0)
    max_opt_gen = pd.read_csv(os.path.join(curPath, 'max_opt_gen.csv'), header=0)
    min_opt_gen = pd.read_csv(os.path.join(curPath, 'min_opt_gen.csv'), header=0)
    weight = pd.read_csv(os.path.join(curPath, 'weight.csv'), header=0)
    operation_time = pd.read_csv(os.path.join(curPath, 'operation_time.csv'), header=0)
    pre_cap_line = pd.read_csv(os.path.join(curPath, 'pre_cap_line.csv'), header=0)
    pre_cap_gen = pd.read_csv(os.path.join(curPath, 'pre_cap_gen.csv'), header=0)
    prob = pd.read_csv(os.path.join(curPath, 'prob.csv'), header=0)
    ramp_down = pd.read_csv(os.path.join(curPath, 'ramp_down.csv'), header=0)
    ramp_up = pd.read_csv(os.path.join(curPath, 'ramp_up.csv'), header=0)
    scenario_indicator_gen_n1 = pd.read_csv(os.path.join(curPath, 'scenario_indicator_gen_n1.csv'), header=0)
    scenario_indicator_gen_n2 = pd.read_csv(os.path.join(curPath, 'scenario_indicator_gen_n2.csv'), header=0)
    scenario_indicator_line_n1 = pd.read_csv(os.path.join(curPath, 'scenario_indicator_line_n1.csv'), header=0)
    scenario_indicator_line_n2 = pd.read_csv(os.path.join(curPath, 'scenario_indicator_line_n2.csv'), header=0)
    scenario_rate_n1 = pd.read_csv(os.path.join(curPath, 'scenario_rate_n1.csv'), header=0)
    scenario_rate_n2 = pd.read_csv(os.path.join(curPath, 'scenario_rate_n1.csv'), header=0)
    state_indicator_gen = pd.read_csv(os.path.join(curPath, 'state_indicator_gen.csv'), header=0)
    state_indicator_backup = pd.read_csv(os.path.join(curPath, 'state_indicator_backup.csv'), header=0)
    

    d = {}
    
    if datafolder == "Illustrative":
        d['ND'] = 3     # Number of nodes
        d['LN'] = 3     # Number of lines
        d['TN'] = 3     # Number of planning periods 
        d['NN'] = 4     # Number of representative days (4 average demand from each seaseon)
        d['BN'] = 24    # Number of subperiods 
        
        if n-k:
        if example == 'n-1':
            d['SC'] = 36   # Number of scenarios
            
        elif example == 'n-2':
            d['SC'] = 36   # Number of scenarios
            
        else:
            d['ST'] = 8    # Number of states        


        # SETS
        d['node'] = list(range(1,d['ND']+1))
        d['generator'] = ['ng']
        d['dispatch_gen'] = ['ng']
        d['renewable_gen'] = []
        d['gen_pn'] = ['ng']
        d['dis_pn'] = ['ng'] 
        d['res_pn'] = [] 
        d['gen_ex'] = []
        d['line'] = list(range(1,d['LN']+1))
        d['line_pn'] = list(range(1,d['LN']+1))
        d['line_ex'] = []
        d['year'] = list(range(1,d['TN']+1))
        d['rpdn'] = list(range(1,d['NN']+1))
        d['sub'] = list(range(1,d['BN']+1))
        d['scenario'] = list(range(0,d['SC']+1))
        d['state'] = list(range(1,d['ST']+1))
            
        # INDEXED SETS    
        d['line_to_node'] = {1: [3], 2: [1,2], 3: []}
        d['line_fr_node'] = {1: [1], 2: [], 3: [2,3]}
        d['node_npn_gen'] = {1: [], 2: [], 3: []}    



    if datafolder == "San Diego":
        d['ND'] = 4     # Number of nodes
        d['LN'] = 5     # Number of lines
        d['TN'] = 5     # Number of planning periods (10-year planning, 5 interval)
        d['NN'] = 4     # Number of representative days (4 average demand from each seaseon)
        d['BN'] = 12    # Number of subperiods (24 hours, 12 interval)

        if example == 'n-1':
            d['SC'] = 80   # Number of scenarios

            d['scenario_indicator_gen'] = {(row['i'], row['k'], row['t'], row['n'], row['sc']): 
                                           row['sc_gen'] for _, row in scenario_indicator_gen_n1.iterrows()}   
            d['scenario_rate'] = {row['sc']: row['sc_rate'] for _, row in scenario_rate_n1.iterrows()}
            d['scenario_indicator_line'] = {(row['l'], row['t'], row['n'], row['sc']): 
                                           row['sc_line'] for _, row in scenario_indicator_line_n1.iterrows()}   
                
            
        elif example == 'n-2':
            d['SC'] = 120   # Number of scenarios
            d['scenario_indicator_gen'] = {(row['i'], row['k'], row['t'], row['n'], row['sc']): 
                                           row['sc_gen'] for _, row in scenario_indicator_gen_n2.iterrows()}   
            d['scenario_rate'] = {row['sc']: row['sc_rate'] for _, row in scenario_rate_n2.iterrows()}
            d['scenario_indicator_line'] = {(row['l'], row['t'], row['n'], row['sc']): 
                                           row['sc_line'] for _, row in scenario_indicator_line_n2.iterrows()}   

        elif example == 'dual-no':
            d['ST'] = 16    # Number of states

        
        elif example == 'dual-yes':
            d['ST'] = 16    # Number of states

        
        # SETS
        d['node'] = list(range(1,d['ND']+1))
        d['generator'] = ['ng1','ng2','ng3','ng-p','wt-p']
        d['dispatch_gen'] = ['ng1','ng2','ng3','ng-p']
        d['renewable_gen'] = ['wt-p']
        d['gen_pn'] = ['ng-p','wt-p']
        d['dis_pn'] = ['ng-p'] 
        d['res_pn'] = ['wt-p'] 
        d['gen_ex'] = ['ng1','ng2','ng3']
        d['line'] = list(range(1,d['LN']+1))
        d['line_pn'] = [2,3,4,5]
        d['line_ex'] = [1]
        d['year'] = list(range(1,d['TN']+1))
        d['rpdn'] = list(range(1,d['NN']+1))
        d['sub'] = list(range(1,d['BN']+1))
        d['scenario'] = list(range(0,d['SC']+1))
        d['state'] = list(range(1,d['ST']+1))
            
        # INDEXED SETS    
        d['line_to_node'] = {1: [2,3], 2: [], 3: [], 4:[1,4,5]}
        d['line_fr_node'] = {1: [1], 2: [2,4], 3: [3,5], 4:[]}
        d['node_npn_gen'] = {1: [], 2: [], 3: [], 4: []}    


    # PARAMETERS
    d['weight_time'] = {row['n']: row['weight'] for _, row in weight.iterrows()}
    d['operation_time'] = {row['b']: row['opt_time'] for _, row in operation_time.iterrows()}
    d['min_ins_cap'] = {row['k']: row['min_cap'] for _, row in min_cap_gen.iterrows()}
    d['max_ins_cap'] = {row['k']: row['max_cap'] for _, row in max_cap_gen.iterrows()}
    d['min_line'] = {row['l']: row['min_cap'] for _, row in min_cap_line.iterrows()}
    d['max_line'] = {row['l']: row['max_cap'] for _, row in max_cap_line.iterrows()}
    d['load_demand'] = {(row['i'], row['t'], row['n'], row['b']): row['D'] for _, row in demand.iterrows()}   
    d['capacity_factor'] = {(row['i'], row['t'], row['n'], row['b']): row['CPF'] for _, row in capacity_factor.iterrows()}
    d['min_opt_dpt'] = {row['k']: row['min_opt'] for _, row in min_opt_gen.iterrows()}
    d['max_opt_dpt'] = {row['k']: row['max_opt'] for _, row in max_opt_gen.iterrows()}
    d['ramp_up'] = {row['k']: row['ramp_up'] for _, row in ramp_up.iterrows()}
    d['ramp_down'] = {row['k']: row['ramp_down'] for _, row in ramp_down.iterrows()}
    d['pre_cap'] = {(row['i'], row['k']): row['pre_cap'] for _, row in pre_cap_gen.iterrows()}   
    d['pre_cap_line'] = {row['l']: row['pre_cap'] for _, row in pre_cap_line.iterrows()}  


    d['unit_IC'] = {(row['k'], row['t']): row['ic_gen'] for _, row in ic_gen.iterrows()}         # M$/MW
    d['unit_IC_line'] = {(row['l'], row['t']): row['ic_line'] for _, row in ic_line.iterrows()}  # M$/MW
    d['unit_FC'] = {(row['k'], row['t']): row['fc_gen'] for _, row in fc_gen.iterrows()}         # M$/MW                
    d['unit_FC_line'] = {(row['l'], row['t']): row['fc_line'] for _, row in fc_line.iterrows()}  # M$/MW
    d['unit_VC'] = {(row['k'], row['t']): row['vc_gen'] for _, row in vc_gen.iterrows()}         # $/MWh (including fuel cost)
    d['unit_VC_line'] = {(row['l'], row['t']): row['vc_line'] for _, row in vc_line.iterrows()}  # $/MWh

        
    d['res_target'] = {}
    d['res_target'][1] = 0.12
    d['res_target'][2] = 0.24
    d['res_target'][3] = 0.36
    d['res_target'][4] = 0.48
    d['res_target'][5] = 0.60

    # Bounds
    d['ub_IC'] = {}
    for k in d['gen_pn']:
        for t in d['year']:
            d['ub_IC'][k,t] = d['max_ins_cap'][k] * d['unit_IC'][k,t]    
    
    d['ub_ICL'] = {}
    for l in d['line_pn']:
        for t in d['year']:
            d['ub_ICL'][l,t] = d['max_line'][l] * d['unit_IC_line'][l,t]    

    d['ub_IC_backup'] = {}
    for k in d['dis_pn']:
        for t in d['year']:
            d['ub_IC_backup'][k,t] = d['max_ins_cap_backup'][k] * d['unit_IC_backup'][k,t]            

    

    ###########################################################################################
    ##   Probability of failure method 

    d['min_ins_cap_backup'] = {k: 10 for k in d['dis_pn']}
    d['max_ins_cap_backup'] = {k: 800 for k in d['dis_pn']}   

    d['unit_IC_backup'] = {}  # M$/MW
    for k in d['dis_pn']:
        d['unit_IC_backup'][k,1] = 0.42
        d['unit_IC_backup'][k,2] = 0.4074
        d['unit_IC_backup'][k,3] = 0.3948
        d['unit_IC_backup'][k,4] = 0.3822
        d['unit_IC_backup'][k,5] = 0.3696

    d['unit_FC_backup'] = {} # M$/MW
    for k in d['dis_pn']:
        d['unit_FC_backup'][k,1] = 0.031
        d['unit_FC_backup'][k,2] = 0.030
        d['unit_FC_backup'][k,3] = 0.029
        d['unit_FC_backup'][k,4] = 0.028
        d['unit_FC_backup'][k,5] = 0.027

    d['UD_penalty'] = 9

    d['prob'] = {}
    for a in range(prob_state.shape[0]):
        st = prob_state['st'].loc[a]
        prob = prob_state['prob'].loc[a]
        d['prob'][st] = prob
    
    d['state_indicator_gen'] = {}
    for a in range(state_indicator_gen.shape[0]):
        i = state_indicator_gen['i'].loc[a]
        k = state_indicator_gen['k'].loc[a]
        st = state_indicator_gen['st'].loc[a]
        st_gen = state_indicator_gen['state_gen'].loc[a]
        d['state_indicator_gen'][(i,k,st)] = st_gen

    if example == 'dual-no':
        d['state_indicator_backup'] = {}
        for a in range(state_indicator_backup.shape[0]):
            i = state_indicator_backup['i'].loc[a]
            k = state_indicator_backup['k'].loc[a]
            st = state_indicator_backup['st'].loc[a]
            st_backup = state_indicator_backup['state_backup'].loc[a]
            d['state_indicator_backup'][(i,k,st)] = st_backup

    if example == 'dual-yes':
        d['state_indicator_backup'] = {(i,k,st): 1 for i in d['node'] for k in d['dis_pn'] for st in d['state']}       
    
    d['state_indicator_line'] = {(l,st): 1 for l in d['line'] for st in d['state']}        
    
    
    return d