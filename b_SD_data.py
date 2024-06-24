import os
import pandas as pd

def read_data(datafolder, example):
    curPath = os.path.join(os.path.abspath(os.path.curdir), 'data', datafolder)

    # Read CSV files after defining file paths
    hourly_demand = pd.read_csv(os.path.join(curPath, 'sd_demand.csv'), header=0)
    sd_ic_line = pd.read_csv(os.path.join(curPath, 'sd_ic_line.csv'), header=0)
    sd_vc_line = pd.read_csv(os.path.join(curPath, 'sd_vc_line.csv'), header=0)
    sd_pre_cap = pd.read_csv(os.path.join(curPath, 'sd_pre_cap.csv'), header=0)
    
    scenario_indicator_gen_n1 = pd.read_csv(os.path.join(curPath, 'sd_ind_gen_n1.csv'), header=0)
    scenario_indicator_gen_n2 = pd.read_csv(os.path.join(curPath, 'sd_ind_gen_n2.csv'), header=0)
    prob_state = pd.read_csv(os.path.join(curPath, 'sd_prob.csv'), header=0)
    state_indicator_gen = pd.read_csv(os.path.join(curPath, 'sd_state_ind_gen.csv'), header=0)
    state_indicator_backup = pd.read_csv(os.path.join(curPath, 'sd_state_ind_backup.csv'), header=0)
    
    d = {}
    
    d['ND'] = 4     # Number of nodes
    d['LN'] = 5     # Number of lines
    d['TN'] = 5     # Number of planning periods (10-year planning, 5 interval)
    d['NN'] = 4     # Number of representative days (4 average demand from each seaseon)
    d['BN'] = 12    # Number of subperiods (24 hours, 12 interval)
    d['ST'] = 32    # Number of states

    if example == 'n-1':
        d['SC'] = 100   # Number of scenarios
        
    if example == 'n-2':
        d['SC'] = 200   # Number of scenarios
        
    if example == 'dual-no' or example == 'dual-yes':
        d['SC'] = 100            
    
    # SETS
    d['node'] = list(range(1,d['ND']+1))
    d['generator'] = ['ng1','ng2','ng3','ng-p']
    d['gen_pn'] = ['ng-p']
    d['gen_ex'] = ['ng1','ng2','ng3']
    d['line'] = list(range(1,d['LN']+1))
    d['line_pn'] = [2,3,4,5]
    d['line_ex'] = [1]
    d['year'] = list(range(1,d['TN']+1))
    d['rpdn'] = list(range(1,d['NN']+1))
    d['sub'] = list(range(1,d['BN']+1))
    d['scenario'] = list(range(1,d['SC']+1))
    d['state'] = list(range(1,d['ST']+1))
        
    # INDEXED SETS    
    d['line_to_node'] = {1: [2,3], 2: [], 3: [], 4:[1,4,5]}
    d['line_fr_node'] = {1: [1], 2: [2,4], 3: [3,5], 4:[]}
    d['node_npn_gen'] = {1: ['ng-p'], 2: [], 3: [], 4: ['ng-p']}    


    # PARAMETERS
    d['weight_time'] = {n: 91.25 for n in d['rpdn']}
    d['operation_time'] = {b: 2 for b in d['sub']}
    d['min_ins_cap'] = {k: 10 for k in d['gen_pn']}
    d['max_ins_cap'] = {k: 1500 for k in d['gen_pn']} 
    d['min_line'] = {l: 10 for l in d['line_pn']}
    d['max_line'] = {l: 1500 for l in d['line_pn']}

    d['load_demand'] = {}
    for a in range(hourly_demand.shape[0]):
        i = hourly_demand['i'].loc[a]
        t = hourly_demand['t'].loc[a]
        n = hourly_demand['n'].loc[a]
        b = hourly_demand['b'].loc[a]
        demand = hourly_demand['D'].loc[a]
        d['load_demand'][(i,t,n,b)] = demand
        
    d['min_opt_dpt'] = {k: 0.15 for k in d['generator']}
    d['max_opt_dpt'] = {k: 0.85 for k in d['generator']}
    d['ramp_up'] = {k: 0.7 for k in d['generator']}    
    d['ramp_down'] = {k: 0.7 for k in d['generator']}

    d['pre_cap'] = {}
    for a in range(sd_pre_cap.shape[0]):
        i = sd_pre_cap['i'].loc[a]
        k = sd_pre_cap['k'].loc[a]
        pre_cap = sd_pre_cap['pre_cap'].loc[a]
        d['pre_cap'][(i,k)] = pre_cap    

    d['pre_cap_line'] = {}
    d['pre_cap_line'][1] = 300
    
    d['unit_IC'] = {}  # M$/MW
    for k in d['gen_pn']:
        d['unit_IC'][k,1] = 0.347
        d['unit_IC'][k,2] = 0.337
        d['unit_IC'][k,3] = 0.326
        d['unit_IC'][k,4] = 0.316
        d['unit_IC'][k,5] = 0.305
                 
    d['unit_IC_line'] = {}  # M$/MW
    for a in range(sd_ic_line.shape[0]):
        l = sd_ic_line['l'].loc[a]
        t = sd_ic_line['t'].loc[a]
        IC_line = sd_ic_line['IC_line'].loc[a]
        d['unit_IC_line'][(l,t)] = IC_line

    d['unit_FC'] = {} # M$/MW
    for k in d['generator']:
        d['unit_FC'][k,1] = 0.026
        d['unit_FC'][k,2] = 0.025
        d['unit_FC'][k,3] = 0.024
        d['unit_FC'][k,4] = 0.024
        d['unit_FC'][k,5] = 0.023
        
    d['unit_FC_line'] = {} # M$/MW
    for l in d['line']:
        d['unit_FC_line'][l,1] = 0.005
        d['unit_FC_line'][l,2] = 0.0049
        d['unit_FC_line'][l,3] = 0.0047
        d['unit_FC_line'][l,4] = 0.0045
        d['unit_FC_line'][l,5] = 0.0044
        
    d['unit_VC'] = {} # $/MWh (including fuel cost)
    for k in d['generator']:
        d['unit_VC'][k,1] = 9.275
        d['unit_VC'][k,2] = 8.997
        d['unit_VC'][k,3] = 8.719
        d['unit_VC'][k,4] = 8.440
        d['unit_VC'][k,5] = 8.162
        
    d['unit_VC_line'] = {} # $/MWh
    for a in range(sd_vc_line.shape[0]):
        l = sd_vc_line['l'].loc[a]
        t = sd_vc_line['t'].loc[a]
        VC_line = sd_vc_line['VC_line'].loc[a]
        d['unit_VC_line'][(l,t)] = VC_line  
    
    d['OG_penalty'] = 10


    # Bounds
    d['ub_IC'] = {}
    for k in d['gen_pn']:
        for t in d['year']:
            d['ub_IC'][k,t] = d['max_ins_cap'][k] * d['unit_IC'][k,t]    
    
    d['ub_ICL'] = {}
    for l in d['line_pn']:
        for t in d['year']:
            d['ub_ICL'][l,t] = d['max_line'][l] * d['unit_IC_line'][l,t]    

    
    

    ###########################################################################################
    ##   N-k reliability method 
    
    if example == 'n-1' or example == 'dual-no' or example == 'dual-yes':
        d['scenario_indicator_gen'] = {}
        for a in range(scenario_indicator_gen_n1.shape[0]):
            i = scenario_indicator_gen_n1['i'].loc[a]
            k = scenario_indicator_gen_n1['k'].loc[a]
            t = scenario_indicator_gen_n1['t'].loc[a]
            n = scenario_indicator_gen_n1['n'].loc[a]
            sc = scenario_indicator_gen_n1['sc'].loc[a]
            sc_gen = scenario_indicator_gen_n1['sc_gen'].loc[a]
            d['scenario_indicator_gen'][(i,k,t,n,sc)] = sc_gen
                
        d['scenario_rate'] = {sc: 0.01 for sc in d['scenario']}

    if example == 'n-2':
        d['scenario_indicator_gen'] = {}
        for a in range(scenario_indicator_gen_n2.shape[0]):
            i = scenario_indicator_gen_n2['i'].loc[a]
            k = scenario_indicator_gen_n2['k'].loc[a]
            t = scenario_indicator_gen_n2['t'].loc[a]
            n = scenario_indicator_gen_n2['n'].loc[a]
            sc = scenario_indicator_gen_n2['sc'].loc[a]
            sc_gen = scenario_indicator_gen_n2['sc_gen'].loc[a]
            d['scenario_indicator_gen'][(i,k,t,n,sc)] = sc_gen
                
        d['scenario_rate'] = {sc: 0.005 for sc in d['scenario']}        
        
    d['scenario_indicator_line'] = {(l,t,n,sc): 1 for l in d['line_ex'] for t in d['year'] for n in d['rpdn'] for sc in d['scenario']}
    

    ###########################################################################################
    ##   Probability of failure method 

    d['min_ins_cap_backup'] = {k: 10 for k in d['gen_ex']}
    d['max_ins_cap_backup'] = {k: 1500 for k in d['gen_ex']}   

    d['unit_IC_backup'] = {}  # M$/MW
    for k in d['gen_ex']:
        d['unit_IC_backup'][k,1] = 0.416
        d['unit_IC_backup'][k,2] = 0.404
        d['unit_IC_backup'][k,3] = 0.391
        d['unit_IC_backup'][k,4] = 0.379
        d['unit_IC_backup'][k,5] = 0.366

    d['unit_FC_backup'] = {} # M$/MW
    for k in d['gen_ex']:
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
        d['state_indicator_backup'] = {(i,k,st): 1 for i in d['node'] for k in d['gen_ex'] for st in d['state']}       
    
    d['state_indicator_line'] = {(l,st): 1 for l in d['line_ex'] for st in d['state']}    


    # Bounds
    d['ub_IC_backup'] = {}
    for k in d['gen_ex']:
        for t in d['year']:
            d['ub_IC_backup'][k,t] = d['max_ins_cap_backup'][k] * d['unit_IC_backup'][k,t]            
    
    
    return d