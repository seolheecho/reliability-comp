__author__ = "Seolhee Cho"

import pyomo.environ as pyo
from example_data import read_data
from utilities import solve_model


def n_k_reliability_model(data, renewable):
    
    m = pyo.ConcreteModel()
    
    # Sets   
    m.node = pyo.Set(initialize=data['node'])
    m.generator = pyo.Set(initialize=data['generator'])
    m.dispatch_gen = pyo.Set(initialize=data['dispatch_gen'])
    m.renewable_gen = pyo.Set(initialize=data['renewable_gen'])
    m.gen_pn = pyo.Set(within=m.generator, initialize=data['gen_pn'])
    m.dis_pn = pyo.Set(within=m.gen_pn, initialize=data['dis_pn'])    
    m.res_pn = pyo.Set(within=m.gen_pn, initialize=data['res_pn'])    
    m.gen_ex = pyo.Set(within=m.generator, initialize=data['gen_ex'])
    m.line = pyo.Set(initialize=data['line'])
    m.line_pn = pyo.Set(within=m.line, initialize=data['line_pn'])
    m.line_ex = pyo.Set(within=m.line, initialize=data['line_ex'])
    m.year = pyo.Set(initialize=data['year'])
    m.rpdn = pyo.Set(initialize=data['rpdn'])
    m.sub = pyo.Set(initialize=data['sub'])


    # Indexed Set
    m.line_to_node = pyo.Set(m.node, within=m.line, initialize=data['line_to_node'])
    m.line_fr_node = pyo.Set(m.node, within=m.line, initialize=data['line_fr_node'])
    m.node_npn_gen = pyo.Set(m.node, within=m.gen_pn, initialize=data['node_npn_gen'], 
                             doc='potential dispatchable generators not available in nodes')
    
    
    # Parameters
    m.weight_time = pyo.Param(m.rpdn, within=pyo.NonNegativeReals, initialize=data['weight_time'])
    m.operation_time = pyo.Param(m.sub, within=pyo.NonNegativeReals, initialize=data['operation_time'])
    m.min_ins_cap = pyo.Param(m.gen_pn, within=pyo.NonNegativeReals, initialize=data['min_ins_cap'])
    m.max_ins_cap = pyo.Param(m.gen_pn, within=pyo.NonNegativeReals, initialize=data['max_ins_cap'])
    m.min_line = pyo.Param(m.line_pn, within=pyo.NonNegativeReals, initialize=data['min_line'])
    m.max_line = pyo.Param(m.line_pn, within=pyo.NonNegativeReals, initialize=data['max_line'])
    m.load_demand = pyo.Param(m.node, m.year, m.rpdn, m.sub, within=pyo.NonNegativeReals, initialize=data['load_demand'])
    m.capacity_factor = pyo.Param(m.node, m.year, m.rpdn, m.sub, within=pyo.NonNegativeReals, initialize=data['capacity_factor'])
    m.min_opt_dpt = pyo.Param(m.dispatch_gen, within=pyo.NonNegativeReals, initialize=data['min_opt_dpt'])
    m.max_opt_dpt = pyo.Param(m.dispatch_gen, within=pyo.NonNegativeReals, initialize=data['max_opt_dpt'])
    m.ramp_up = pyo.Param(m.dispatch_gen, within=pyo.NonNegativeReals, initialize=data['ramp_up'])
    m.ramp_down = pyo.Param(m.dispatch_gen, within=pyo.NonNegativeReals, initialize=data['ramp_down'])
    m.pre_cap = pyo.Param(m.node, m.gen_ex, within=pyo.NonNegativeReals, initialize=data['pre_cap'])
    m.pre_cap_line = pyo.Param(m.line_ex, within=pyo.NonNegativeReals, initialize=data['pre_cap_line'])

    m.unit_IC = pyo.Param(m.gen_pn, m.year, within=pyo.NonNegativeReals, initialize=data['unit_IC']) # unit: M$/MW
    m.unit_IC_line = pyo.Param(m.line_pn, m.year, within=pyo.NonNegativeReals, initialize=data['unit_IC_line']) # unit: M$/MW 
    m.unit_FC = pyo.Param(m.generator, m.year, within=pyo.NonNegativeReals, initialize=data['unit_FC']) # unit: M$/MW 
    m.unit_FC_line = pyo.Param(m.line, m.year, within=pyo.NonNegativeReals, initialize=data['unit_FC_line']) # unit: M$/MW    
    m.unit_VC = pyo.Param(m.generator, m.year, within=pyo.NonNegativeReals, initialize=data['unit_VC'])   # unit: $/MWh  
    m.unit_VC_line = pyo.Param(m.line, m.year, within=pyo.NonNegativeReals, initialize=data['unit_VC_line'])   # unit: $/MWh
    m.res_target = pyo.Param(m.year, within=pyo.NonNegativeReals, initialize=data['res_target'])
   
    # Bounds
    def _bounds_cap_ins_rule(m, i, k, t):
        return (0, m.max_ins_cap[k])  
    
    def _bounds_cap_ins_line_rule(m, l, t):
        return (0, m.max_line[l])   
   
    m.ub_IC = pyo.Param(m.gen_pn, m.year, within=pyo.NonNegativeReals, initialize=data['ub_IC']) 
    def _bounds_IC_rule(m, i, k, t):
        return (0, m.ub_IC[k,t]) 
 
    m.ub_ICL = pyo.Param(m.line_pn, m.year, within=pyo.NonNegativeReals, initialize=data['ub_ICL']) 
    def _bounds_ICL_rule(m, l, t):
        return (0, m.ub_ICL[l,t])         
    

    # Non-negative variables  
    m.cap_ins = pyo.Var(m.node, m.gen_pn, m.year, bounds=_bounds_cap_ins_rule, within=pyo.NonNegativeReals, doc='Installed capacity of generators')
    m.cap_ins_line = pyo.Var(m.line_pn, m.year, bounds=_bounds_cap_ins_line_rule, within=pyo.NonNegativeReals, doc='Installed capacity of lines')
    m.cap_ava = pyo.Var(m.node, m.generator, m.year, within=pyo.NonNegativeReals, doc='Available capacity of generators')
    m.cap_ava_line = pyo.Var(m.line, m.year, within=pyo.NonNegativeReals, doc='Available capacity of lines')
    m.IC = pyo.Var(m.node, m.gen_pn, m.year, bounds=_bounds_IC_rule, within=pyo.NonNegativeReals, doc='Investment cost of generator')
    m.ICL = pyo.Var(m.line_pn, m.year, bounds=_bounds_ICL_rule, within=pyo.NonNegativeReals, doc='Investment cost of transmission lines')
    
    
    
    # CONSTRAINTS
    ############################################################################################ 
    ##                Investment of generators, batteries, and transmission lines             ##
    ############################################################################################      
 
    ## Installation of generators
    @m.Disjunct(m.node, m.gen_pn, m.year)
    def gen_install(disj, i, k, t):
       disj.install_cap_res1 = pyo.Constraint(expr= m.min_ins_cap[k] <= m.cap_ins[i,k,t])
       disj.install_cap_res2 = pyo.Constraint(expr= m.cap_ins[i,k,t] <= m.max_ins_cap[k])
       disj.invest_cost_res =  pyo.Constraint(expr= m.IC[i,k,t] == m.unit_IC[k,t] * m.cap_ins[i,k,t])
    
    @m.Disjunct(m.node, m.gen_pn, m.year)
    def gen_install_no(outer, i, k, t):
        outer.invest_cost_res_no = pyo.Constraint(expr= m.cap_ins[i,k,t] == 0)
        outer.install_cap_res_no = pyo.Constraint(expr= m.IC[i,k,t] == 0)
        
    @m.Disjunction(m.node, m.gen_pn, m.year)
    def Ornot_gen_install(m, i, k, t):
        return [m.gen_install[i,k,t], m.gen_install_no[i,k,t]]
    
    
    ## Assumptions
    ## For the generators do not exist in a specific node, assume that it is not possible to install them
    for i in m.node:
        for k in m.node_npn_gen[i]:
            for t in m.year:
                m.gen_install[i,k,t].indicator_var.fix(False)  
       
       
    
    ## Installation of transmission lines
    @m.Disjunct(m.line_pn, m.year)
    def line_install(disj, l, t):
        disj.ins_cap_lb = pyo.Constraint(expr= m.min_line[l] <= m.cap_ins_line[l,t])
        disj.ins_cap_ub = pyo.Constraint(expr= m.cap_ins_line[l,t] <= m.max_line[l])
        disj.invest_cost = pyo.Constraint(expr= m.ICL[l,t] == m.unit_IC_line[l,t] * m.cap_ins_line[l,t])
    # m.line_install.pprint()

    @m.Disjunct(m.line_pn, m.year)
    def line_install_no(disj, l, t):
        disj.ins_cap_no = pyo.Constraint(expr= m.cap_ins_line[l,t] == 0)
        disj.invest_cost_no = pyo.Constraint(expr= m.ICL[l,t] == 0)
        
    @m.Disjunction(m.line_pn, m.year)
    def Ornot_line_install(m, l, t):
        return [m.line_install[l,t], m.line_install_no[l,t]]    
    

    ## Available capacity of generators         
    @m.Constraint(m.node, m.gen_pn, m.year)
    def availability_capacity_gen_pn(m, i, k, t):
        return m.cap_ava[i,k,t] == sum(m.cap_ins[i,k,tq] for tq in range(1,t+1))
    
    @m.Constraint(m.node, m.gen_ex, m.year)
    def availability_capacity_gen_ex(m, i, k, t):
        return m.cap_ava[i,k,t] == m.pre_cap[i,k]
    
    
    ## Available capacity of transmission lines    
    @m.Constraint(m.line_pn, m.year)
    def available_capacity_line_pn(m, l, t):
        return m.cap_ava_line[l,t] == sum(m.cap_ins_line[l,tp] for tp in range(1, t+1))

    @m.Constraint(m.line_ex, m.year)
    def available_capacity_line_ex(m, l, t):
        return m.cap_ava_line[l,t] == m.pre_cap_line[l]
      


    ############################################################################################ 
    ##                    Operation of generators and transmission lines                      ##
    ############################################################################################  

    m.scenario = pyo.Set(initialize=data['scenario'])   
    
    m.scenario_indicator_gen = pyo.Param(m.node, m.dis_pn, m.year, m.rpdn, m.scenario, within=pyo.NonNegativeReals, initialize=data['scenario_indicator_gen'])
    m.scenario_indicator_line = pyo.Param(m.line, m.year, m.rpdn, m.scenario, within=pyo.NonNegativeReals, initialize=data['scenario_indicator_line'])
    m.scenario_rate = pyo.Param(m.scenario, within=pyo.NonNegativeReals, initialize=data['scenario_rate'])

    m.cap_sv = pyo.Var(m.node, m.gen_pn, m.year, m.rpdn, m.scenario, within=pyo.NonNegativeReals, doc='Generation capacity survived in scenario')
    m.cap_sv_line = pyo.Var(m.line, m.year, m.rpdn, m.scenario, within=pyo.NonNegativeReals, doc='Line capacity survived in scenario')
    m.cap_sv_avg = pyo.Var(m.node, m.generator, m.year, m.scenario, within=pyo.NonNegativeReals, doc='Average generation capacity survived in scenario')
    m.cap_sv_line_avg = pyo.Var(m.line, m.year, m.scenario, within=pyo.NonNegativeReals, doc='Average line capacity survived in scenario')
    
    m.ppd = pyo.Var(m.node, m.generator, m.year, m.rpdn, m.sub, m.scenario, within=pyo.NonNegativeReals, doc='Power produced in scenario')
    m.flow = pyo.Var(m.line, m.year, m.rpdn, m.sub, m.scenario, within=pyo.Reals, doc='Power flow in scenario')
    m.flow_pos = pyo.Var(m.line, m.year, m.rpdn, m.sub, m.scenario, within=pyo.NonNegativeReals, doc='Positive power flow in scenario')
    m.flow_neg = pyo.Var(m.line, m.year, m.rpdn, m.sub, m.scenario, within=pyo.NonPositiveReals, doc='Negative power flow in scenario')  
    m.over_gen = pyo.Var(m.node, m.year, m.rpdn, m.sub, m.scenario, within=pyo.NonNegativeReals, doc='Over-generation')       
    
    # Potential generators
    @m.Constraint(m.node, m.dis_pn, m.year, m.rpdn, m.scenario)
    def dis_survived_capacity_pn(m, i, k, t, n, sc):
        return m.cap_sv[i,k,t,n,sc] == m.scenario_indicator_gen[i,k,t,n,sc] * m.cap_ava[i,k,t]


    @m.Constraint(m.node, m.dis_pn, m.year, m.rpdn, m.sub, m.scenario)
    def power_generation_lb_pn(m, i, k, t, n, b, sc):
        return m.min_opt_dpt[k] * m.cap_sv[i,k,t,n,sc] <= m.ppd[i,k,t,n,b,sc]
    
    @m.Constraint(m.node, m.dis_pn, m.year, m.rpdn, m.sub, m.scenario)
    def power_generation_ub_pn(m, i, k, t, n, b, sc):
        return m.ppd[i,k,t,n,b,sc] <= m.max_opt_dpt[k] * m.cap_sv[i,k,t,n,sc]  

    @m.Constraint(m.node, m.dis_pn, m.year, m.rpdn, m.sub, m.scenario)
    def ramp_up_constraint_pn(m, i, k, t, n, b, sc):
        if b == 1:
            return m.ppd[i,k,t,n,b,sc] <= m.ramp_up[k] * m.cap_sv[i,k,t,n,sc]  
        else:
            return m.ppd[i,k,t,n,b,sc] - m.ppd[i,k,t,n,b-1,sc] <= m.ramp_up[k] * m.cap_sv[i,k,t,n,sc]    

    @m.Constraint(m.node, m.dis_pn, m.year, m.rpdn, m.sub, m.scenario)
    def ramp_down_constraint_pn(m, i, k, t, n, b, sc):
        if b == 1:
            return -m.ppd[i,k,t,n,b,sc] <= m.ramp_down[k] * m.cap_sv[i,k,t,n,sc] 
        else:
            return m.ppd[i,k,t,n,b-1,sc] - m.ppd[i,k,t,n,b,sc] <= m.ramp_down[k] * m.cap_sv[i,k,t,n,sc]   
    
    @m.Constraint(m.node, m.dis_pn, m.year, m.scenario)
    def aggregated_cap_gen_pn(m, i, k, t, sc):
        return m.cap_sv_avg[i,k,t,sc] == sum(m.cap_sv[i,k,t,n,sc] for n in m.rpdn) / len(m.rpdn)        
    
    
    
    # Existing generators
    @m.Constraint(m.node, m.gen_ex, m.year, m.scenario)
    def aggregated_cap_gen_ex(m, i, k, t, sc):
        return m.cap_sv_avg[i,k,t,sc] == m.cap_ava[i,k,t]        
    
    @m.Constraint(m.node, m.gen_ex, m.year, m.rpdn, m.sub, m.scenario)
    def power_generation_lb_ex(m, i, k, t, n, b, sc):
        return m.min_opt_dpt[k] * m.cap_sv_avg[i,k,t,sc] <= m.ppd[i,k,t,n,b,sc]
    
    @m.Constraint(m.node, m.gen_ex, m.year, m.rpdn, m.sub, m.scenario)
    def power_generation_ub_ex(m, i, k, t, n, b, sc):
        return m.ppd[i,k,t,n,b,sc] <= m.max_opt_dpt[k] * m.cap_sv_avg[i,k,t,sc]  

    @m.Constraint(m.node, m.gen_ex, m.year, m.rpdn, m.sub, m.scenario)
    def ramp_up_constraint_ex(m, i, k, t, n, b, sc):
        if b == 1:
            return m.ppd[i,k,t,n,b,sc] <= m.ramp_up[k] * m.cap_sv_avg[i,k,t,sc]  
        else:
            return m.ppd[i,k,t,n,b,sc] - m.ppd[i,k,t,n,b-1,sc] <= m.ramp_up[k] * m.cap_sv_avg[i,k,t,sc]   

    @m.Constraint(m.node, m.gen_ex, m.year, m.rpdn, m.sub, m.scenario)
    def ramp_down_constraint_ex(m, i, k, t, n, b, sc):
        if b == 1:
            return -m.ppd[i,k,t,n,b,sc] <= m.ramp_down[k] * m.cap_sv_avg[i,k,t,sc] 
        else:
            return m.ppd[i,k,t,n,b-1,sc] - m.ppd[i,k,t,n,b,sc] <= m.ramp_down[k] * m.cap_sv_avg[i,k,t,sc]          


    @m.Constraint(m.node, m.res_pn, m.year, m.scenario)
    def res_survived_capacity_pn(m, i, k, t, sc):
        return m.cap_sv_avg[i,k,t,sc] == m.cap_ava[i,k,t]  

    @m.Constraint(m.node, m.res_pn, m.year, m.rpdn, m.sub, m.scenario)
    def res_power_generation_pn(m, i, k, t, n, b, sc):
        return m.ppd[i,k,t,n,b,sc] == m.capacity_factor[i,t,n,b] * m.cap_sv_avg[i,k,t,sc]      
    

    # Transmission lines        
    @m.Constraint(m.line, m.year, m.rpdn, m.scenario)
    def survived_capacity_line(m, l, t, n, sc):
        return m.cap_sv_line[l,t,n,sc] == m.scenario_indicator_line[l,t,n,sc] * m.cap_ava_line[l,t]
        
    @m.Constraint(m.line, m.year, m.rpdn, m.sub, m.scenario)
    def flows_lb_n1(m, l, t, n, b, sc):
        return -m.cap_sv_line[l,t,n,sc] <= m.flow[l,t,n,b,sc]
    
    @m.Constraint(m.line, m.year, m.rpdn, m.sub, m.scenario)
    def flows_ub_n1(m, l, t, n, b, sc):
        return m.flow[l,t,n,b,sc] <= m.cap_sv_line[l,t,n,sc]   
    
    @m.Constraint(m.line, m.year, m.scenario)
    def aggregated_cap_line(m, l, t, sc):
        return m.cap_sv_line_avg[l,t,sc] == sum(m.cap_sv_line[l,t,n,sc] for n in m.rpdn) / len(m.rpdn)            
                
    
            
    
    # Power flows
    @m.Constraint(m.line_pn, m.year, m.rpdn, m.sub, m.scenario)
    def flows_lb_pn(m, l, t, n, b, sc):
        return -m.cap_sv_line_avg[l,t,sc] <= m.flow[l,t,n,b,sc]
    
    @m.Constraint(m.line_pn, m.year, m.rpdn, m.sub, m.scenario)
    def flows_ub_pn(m, l, t, n, b, sc):
        return m.flow[l,t,n,b,sc] <= m.cap_sv_line_avg[l,t,sc]         
    
    @m.Constraint(m.line, m.year, m.rpdn, m.sub, m.scenario)
    def flows_pos_neg(m, l, t, n, b, sc):
        return m.flow[l,t,n,b,sc] == m.flow_pos[l,t,n,b,sc] + m.flow_neg[l,t,n,b,sc]
    
    
    # Demand satisfaction
    @m.Constraint(m.node, m.year, m.rpdn, m.sub, m.scenario)
    def nodal_power_balance(m, i, t, n, b, sc):
        return sum(m.ppd[i,k,t,n,b,sc] for k in m.generator) + sum(m.flow[l,t,n,b,sc] for l in m.line_to_node[i]) == \
                m.load_demand[i,t,n,b] + sum(m.flow[l,t,n,b,sc] for l in m.line_fr_node[i]) + m.over_gen[i,t,n,b,sc]        

    if renewable == True:
        @m.Constraint(m.year)
        def renewable_gen_power(m, t):
            return (
                sum(m.ppd[i,k,t,n,b,1]
                for i in m.node for k in m.renewable_gen for n in m.rpdn for b in m.sub)
                - sum(m.over_gen[i,t,n,b,1] for i in m.node for n in m.rpdn for b in m.sub)
                >= m.res_target[t] 
                * sum(m.load_demand[i,t,n,b] 
                        for i in m.node for n in m.rpdn for b in m.sub)
            )                           
    # In N-k reliability, this constraint is only applied to the normal scenario
    
    @m.Expression()  # unit: M$
    def capital_expenditure(m):
        return sum(m.IC[i,k,t] for i in m.node for k in m.gen_pn for t in m.year) + sum(m.ICL[l,t] for l in m.line_pn for t in m.year) 

    @m.Expression()
    def IC_generator(m):
        return sum(m.IC[i,k,t] for i in m.node for k in m.gen_pn for t in m.year)
    
    @m.Expression()
    def IC_line(m):
        return sum(m.ICL[l,t] for l in m.line_pn for t in m.year)
    
    @m.Expression() 
    def operating_expenses(m):
        return sum(m.scenario_rate[sc] * m.unit_FC[k,t] * m.cap_sv_avg[i,k,t,sc] for i in m.node for k in m.generator for t in m.year for sc in m.scenario) + \
            sum(m.scenario_rate[sc] * m.unit_FC_line[l,t] * m.cap_sv_line_avg[l,t,sc] for l in m.line for t in m.year for sc in m.scenario) +\
                sum(m.scenario_rate[sc] * m.weight_time[n] * m.operation_time[b] * m.unit_VC[k,t] * m.ppd[i,k,t,n,b,sc] 
                    for i in m.node for k in m.generator for t in m.year for n in m.rpdn for b in m.sub for sc in m.scenario)/1000000  +\
                        sum(m.scenario_rate[sc] * m.weight_time[n] * m.operation_time[b] * m.unit_VC_line[l,t] * (m.flow_pos[l,t,n,b,sc] - m.flow_neg[l,t,n,b,sc]) 
                            for l in m.line for t in m.year for n in m.rpdn for b in m.sub for sc in m.scenario)/1000000 

    @m.Expression()
    def FOC_generator(m):
        return sum(m.scenario_rate[sc] * m.unit_FC[k,t] * m.cap_sv_avg[i,k,t,sc] for i in m.node for k in m.generator for t in m.year for sc in m.scenario)

    @m.Expression()
    def FOC_line(m):
        return sum(m.scenario_rate[sc] * m.unit_FC_line[l,t] * m.cap_sv_line_avg[l,t,sc] for l in m.line for t in m.year for sc in m.scenario)
    
    @m.Expression()
    def VOC_generator(m):
        return sum(m.scenario_rate[sc] * m.weight_time[n] * m.operation_time[b] * m.unit_VC[k,t] * m.ppd[i,k,t,n,b,sc] 
                    for i in m.node for k in m.generator for t in m.year for n in m.rpdn for b in m.sub for sc in m.scenario)/1000000 
    
    @m.Expression()
    def VOC_line(m):
        return sum(m.scenario_rate[sc] * m.weight_time[n] * m.operation_time[b] * m.unit_VC_line[l,t] * (m.flow_pos[l,t,n,b,sc] - m.flow_neg[l,t,n,b,sc])  
                    for l in m.line for t in m.year for n in m.rpdn for b in m.sub for sc in m.scenario)/1000000    

            
    @m.Objective(sense=pyo.minimize)   # unit: M$
    def obj(m):
        return sum(m.IC[i,k,t] for i in m.node for k in m.gen_pn for t in m.year) + sum(m.ICL[l,t] for l in m.line_pn for t in m.year) +\
            sum(m.scenario_rate[sc] * m.unit_FC[k,t] * m.cap_sv_avg[i,k,t,sc] for i in m.node for k in m.generator for t in m.year for sc in m.scenario) + \
                sum(m.scenario_rate[sc] * m.unit_FC_line[l,t] * m.cap_sv_line_avg[l,t,sc] for l in m.line for t in m.year for sc in m.scenario) +\
                    sum(m.scenario_rate[sc] * m.weight_time[n] * m.operation_time[b] * m.unit_VC[k,t] * m.ppd[i,k,t,n,b,sc] 
                        for i in m.node for k in m.generator for t in m.year for n in m.rpdn for b in m.sub for sc in m.scenario)/1000000 +\
                            sum(m.scenario_rate[sc] * m.weight_time[n] * m.operation_time[b] * m.unit_VC_line[l,t] * (m.flow_pos[l,t,n,b,sc] - m.flow_neg[l,t,n,b,sc]) 
                                for l in m.line for t in m.year for n in m.rpdn for b in m.sub for sc in m.scenario)/1000000     
    

    transformation_string = 'gdp.bigm'
    pyo.TransformationFactory(transformation_string).apply_to(m)

       
    return m

if __name__ == "__main__":
    formulation = 'n-2'    # None (--> None includes no and reserve), n-1, n-2, dual-no, dual-yes
    renewable_status = False
    data = read_data(datafolder="San Diego", advanced=formulation)
    m = n_k_reliability_model(data, renewable=renewable_status)

    m = solve_model(m, advanced=formulation, renewable=renewable_status, time_limit=1000, abs_gap=0.01, threads=8)

