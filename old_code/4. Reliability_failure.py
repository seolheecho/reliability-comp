__author__ = "Seolhee Cho"

import pyomo.environ as pyo
from pyomo.gdp import Disjunction, Disjunct
import pandas as pd

def RGTEP_CEC_model(transformation):
    
    m = pyo.ConcreteModel()
    
    # Sets   
    m.node = pyo.RangeSet(1,3)  # 1,2,3
    m.generator = pyo.Set(initialize=['ng'])  
    m.line = pyo.RangeSet(1,3)  # 1,2,3
    m.year = pyo.RangeSet(1,3)  # 1,2,3
    m.rpdn = pyo.RangeSet(1,2)  # 1,2
    m.sub = pyo.RangeSet(1,2)   # 1,2
    m.state = pyo.RangeSet(1,8)  # 1-8
    
    # Indexed Set
    line_to_node = {1: [3], 2: [1,2], 3: []}
    line_fr_node = {1: [1], 2: [], 3: [2,3]}
    
    m.line_to_node = pyo.Set(m.node, within=m.line, initialize=line_to_node)
    m.line_fr_node = pyo.Set(m.node, within=m.line, initialize=line_fr_node)
    
    # Parameters
    m.UD_penalty = pyo.Param(within=pyo.NonNegativeReals, initialize=500)
    m.DT_penalty = pyo.Param(within=pyo.NonNegativeReals, initialize=500)
    
    prob_state = {}
    prob_state[1] = 0.8044
    prob_state[2] = 0.0605
    prob_state[3] = 0.0605
    prob_state[4] = 0.0605
    prob_state[5] = 0.0046
    prob_state[6] = 0.0046
    prob_state[7] = 0.0046
    prob_state[8] = 0.0003
    m.prob_state = pyo.Param(m.state, within=pyo.NonNegativeReals, initialize=prob_state)
    
    state_indicator = {}
    state_indicator[1,'ng',1] = 1
    state_indicator[2,'ng',1] = 1
    state_indicator[3,'ng',1] = 1
    state_indicator[1,'ng',2] = 0
    state_indicator[2,'ng',2] = 1
    state_indicator[3,'ng',2] = 1
    state_indicator[1,'ng',3] = 1
    state_indicator[2,'ng',3] = 0
    state_indicator[3,'ng',3] = 1
    state_indicator[1,'ng',4] = 1
    state_indicator[2,'ng',4] = 1
    state_indicator[3,'ng',4] = 0
    state_indicator[1,'ng',5] = 0
    state_indicator[2,'ng',5] = 0
    state_indicator[3,'ng',5] = 1
    state_indicator[1,'ng',6] = 0
    state_indicator[2,'ng',6] = 1
    state_indicator[3,'ng',6] = 0
    state_indicator[1,'ng',7] = 1
    state_indicator[2,'ng',7] = 0
    state_indicator[3,'ng',7] = 0
    state_indicator[1,'ng',8] = 0
    state_indicator[2,'ng',8] = 0
    state_indicator[3,'ng',8] = 0
    m.state_indicator = pyo.Param(m.node, m.generator, m.state, within=pyo.NonNegativeReals, initialize=state_indicator)    
    
    weight_time = {n: 1 for n in m.rpdn}
    m.weight_time = pyo.Param(m.rpdn, within=pyo.NonNegativeReals, initialize=weight_time)
    
    operation_time = {b: 1 for b in m.sub}
    m.operation_time = pyo.Param(m.sub, within=pyo.NonNegativeReals, initialize=operation_time)
    
    loss_line = {l: 0.05 for l in m.line}
    m.loss_line = pyo.Param(m.line, within=pyo.NonNegativeReals, initialize=loss_line)
    
    min_ins_cap = {k: 10 for k in m.generator} 
    m.min_ins_cap = pyo.Param(m.generator, within=pyo.NonNegativeReals, initialize=min_ins_cap)
    
    max_ins_cap = {k: 500 for k in m.generator} 
    m.max_ins_cap = pyo.Param(m.generator, within=pyo.NonNegativeReals, initialize=max_ins_cap)
    
    min_line = {l: 10 for l in m.line}
    m.min_line = pyo.Param(m.line, within=pyo.NonNegativeReals, initialize=min_line)
    
    max_line = {l: 500 for l in m.line}
    m.max_line = pyo.Param(m.line, within=pyo.NonNegativeReals, initialize=max_line)
    
    load_demand = {}
    load_demand[1,1,1,1] = 50
    load_demand[1,1,1,2] = 70
    load_demand[1,1,2,1] = 50
    load_demand[1,1,2,2] = 80
    load_demand[1,2,1,1] = 90
    load_demand[1,2,1,2] = 110
    load_demand[1,2,2,1] = 130
    load_demand[1,2,2,2] = 110
    load_demand[1,3,1,1] = 140
    load_demand[1,3,1,2] = 160
    load_demand[1,3,2,1] = 120
    load_demand[1,3,2,2] = 130
    load_demand[2,1,1,1] = 100
    load_demand[2,1,1,2] = 150
    load_demand[2,1,2,1] = 100
    load_demand[2,1,2,2] = 200
    load_demand[2,2,1,1] = 230
    load_demand[2,2,1,2] = 300
    load_demand[2,2,2,1] = 250
    load_demand[2,2,2,2] = 300
    load_demand[2,3,1,1] = 350
    load_demand[2,3,1,2] = 300
    load_demand[2,3,2,1] = 350
    load_demand[2,3,2,2] = 400
    load_demand[3,1,1,1] = 0
    load_demand[3,1,1,2] = 0
    load_demand[3,1,2,1] = 0
    load_demand[3,1,2,2] = 0
    load_demand[3,2,1,1] = 0
    load_demand[3,2,1,2] = 0
    load_demand[3,2,2,1] = 0
    load_demand[3,2,2,2] = 0
    load_demand[3,3,1,1] = 0
    load_demand[3,3,1,2] = 0
    load_demand[3,3,2,1] = 0
    load_demand[3,3,2,2] = 0          
    m.load_demand = pyo.Param(m.node, m.year, m.rpdn, m.sub, within=pyo.NonNegativeReals, initialize=load_demand)

    min_opt_dpt = {k: 0.2 for k in m.generator} 
    m.min_opt_dpt = pyo.Param(m.generator, within=pyo.NonNegativeReals, initialize=min_opt_dpt)
    
    max_opt_dpt = {k: 0.8 for k in m.generator} 
    m.max_opt_dpt = pyo.Param(m.generator, within=pyo.NonNegativeReals, initialize=max_opt_dpt)

    unit_IC = {}
    for t in m.year:
        unit_IC['ng',t] = 130 
    m.unit_IC = pyo.Param(m.generator, m.year, within=pyo.NonNegativeReals, initialize=unit_IC) # unit: M$
    
    unit_IC_line = {(l,t): 30 for l in m.line for t in m.year}
    m.unit_IC_line = pyo.Param(m.line, m.year, within=pyo.NonNegativeReals, initialize=unit_IC_line)
    
    unit_FC = {}
    for t in m.year:
        unit_FC['ng',t] = 5     
    m.unit_FC = pyo.Param(m.generator, m.year, within=pyo.NonNegativeReals, initialize=unit_FC)
    
    unit_FC_line = {(l,t): 1 for l in m.line for t in m.year}    
    m.unit_FC_line = pyo.Param(m.line, m.year, within=pyo.NonNegativeReals, initialize=unit_FC_line)
    
    unit_VC = {}
    for t in m.year:
        unit_VC['ng',t] = 0.005       
    m.unit_VC = pyo.Param(m.generator, m.year, within=pyo.NonNegativeReals, initialize=unit_VC)
    
    unit_VC_line = {(l,t): 0.001 for l in m.line for t in m.year}    
    m.unit_VC_line = pyo.Param(m.line, m.year, within=pyo.NonNegativeReals, initialize=unit_VC_line)
    
   
    # Bounds
    m.ub_cap_ins = pyo.Param(m.generator, within=pyo.NonNegativeReals, initialize=max_ins_cap) 
    def _bounds_cap_ins_rule(m, i, k, t):
        return (0, m.ub_cap_ins[k])     

    m.ub_cap_ins_line = pyo.Param(m.line, within=pyo.NonNegativeReals, initialize=max_line) 
    def _bounds_cap_ins_line_rule(m, l, t):
        return (0, m.ub_cap_ins_line[l]) 
    
    ub_IC = {}
    for k in m.generator:
        ub_IC[k] = m.max_ins_cap[k] * m.unit_IC[k,3]
    m.ub_IC = pyo.Param(m.generator, within=pyo.NonNegativeReals, initialize=ub_IC) 
    def _bounds_IC_rule(m, i, k, t):
        return (0, m.ub_IC[k]) 
    
    ub_ICL = {}
    for l in m.line:
        ub_ICL[l] = m.max_line[l] * m.unit_IC_line[l,3]
    m.ub_ICL = pyo.Param(m.line, within=pyo.NonNegativeReals, initialize=ub_ICL) 
    def _bounds_ICL_rule(m, l, t):
        return (0, m.ub_ICL[l])         

    m.ub_UD = pyo.Param(m.node, m.year, m.rpdn, m.sub, within=pyo.Reals, initialize=load_demand)
    def _bounds_UD_rule(m, i, t, n, b, st):
        return (0, m.load_demand[i,t,n,b])
    
    ub_UDP = {}
    for i in m.node:
        for t in m.year:
            for n in m.rpdn:
                for b in m.sub:
                    ub_UDP[i,t,n,b] = m.load_demand[i,t,n,b] * m.UD_penalty
    m.ub_UDP = pyo.Param(m.node, m.year, m.rpdn, m.sub, within=pyo.Reals, initialize=ub_UDP)
    def _bounds_UDP_rule(m, i, t, n, b, st):
        return (0, m.ub_UDP[i,t,n,b])    
    
    ub_DTP = {}
    for i in m.node:
        for t in m.year:
            for n in m.rpdn:
                for b in m.sub:
                    ub_DTP[i,t,n,b] = len(m.rpdn) * len(m.sub) * m.DT_penalty
    m.ub_DTP = pyo.Param(m.node, m.year, m.rpdn, m.sub, within=pyo.Reals, initialize=ub_DTP)
    def _bounds_DTP_rule(m, i, t, n, b, st):
        return (0, m.ub_DTP[i,t,n,b])         


    # Non-negative variables  
    m.cap_ins = pyo.Var(m.node, m.generator, m.year, bounds=_bounds_cap_ins_rule, within=pyo.NonNegativeReals, doc='Installed capacity of generators')
    m.cap_ins_line = pyo.Var(m.line, m.year, bounds=_bounds_cap_ins_line_rule, within=pyo.NonNegativeReals, doc='Installed capacity of lines')
    m.cap_ava = pyo.Var(m.node, m.generator, m.year, within=pyo.NonNegativeReals, doc='Available capacity of generators')
    m.cap_ava_st = pyo.Var(m.node, m.generator, m.year, m.state, within=pyo.NonNegativeReals, doc='Available capacity of generators at state')
    m.cap_ava_line = pyo.Var(m.line, m.year, within=pyo.NonNegativeReals, doc='Available capacity of lines')
    m.pnd= pyo.Var(m.node, m.generator, m.year, m.rpdn, m.sub, m.state, within=pyo.NonNegativeReals, doc='Power produced and used')
    
    m.ppd = pyo.Var(m.node, m.generator, m.year, m.rpdn, m.sub, m.state, within=pyo.NonNegativeReals, doc='Power produced')
    m.pexp = pyo.Var(m.node, m.generator, m.year, m.rpdn, m.sub, m.state, within=pyo.NonNegativeReals, doc='Power exported')
    m.flow = pyo.Var(m.line, m.year, m.rpdn, m.sub, m.state, within=pyo.NonNegativeReals, doc='Power flow')
    m.UD = pyo.Var(m.node, m.year, m.rpdn, m.sub, m.state, within=pyo.NonNegativeReals, bounds=_bounds_UD_rule, doc='Unmet demand')

    m.IC = pyo.Var(m.node, m.generator, m.year, bounds=_bounds_IC_rule, within=pyo.NonNegativeReals)
    m.ICL = pyo.Var(m.line, m.year, bounds=_bounds_ICL_rule, within=pyo.NonNegativeReals)
    m.FC = pyo.Var(m.node, m.generator, m.year, m.state, within=pyo.NonNegativeReals)
    m.FCL = pyo.Var(m.line, m.year, within=pyo.NonNegativeReals)
    m.VC = pyo.Var(m.node, m.generator, m.year, m.rpdn, m.sub, m.state, within=pyo.NonNegativeReals)
    m.VCL = pyo.Var(m.line, m.year, m.rpdn, m.sub, m.state, within=pyo.NonNegativeReals)
    m.UDP = pyo.Var(m.node, m.year, m.rpdn, m.sub, m.state, within=pyo.NonNegativeReals, bounds=_bounds_UDP_rule, doc='Unmet demand penalty')
    m.DTP = pyo.Var(m.node, m.year, m.rpdn, m.sub, m.state, within=pyo.NonNegativeReals, bounds=_bounds_DTP_rule, doc='Downtime penalty')

    m.CAPEX = pyo.Var(within=pyo.NonNegativeReals)
    m.OPEX = pyo.Var(within=pyo.NonNegativeReals)    
    m.PEN = pyo.Var(within=pyo.NonNegativeReals)
    
    
    
    # CONSTRAINTS
    ############################################################################################ 
    ##                Investment of generators, batteries, and transmission lines             ##
    ############################################################################################      
 
    ## Installation of generators
    @m.Disjunct(m.node, m.generator, m.year)
    def gen_install(disj, i, k, t):
       disj.install_cap_res1 = pyo.Constraint(expr= m.min_ins_cap[k] <= m.cap_ins[i,k,t])
       disj.install_cap_res2 = pyo.Constraint(expr= m.cap_ins[i,k,t] <= m.max_ins_cap[k])
       disj.invest_cost_res =  pyo.Constraint(expr= m.IC[i,k,t] == m.unit_IC[k,t] * m.cap_ins[i,k,t])
    
    @m.Disjunct(m.node, m.generator, m.year)
    def gen_install_no(disj, i, k, t):
        disj.invest_cost_res_no = pyo.Constraint(expr= m.cap_ins[i,k,t] == 0)
        disj.install_cap_res_no = pyo.Constraint(expr= m.IC[i,k,t] == 0)
        
    @m.Disjunction(m.node, m.generator, m.year)
    def Ornot_gen_install(m, i, k, t):
        return [m.gen_install[i,k,t], m.gen_install_no[i,k,t]]
    
    @m.LogicalConstraint(m.node, m.generator)
    def atmost_gens1(m, i, k):
        return pyo.atmost(1, [m.gen_install[i,k,t].indicator_var for t in m.year])         
    
    
    
    ## Installation of transmission lines
    @m.Disjunct(m.line, m.year)
    def line_install(disj, l, t):
        disj.ins_cap_lb = pyo.Constraint(expr= m.min_line[l] <= m.cap_ins_line[l,t])
        disj.ins_cap_ub = pyo.Constraint(expr= m.cap_ins_line[l,t] <= m.max_line[l])
        disj.invest_cost = pyo.Constraint(expr= m.ICL[l,t] == m.unit_IC_line[l,t] * m.cap_ins_line[l,t])
    # m.line_install.pprint()

    @m.Disjunct(m.line, m.year)
    def line_install_no(disj, l, t):
        disj.ins_cap_no = pyo.Constraint(expr= m.cap_ins_line[l,t] == 0)
        disj.invest_cost_no = pyo.Constraint(expr= m.ICL[l,t] == 0)
        
    @m.Disjunction(m.line, m.year)
    def Ornot_line_install(m, l, t):
        return [m.line_install[l,t], m.line_install_no[l,t]]    
    
    @m.LogicalConstraint(m.line)
    def atmost_line_install(m, l):
        return pyo.atmost(1, [m.line_install[l,t].indicator_var for t in m.year])   



    ## Available capacity of generators         
    @m.Constraint(m.node, m.generator, m.year)
    def availability_capacity_gen(m, i, k, t):
        return m.cap_ava[i,k,t] == sum(m.cap_ins[i,k,tq] for tq in range(1,t+1))
    # m.availability_capacity_gen.pprint()
    
    ## Available capacity of generators at state        
    @m.Constraint(m.node, m.generator, m.year, m.state)
    def availability_capacity_gen_st(m, i, k, t, st):
        return m.cap_ava_st[i,k,t,st] == m.state_indicator[i,k,st] * m.cap_ava[i,k,t]
    # m.availability_capacity_gen_st.pprint()
    
    @m.Constraint(m.node, m.generator, m.year, m.state) 
    def fixed_operating_cost(m, i, k, t, st):
        return m.FC[i,k,t,st] ==  m.unit_FC[k,t] * m.cap_ava_st[i,k,t,st]   
    
    ## Available capacity of transmission lines    
    @m.Constraint(m.line, m.year)
    def available_capacity_line_pn(m, l, t):
        return m.cap_ava_line[l,t] == sum(m.cap_ins_line[l,tp] for tp in range(1, t+1))
                    

    ############################################################################################ 
    ##                                    Generator operation                                 ##
    ############################################################################################  

    @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub, m.state)
    def power_generation_lb(m, i, k, t, n, b, st):
        return m.min_opt_dpt[k] *  m.cap_ava_st[i,k,t,st] <= m.ppd[i,k,t,n,b,st]
    
    @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub, m.state)
    def power_generation_ub(m, i, k, t, n, b, st):
        return m.ppd[i,k,t,n,b,st] <= m.max_opt_dpt[k] *  m.cap_ava_st[i,k,t,st]
    



    ############################################################################################ 
    ##                                      Power balances                                    ##
    ############################################################################################  
    
    @m.Constraint(m.node, m.year, m.rpdn, m.sub, m.state)
    def nodal_power_balance(m, i, t, n, b, st):
        return sum(m.pnd[i,k,t,n,b,st] for k in m.generator) + sum((1 - m.loss_line[l]) * m.flow[l,t,n,b,st] for l in m.line_to_node[i]) + m.UD[i,t,n,b,st] == m.load_demand[i,t,n,b]
    # m.nodel_power_balance.pprint()            
    
    @m.Constraint(m.node, m.year, m.rpdn, m.sub, m.state)
    def power_balance_dpt(m, i, t, n, b, st):
        return sum(m.ppd[i,k,t,n,b,st] for k in m.generator) == sum(m.pnd[i,k,t,n,b,st] for k in m.generator) + sum(m.pexp[i,k,t,n,b,st] for k in m.generator)
    # m.power_balance_dpt.pprint()     
  
 
    @m.Constraint(m.node, m.year, m.rpdn, m.sub, m.state)
    def power_flow_export(m, i, t, n, b, st):
        return sum(m.pexp[i,k,t,n,b,st] for k in m.generator) == sum(m.flow[l,t,n,b,st] for l in m.line_fr_node[i])
    # m.power_flow_export.pprint()  
    
    
    @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub, m.state)
    def variable_operating_cost(m, i, k, t, n, b, st):
        return m.VC[i,k,t,n,b,st] == m.unit_VC[k,t] * m.ppd[i,k,t,n,b,st]
    
    

    ## Reliability penalty estimation
    @m.Disjunct(m.node, m.year, m.rpdn, m.sub, m.state)
    def high_reliability(disj, i, t, n, b, st):
        disj.unmet_demand_est = pyo.Constraint(expr= m.UD[i,t,n,b,st] == 0)
        disj.ud_penalty_est = pyo.Constraint(expr= m.UDP[i,t,n,b,st] == 0)
        disj.dt_penalty_est =  pyo.Constraint(expr= m.DTP[i,t,n,b,st] == 0)
    
    @m.Disjunct(m.node, m.year, m.rpdn, m.sub, m.state)
    def low_reliability(disj, i, t, n, b, st):
        disj.unmet_demand_est = pyo.Constraint(expr= m.UD[i,t,n,b,st] >= 0)
        disj.ud_penalty_est = pyo.Constraint(expr= m.UDP[i,t,n,b,st] == m.UD[i,t,n,b,st] * m.UD_penalty)
        disj.dt_penalty_est =  pyo.Constraint(expr= m.DTP[i,t,n,b,st] == m.weight_time[n] * m.operation_time[b] * m.DT_penalty)
        
    @m.Disjunction(m.node, m.year, m.rpdn, m.sub, m.state)
    def Ornot_reliability(m, i, t, n, b, st):
        return [m.high_reliability[i,t,n,b,st], m.low_reliability[i,t,n,b,st]]

        
    
    ############################################################################################ 
    ##                              Operation of transmission line                            ##
    ############################################################################################ 
    
    @m.Constraint(m.line, m.year, m.rpdn, m.sub, m.state)
    def flows_lb(m, l, t, n, b, st):
        return -m.cap_ava_line[l,t] <= m.flow[l,t,n,b,st]
    # m.flows_under_disruption1.pprint()
    
    @m.Constraint(m.line, m.year, m.rpdn, m.sub, m.state)
    def flows_ub(m, l, t, n, b, st):
        return m.flow[l,t,n,b,st] <= m.cap_ava_line[l,t] 
    # m.flows_under_disruption2.pprint()    
    
    @m.Constraint(m.line, m.year, m.rpdn, m.sub, m.state)
    def variable_cost_line(m, l, t, n, b, st):
        return m.VCL[l,t,n,b,st] == m.unit_VC_line[l,t] * m.flow[l,t,n,b,st]




    ############################################################################################ 
    ##                                    Objective function                                  ##
    ############################################################################################ 

    @m.Constraint()  # unit: M$
    def capital_expenditure(m):
        return m.CAPEX == sum(m.IC[i,k,t] for i in m.node for k in m.generator for t in m.year) + sum(m.ICL[l,t] for l in m.line for t in m.year) 
    
    
    @m.Constraint() # unit: FC & FCL -- M$, UC & DC -- $, Fuel price, VC -- $
    def operating_expenses(m):
        return m.OPEX == sum(m.prob_state[st] * m.FC[i,k,t,st] for i in m.node for k in m.generator for t in m.year for st in m.state) + sum(m.FCL[l,t] for l in m.line for t in m.year) +\
            sum(m.prob_state[st] * m.weight_time[n] * m.operation_time[b] * m.VC[i,k,t,n,b,st] for i in m.node for k in m.generator for t in m.year for n in m.rpdn for b in m.sub for st in m.state)  +\
                sum(m.prob_state[st] * m.weight_time[n] * m.operation_time[b] * m.VCL[l,t,n,b,st] for l in m.line for t in m.year for n in m.rpdn for b in m.sub for st in m.state) 
        
    @m.Constraint()
    def penalties(m):
        return m.PEN == sum(m.prob_state[st] * m.UDP[i,t,n,b,st] for i in m.node for t in m.year for n in m.rpdn for b in m.sub for st in m.state)  + \
            sum(m.prob_state[st] * m.DTP[i,t,n,b,st] for i in m.node for t in m.year for n in m.rpdn for b in m.sub for st in m.state) 
        
    @m.Objective(sense=pyo.minimize)   # unit: M$
    def obj(m):
        return m.CAPEX + m.OPEX + m.PEN
    
    transformation_string = 'gdp.' + transformation 
    pyo.TransformationFactory(transformation_string).apply_to(m)
       
    # # N-1 reliability design results   
    # m.cap_ins[1,'ng',1].fix(363.2)
    # m.cap_ins[2,'ng',2].fix(312.5)   
    # m.cap_ins[3,'ng',1].fix(368.4) 
    # m.cap_ins_line[1,1].fix(210.5)
    # m.cap_ins_line[2,1].fix(210.5)   
    # m.cap_ins_line[3,1].fix(168.4)       
    
    # # Reserve margin design results   
    # m.cap_ins[1,'ng',1].fix(240)
    # m.cap_ins[2,'ng',1].fix(500)   
    # m.cap_ins[3,'ng',3].fix(60.3) 
    # m.cap_ins_line[1,3].fix(36.0)
    # m.cap_ins_line[2,3].fix(48.2)   
    # m.cap_ins_line[3,1].fix(0)       
    # m.cap_ins_line[3,2].fix(0)   
    # m.cap_ins_line[3,3].fix(0)           
    
    # No reliability design results   
    m.cap_ins[1,'ng',1].fix(200)
    m.cap_ins[2,'ng',1].fix(464.4)   
    m.cap_ins[3,'ng',1].fix(0) 
    m.cap_ins[3,'ng',2].fix(0) 
    m.cap_ins[3,'ng',3].fix(0) 
    m.cap_ins_line[1,3].fix(30.0)
    m.cap_ins_line[2,1].fix(0)       
    m.cap_ins_line[2,2].fix(0)   
    m.cap_ins_line[2,3].fix(0)    
    m.cap_ins_line[3,1].fix(0)       
    m.cap_ins_line[3,2].fix(0)   
    m.cap_ins_line[3,3].fix(0)          

       
    return m

if __name__ == "__main__":
    m = RGTEP_CEC_model(transformation='bigm')

    opt = pyo.SolverFactory('gurobi')
    opt.options['MIPGap'] = 0.00005
    opt.options['TimeLimit'] = 3600
    # opt.options['NonConvex'] = 2
    results = opt.solve(m, tee=True)
    # filename = os.path.join(os.path.dirname(__file__), 'model.lp')
    # RGTEP_CEC_model.write(filename, io_options={'symbolic_solver_labels':True})



    # Export results
    # Extracting variable values
    results = {}
    for var in m.component_data_objects(pyo.Var, active=True):
        var_results = {}
        index_set = var.index_set()
        for index in index_set:
            index_values = list(index)
            index_values.append(pyo.value(var[index]))
            var_results[index] = index_values
        results[var.getname()] = var_results

    # Creating DataFrame for each variable
    dfs = {}
    for var_name, var_result in results.items():
        df = pd.DataFrame.from_dict(var_result, orient='index')
        df.columns = [f'index_{i}' if i < len(index) else var_name for i in range(len(df.columns))]
        dfs[var_name] = df

    # Writing DataFrames to Excel
    with pd.ExcelWriter('results.xlsx') as writer:
        for var_name, df in dfs.items():
            df.to_excel(writer, sheet_name=var_name)


for i in m.node:
    for t in m.year:
        for k in m.generator:
            if m.gen_install[i,k,t].binary_indicator_var.value > 0.9:
                print("Dispatchable", k, "in", i, "is installed in year", t, "| IC: ", round(m.IC[i,k,t].value, 1), "| Installed Cap: ", round(m.cap_ins[i,k,t].value,1))
            else:
                print("Dispatchable", k, "in", i, "is not installed in year", t)


for l in m.line:
    for t in m.year:                
        if m.line_install[l,t].binary_indicator_var.value > 0.9:
            print("line", l, "is installed in year", t, "| ICL: ", round(m.ICL[l,t].value, 1), "| Installed Cap: ", round(m.cap_ins_line[l,t].value,1))
        else:
            print("line", l, "is not installed in year", t)
                     

for i in m.node:
    for k in m.generator:
        for t in m.year:
            for n in m.rpdn:
                for b in m.sub:
                    for st in m.state:
                        print("node", i, "plant", k, "year", t, "state", st,
                            "| Available Cap", round(m.cap_ava_st[i,k,t,st].value,1), 
                            "day", n, "subperiod", b, "| E. produced", round(m.ppd[i,k,t,n,b,st].value,1), "| E. used for demand", round(m.pnd[i,k,t,n,b,st].value,1), 
                            "| E. exported", round(m.pexp[i,k,t,n,b,st].value,1))
                        
for i in m.node:
    for t in m.year:
        for n in m.rpdn:
            for b in m.sub:
                for st in m.state:
                    print("node", i, "year", t, "day", n, "subperiod", b, "state", st,
                        "| Unmet D", round(m.UD[i,t,n,b,st].value,1),
                        "| Unmet D P", round(m.UDP[i,t,n,b,st].value,1), "| Downtime P", round(m.DTP[i,t,n,b,st].value,1))
                               

print("CAPEX", round(m.CAPEX.value, 1), "OPEX", round(m.OPEX.value, 1), "PEN", round(m.PEN.value, 1))       


for i in m.node:
    print("For node", i, "EENS", round(sum(m.prob_state[st] * m.UD[i,t,n,b,st].value for t in m.year for n in m.rpdn for b in m.sub for st in m.state), 1),
          "| LOLE", round(sum(m.prob_state[st] * (m.DTP[i,t,n,b,st].value / m.DT_penalty) for t in m.year for n in m.rpdn for b in m.sub for st in m.state), 1))
    
    
print("EENS penalty", round(sum(m.prob_state[st] * m.UDP[i,t,n,b,st].value for i in m.node for t in m.year for n in m.rpdn for b in m.sub for st in m.state), 1), 
      "LOLE penalty", round(sum(m.prob_state[st] * m.DTP[i,t,n,b,st].value for i in m.node for t in m.year for n in m.rpdn for b in m.sub for st in m.state), 1))