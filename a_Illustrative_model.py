import pyomo.environ as pyo
from pyomo.environ import value
from pyomo.gdp import Disjunction, Disjunct
import pandas as pd
import os

def Reliability_model(transformation, formulation, datafolder):
    
    curPath = os.path.join(os.path.abspath(os.path.curdir), 'data', datafolder)
    
    m = pyo.ConcreteModel()
    
    # Sets   
    m.node = pyo.RangeSet(1,3)  # N1, N2, N3
    m.generator = pyo.Set(initialize=['ng'])  
    m.line = pyo.RangeSet(1,3)  # L1-L3
    m.year = pyo.RangeSet(1,3)  # Y1-Y3
    m.rpdn = pyo.RangeSet(1,4)  # D1-D4
    m.sub = pyo.RangeSet(1,24)  # S1-S24
    
    # Indexed Set
    line_to_node = {1: [3], 2: [1,2], 3: []}  
    line_fr_node = {1: [1], 2: [], 3: [2,3]}
    # Line 1: N1 -> N2, Line 2: N3 -> N2, Line 3: N3 -> N1, Line 4: N2 -> N1
    
    m.line_to_node = pyo.Set(m.node, within=m.line, initialize=line_to_node, doc='lines entering to nodes')
    m.line_fr_node = pyo.Set(m.node, within=m.line, initialize=line_fr_node, doc='lines leaving from nodes')
    
    # Parameters    
    weight_time = {n: 91.25 for n in m.rpdn}
    m.weight_time = pyo.Param(m.rpdn, within=pyo.NonNegativeReals, initialize=weight_time)
    
    operation_time = {b: 1 for b in m.sub}
    m.operation_time = pyo.Param(m.sub, within=pyo.NonNegativeReals, initialize=operation_time)
    
    min_ins_cap = {k: 10 for k in m.generator} 
    m.min_ins_cap = pyo.Param(m.generator, within=pyo.NonNegativeReals, initialize=min_ins_cap)
    
    max_ins_cap = {k: 1500 for k in m.generator} 
    m.max_ins_cap = pyo.Param(m.generator, within=pyo.NonNegativeReals, initialize=max_ins_cap)
    
    min_line = {l: 10 for l in m.line}
    m.min_line = pyo.Param(m.line, within=pyo.NonNegativeReals, initialize=min_line)
    
    max_line = {l: 1500 for l in m.line}
    m.max_line = pyo.Param(m.line, within=pyo.NonNegativeReals, initialize=max_line)
    
    # Read CSV files after defining file paths
    hourly_demand = pd.read_csv(os.path.join(curPath, 'load_demand.csv'), header=0)
    
    load_demand = {}
    for a in range(hourly_demand.shape[0]):
        i = hourly_demand['i'].loc[a]
        t = hourly_demand['t'].loc[a]
        n = hourly_demand['n'].loc[a]
        b = hourly_demand['b'].loc[a]
        demand = hourly_demand['demand'].loc[a]
        load_demand[(i,t,n,b)] = demand
    m.load_demand = pyo.Param(m.node, m.year, m.rpdn, m.sub, within=pyo.NonNegativeReals, initialize=load_demand)

    min_opt_dpt = {k: 0.15 for k in m.generator} 
    m.min_opt_dpt = pyo.Param(m.generator, within=pyo.NonNegativeReals, initialize=min_opt_dpt)
    
    max_opt_dpt = {k: 0.85 for k in m.generator} 
    m.max_opt_dpt = pyo.Param(m.generator, within=pyo.NonNegativeReals, initialize=max_opt_dpt)
    
    ramp_up = {k: 0.7 for k in m.generator}
    m.ramp_up = pyo.Param(m.generator, within=pyo.NonNegativeReals, initialize=ramp_up)

    ramp_down = {k: 0.7 for k in m.generator}
    m.ramp_down = pyo.Param(m.generator, within=pyo.NonNegativeReals, initialize=ramp_down)

    unit_IC = {}
    for k in m.generator:
        for t in m.year:
            unit_IC[k,t] = 100
    m.unit_IC = pyo.Param(m.generator, m.year, within=pyo.NonNegativeReals, initialize=unit_IC) # unit: k$
    
    unit_IC_line = {}
    for l in m.line:
        for t in m.year:
            unit_IC_line[l,t] = 25
    m.unit_IC_line = pyo.Param(m.line, m.year, within=pyo.NonNegativeReals, initialize=unit_IC_line) # unit: k$
    
    unit_FC = {}
    for k in m.generator:
        for t in m.year:
            unit_FC[k,t] = 10
    m.unit_FC = pyo.Param(m.generator, m.year, within=pyo.NonNegativeReals, initialize=unit_FC)  # unit: k$, 10% of the IC
    
    unit_FC_line = {}
    for l in m.line:
        for t in m.year:
            unit_FC_line[l,t] = 2.5
    m.unit_FC_line = pyo.Param(m.line, m.year, within=pyo.NonNegativeReals, initialize=unit_FC_line) # unit: k$, 10% of the IC
    
    unit_VC = {}
    unit_VC['ng',1] = 20.0
    unit_VC['ng',2] = 17.0
    unit_VC['ng',3] = 14.0      
    m.unit_VC = pyo.Param(m.generator, m.year, within=pyo.NonNegativeReals, initialize=unit_VC) # unit: $
    
    unit_VC_line = {}
    for l in m.line:
        unit_VC_line[l,1] = 0.5 
        unit_VC_line[l,2] = 0.45
        unit_VC_line[l,3] = 0.4          
    m.unit_VC_line = pyo.Param(m.line, m.year, within=pyo.NonNegativeReals, initialize=unit_VC_line) # unit: $
    
    m.OG_penalty = pyo.Param(within=pyo.NonNegativeReals, initialize=1)
    
    
    # Bounds
    ub_IC = {}
    for k in m.generator:
        for t in m.year:
            ub_IC[k,t] = m.max_ins_cap[k] * m.unit_IC[k,t]
    m.ub_IC = pyo.Param(m.generator, m.year, within=pyo.NonNegativeReals, initialize=ub_IC) 
    def _bounds_IC_rule(m, i, k, t):
        return (0, m.ub_IC[k,t]) 
    
    ub_ICL = {}
    for l in m.line:
        for t in m.year:
            ub_ICL[l,t] = m.max_line[l] * m.unit_IC_line[l,t]
    m.ub_ICL = pyo.Param(m.line, m.year, within=pyo.NonNegativeReals, initialize=ub_ICL) 
    def _bounds_ICL_rule(m, l, t):
        return (0, m.ub_ICL[l,t]) 
    
    def _bounds_cap_ins_rule(m, i, k, t):
        return (0, m.max_ins_cap[k])  
    
    def _bounds_cap_ins_line_rule(m, l, t):
        return (0, m.max_line[l])      

    # Non-negative variables  
    m.cap_ins = pyo.Var(m.node, m.generator, m.year, bounds=_bounds_cap_ins_rule, within=pyo.NonNegativeReals, doc='Installed capacity of generators')
    m.cap_ins_line = pyo.Var(m.line, m.year, bounds=_bounds_cap_ins_line_rule, within=pyo.NonNegativeReals, doc='Installed capacity of lines')
    m.cap_ava = pyo.Var(m.node, m.generator, m.year, within=pyo.NonNegativeReals, doc='Available capacity of generators')
    m.cap_ava_line = pyo.Var(m.line, m.year, within=pyo.NonNegativeReals, doc='Available capacity of lines')
    m.IC = pyo.Var(m.node, m.generator, m.year, bounds=_bounds_IC_rule, within=pyo.NonNegativeReals, doc='Investment cost of generator')
    m.ICL = pyo.Var(m.line, m.year, bounds=_bounds_ICL_rule, within=pyo.NonNegativeReals, doc='Investment cost of transmission lines')
    
    
    
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
    def gen_install_no(outer, i, k, t):
        outer.invest_cost_res_no = pyo.Constraint(expr= m.cap_ins[i,k,t] == 0)
        outer.install_cap_res_no = pyo.Constraint(expr= m.IC[i,k,t] == 0)
        
    @m.Disjunction(m.node, m.generator, m.year)
    def Ornot_gen_install(m, i, k, t):
        return [m.gen_install[i,k,t], m.gen_install_no[i,k,t]]       
    
    
    
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



    ## Available capacity of generators         
    @m.Constraint(m.node, m.generator, m.year)
    def availability_capacity_generator(m, i, k, t):
        return m.cap_ava[i,k,t] == sum(m.cap_ins[i,k,tq] for tq in range(1,t+1))
    # m.availability_capacity_gen.pprint()

    ## Available capacity of transmission lines    
    @m.Constraint(m.line, m.year)
    def available_capacity_line(m, l, t):
        return m.cap_ava_line[l,t] == sum(m.cap_ins_line[l,tp] for tp in range(1, t+1))

      


    ############################################################################################ 
    ##                    Operation of generators and transmission lines                      ##
    ############################################################################################  

    if formulation == 'no':
        m.ppd = pyo.Var(m.node, m.generator, m.year, m.rpdn, m.sub, within=pyo.NonNegativeReals, doc='Power produced')
        m.flow = pyo.Var(m.line, m.year, m.rpdn, m.sub, within=pyo.Reals, doc='Power flow')
        m.flow_pos = pyo.Var(m.line, m.year, m.rpdn, m.sub, within=pyo.NonNegativeReals, doc='Positive power flow')
        m.flow_neg = pyo.Var(m.line, m.year, m.rpdn, m.sub, within=pyo.NonPositiveReals, doc='Negative power flow')
        # m.over_gen = pyo.Var(m.node, m.year, m.rpdn, m.sub, within=pyo.NonNegativeReals, doc='Excess power')              
        
        @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub)
        def power_generation_lb(m, i, k, t, n, b):
            return m.min_opt_dpt[k] * m.cap_ava[i,k,t] <= m.ppd[i,k,t,n,b]
        
        @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub)
        def power_generation_ub(m, i, k, t, n, b):
            return m.ppd[i,k,t,n,b] <= m.max_opt_dpt[k] * m.cap_ava[i,k,t]   
        
        
        @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub)
        def ramp_up_constraint(m, i, k, t, n, b):
            if b == 1:
                return m.ppd[i,k,t,n,b] <= m.ramp_up[k] * m.cap_ava[i,k,t]
            else:
                return m.ppd[i,k,t,n,b] - m.ppd[i,k,t,n,b-1] <= m.ramp_up[k] * m.cap_ava[i,k,t]    

        @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub)
        def ramp_down_constraint(m, i, k, t, n, b):
            if b == 1:
                return -m.ppd[i,k,t,n,b] <= m.ramp_down[k] * m.cap_ava[i,k,t]
            else:
                return m.ppd[i,k,t,n,b-1] - m.ppd[i,k,t,n,b] <= m.ramp_down[k] * m.cap_ava[i,k,t]    
            

        @m.Constraint(m.line, m.year, m.rpdn, m.sub)
        def flows_lb(m, l, t, n, b):
            return -m.cap_ava_line[l,t] <= m.flow[l,t,n,b]
        
        @m.Constraint(m.line, m.year, m.rpdn, m.sub)
        def flows_ub(m, l, t, n, b):
            return m.flow[l,t,n,b] <= m.cap_ava_line[l,t]         
        
        
        @m.Constraint(m.line, m.year, m.rpdn, m.sub)
        def flows_pos_neg(m, l, t, n, b):
            return m.flow[l,t,n,b] == m.flow_pos[l,t,n,b] + m.flow_neg[l,t,n,b]        
        
        
        @m.Constraint(m.node, m.year, m.rpdn, m.sub)
        def nodal_power_balance(m, i, t, n, b):
            return sum(m.ppd[i,k,t,n,b] for k in m.generator) + sum(m.flow[l,t,n,b] for l in m.line_to_node[i]) >= \
                    m.load_demand[i,t,n,b] + sum(m.flow[l,t,n,b] for l in m.line_fr_node[i])
        # m.nodel_power_balance.pprint()           
        
        
                
        @m.Expression()  # unit: M$
        def capital_expenditure(m):
            return sum(m.IC[i,k,t] for i in m.node for k in m.generator for t in m.year)/1000 + \
                sum(m.ICL[l,t] for l in m.line for t in m.year)/1000
        
        @m.Expression()
        def IC_generator(m):
            return sum(m.IC[i,k,t] for i in m.node for k in m.generator for t in m.year)/1000
        
        @m.Expression()
        def IC_line(m):
            return sum(m.ICL[l,t] for l in m.line for t in m.year)/1000 
        
        @m.Expression() # unit: M$
        def operating_expenses(m):
            return sum(m.unit_FC[k,t] * m.cap_ava[i,k,t] for i in m.node for k in m.generator for t in m.year)/1000 + \
                sum(m.unit_FC_line[l,t] * m.cap_ava_line[l,t] for l in m.line for t in m.year)/1000 +\
                    sum(m.weight_time[n] * m.operation_time[b] * m.unit_VC[k,t] * m.ppd[i,k,t,n,b] 
                        for i in m.node for k in m.generator for t in m.year for n in m.rpdn for b in m.sub)/1000000 +\
                        sum(m.weight_time[n] * m.operation_time[b] * m.unit_VC_line[l,t] * (m.flow_pos[l,t,n,b] - m.flow_neg[l,t,n,b])  
                            for l in m.line for t in m.year for n in m.rpdn for b in m.sub)/1000000

        @m.Expression()
        def FOC_generator(m):
            return sum(m.unit_FC[k,t] * m.cap_ava[i,k,t] for i in m.node for k in m.generator for t in m.year)/1000

        @m.Expression()
        def FOC_line(m):
            return sum(m.unit_FC_line[l,t] * m.cap_ava_line[l,t] for l in m.line for t in m.year)/1000
        
        @m.Expression()
        def VOC_generator(m):
            return sum(m.weight_time[n] * m.operation_time[b] * m.unit_VC[k,t] * m.ppd[i,k,t,n,b] 
                       for i in m.node for k in m.generator for t in m.year for n in m.rpdn for b in m.sub)/1000000 
        
        @m.Expression()
        def VOC_line(m):
            return sum(m.weight_time[n] * m.operation_time[b] * m.unit_VC_line[l,t] * (m.flow_pos[l,t,n,b] - m.flow_neg[l,t,n,b])  
                       for l in m.line for t in m.year for n in m.rpdn for b in m.sub)/1000000
            
        # @m.Expression()
        # def OG_pen(m):
        #     return sum(m.weight_time[n] * m.operation_time[b] * m.OG_penalty * m.over_gen[i,t,n,b] for i in m.node for t in m.year for n in m.rpdn for b in m.sub)/1000           

                
        @m.Objective(sense=pyo.minimize)   # unit: M$
        def obj(m):
            return sum(m.IC[i,k,t] for i in m.node for k in m.generator for t in m.year)/1000 + \
                sum(m.ICL[l,t] for l in m.line for t in m.year)/1000 +\
                    sum(m.unit_FC[k,t] * m.cap_ava[i,k,t] for i in m.node for k in m.generator for t in m.year)/1000 + \
                        sum(m.unit_FC_line[l,t] * m.cap_ava_line[l,t] for l in m.line for t in m.year)/1000 +\
                            sum(m.weight_time[n] * m.operation_time[b] * m.unit_VC[k,t] * m.ppd[i,k,t,n,b] 
                                for i in m.node for k in m.generator for t in m.year for n in m.rpdn for b in m.sub)/1000000 +\
                                    sum(m.weight_time[n] * m.operation_time[b] * m.unit_VC_line[l,t] * (m.flow_pos[l,t,n,b] - m.flow_neg[l,t,n,b]) 
                                        for l in m.line for t in m.year for n in m.rpdn for b in m.sub)/1000000
                                            # sum(m.weight_time[n] * m.operation_time[b] * m.OG_penalty * m.over_gen[i,t,n,b] 
                                            #     for i in m.node for t in m.year for n in m.rpdn for b in m.sub)/1000
    
    
    
    
    
    if formulation == 'reserve':    
        m.reserve_ratio = pyo.Param(within=pyo.NonNegativeReals, initialize=0.25)
        
        m.cap_opt = pyo.Var(m.node, m.generator, m.year, m.rpdn, m.sub, within=pyo.NonNegativeReals, doc='Operation capacity')
        m.cap_rev = pyo.Var(m.node, m.generator, m.year, m.rpdn, m.sub, within=pyo.NonNegativeReals, doc='Reserve capacity')
        m.ppd = pyo.Var(m.node, m.generator, m.year, m.rpdn, m.sub, within=pyo.NonNegativeReals, doc='Power produced')
        m.flow = pyo.Var(m.line, m.year, m.rpdn, m.sub, within=pyo.Reals, doc='Power flow')       
        m.flow_pos = pyo.Var(m.line, m.year, m.rpdn, m.sub, within=pyo.NonNegativeReals, doc='Positive power flow')
        m.flow_neg = pyo.Var(m.line, m.year, m.rpdn, m.sub, within=pyo.NonPositiveReals, doc='Negative power flow') 
        # m.over_gen = pyo.Var(m.node, m.year, m.rpdn, m.sub, within=pyo.NonNegativeReals, doc='Excess power')   
    
        @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub)
        def operation_reserve_capacity(m, i, k, t, n, b):
            return m.cap_ava[i,k,t] == m.cap_opt[i,k,t,n,b] + m.cap_rev[i,k,t,n,b]
        
        @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub)
        def power_generation_lb(m, i, k, t, n, b):
            return m.min_opt_dpt[k] * m.cap_opt[i,k,t,n,b] <= m.ppd[i,k,t,n,b]
        
        @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub)
        def power_generation_ub(m, i, k, t, n, b):
            return m.ppd[i,k,t,n,b] <= m.max_opt_dpt[k] * m.cap_opt[i,k,t,n,b]  

        @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub)
        def ramp_up_constraint_rv(m, i, k, t, n, b):
            if b == 1:
                return m.ppd[i,k,t,n,b] <= m.ramp_up[k] * m.cap_opt[i,k,t,n,b]  
            else:
                return m.ppd[i,k,t,n,b] - m.ppd[i,k,t,n,b-1] <= m.ramp_up[k] * m.cap_opt[i,k,t,n,b]    

        @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub)
        def ramp_down_constraint_rv(m, i, k, t, n, b):
            if b == 1:
                return -m.ppd[i,k,t,n,b] <= m.ramp_down[k] * m.cap_opt[i,k,t,n,b]  
            else:
                return m.ppd[i,k,t,n,b-1] - m.ppd[i,k,t,n,b] <= m.ramp_down[k] * m.cap_opt[i,k,t,n,b]  

        
        @m.Constraint(m.node, m.year, m.rpdn, m.sub)
        def reserve_capacity(m, i, t, n, b):
            return sum(m.cap_rev[i,k,t,n,b] for k in m.generator) >= m.reserve_ratio * m.load_demand[i,t,n,b]
            

        @m.Constraint(m.line, m.year, m.rpdn, m.sub)
        def flows_lb(m, l, t, n, b):
            return -m.cap_ava_line[l,t] <= m.flow[l,t,n,b]
        
        @m.Constraint(m.line, m.year, m.rpdn, m.sub)
        def flows_ub(m, l, t, n, b):
            return m.flow[l,t,n,b] <= m.cap_ava_line[l,t]         


        @m.Constraint(m.line, m.year, m.rpdn, m.sub)
        def flows_pos_neg(m, l, t, n, b):
            return m.flow[l,t,n,b] == m.flow_pos[l,t,n,b] + m.flow_neg[l,t,n,b]     
        
        
        @m.Constraint(m.node, m.year, m.rpdn, m.sub)
        def nodal_power_balance(m, i, t, n, b):
            return sum(m.ppd[i,k,t,n,b] for k in m.generator) + sum(m.flow[l,t,n,b] for l in m.line_to_node[i]) >= \
                    m.load_demand[i,t,n,b] + sum(m.flow[l,t,n,b] for l in m.line_fr_node[i])
        # m.nodel_power_balance.pprint()                
        


        @m.Expression()  # unit: M$
        def capital_expenditure(m):
            return sum(m.IC[i,k,t] for i in m.node for k in m.generator for t in m.year)/1000 + \
                sum(m.ICL[l,t] for l in m.line for t in m.year)/1000
        
        @m.Expression()
        def IC_generator(m):
            return sum(m.IC[i,k,t] for i in m.node for k in m.generator for t in m.year)/1000
        
        @m.Expression()
        def IC_line(m):
            return sum(m.ICL[l,t] for l in m.line for t in m.year)/1000 
        
        @m.Expression() # unit: M$
        def operating_expenses(m):
            return sum(m.unit_FC[k,t] * m.cap_ava[i,k,t] for i in m.node for k in m.generator for t in m.year)/1000 + \
                sum(m.unit_FC_line[l,t] * m.cap_ava_line[l,t] for l in m.line for t in m.year)/1000 +\
                    sum(m.weight_time[n] * m.operation_time[b] * m.unit_VC[k,t] * m.ppd[i,k,t,n,b] 
                        for i in m.node for k in m.generator for t in m.year for n in m.rpdn for b in m.sub)/1000000 +\
                        sum(m.weight_time[n] * m.operation_time[b] * m.unit_VC_line[l,t] * (m.flow_pos[l,t,n,b] - m.flow_neg[l,t,n,b])  
                            for l in m.line for t in m.year for n in m.rpdn for b in m.sub)/1000000

        @m.Expression()
        def FOC_generator(m):
            return sum(m.unit_FC[k,t] * m.cap_ava[i,k,t] for i in m.node for k in m.generator for t in m.year)/1000

        @m.Expression()
        def FOC_line(m):
            return sum(m.unit_FC_line[l,t] * m.cap_ava_line[l,t] for l in m.line for t in m.year)/1000
        
        @m.Expression()
        def VOC_generator(m):
            return sum(m.weight_time[n] * m.operation_time[b] * m.unit_VC[k,t] * m.ppd[i,k,t,n,b] 
                       for i in m.node for k in m.generator for t in m.year for n in m.rpdn for b in m.sub)/1000000 
        
        @m.Expression()
        def VOC_line(m):
            return sum(m.weight_time[n] * m.operation_time[b] * m.unit_VC_line[l,t] * (m.flow_pos[l,t,n,b] - m.flow_neg[l,t,n,b])  
                       for l in m.line for t in m.year for n in m.rpdn for b in m.sub)/1000000
            
        # @m.Expression()
        # def OG_pen(m):
        #     return sum(m.weight_time[n] * m.operation_time[b] * m.OG_penalty * m.over_gen[i,t,n,b] for i in m.node for t in m.year for n in m.rpdn for b in m.sub)/1000           

                
        @m.Objective(sense=pyo.minimize)   # unit: M$
        def obj(m):
            return sum(m.IC[i,k,t] for i in m.node for k in m.generator for t in m.year)/1000 + \
                sum(m.ICL[l,t] for l in m.line for t in m.year)/1000 +\
                    sum(m.unit_FC[k,t] * m.cap_ava[i,k,t] for i in m.node for k in m.generator for t in m.year)/1000 + \
                        sum(m.unit_FC_line[l,t] * m.cap_ava_line[l,t] for l in m.line for t in m.year)/1000 +\
                            sum(m.weight_time[n] * m.operation_time[b] * m.unit_VC[k,t] * m.ppd[i,k,t,n,b] 
                                for i in m.node for k in m.generator for t in m.year for n in m.rpdn for b in m.sub)/1000000 +\
                                    sum(m.weight_time[n] * m.operation_time[b] * m.unit_VC_line[l,t] * (m.flow_pos[l,t,n,b] - m.flow_neg[l,t,n,b]) 
                                        for l in m.line for t in m.year for n in m.rpdn for b in m.sub)/1000000
                                            # sum(m.weight_time[n] * m.operation_time[b] * m.OG_penalty * m.over_gen[i,t,n,b] 
                                            #     for i in m.node for t in m.year for n in m.rpdn for b in m.sub)/1000





    if formulation == 'n-1':
        m.scenario = pyo.RangeSet(1,36)  # 1-36, a total of 36 scenarios

        # Read CSV files after defining file paths
        sc_ind_gen = pd.read_csv(os.path.join(curPath, 'sc_ind_gen_n1.csv'), header=0)

        scenario_indicator_gen = {}
        for a in range(sc_ind_gen.shape[0]):
            i = sc_ind_gen['i'].loc[a]
            k = sc_ind_gen['k'].loc[a]
            t = sc_ind_gen['t'].loc[a]
            n = sc_ind_gen['n'].loc[a]
            sc = sc_ind_gen['sc'].loc[a]
            sc_gen = sc_ind_gen['sc_gen'].loc[a]
            scenario_indicator_gen[(i,k,t,n,sc)] = sc_gen
        
        m.scenario_indicator_gen = pyo.Param(m.node, m.generator, m.year, m.rpdn, m.scenario, within=pyo.NonNegativeReals, initialize=scenario_indicator_gen)
        m.scenario_indicator_line = pyo.Param(m.line, m.year, m.rpdn, m.scenario, within=pyo.NonNegativeReals, initialize=1)
        m.scenario_rate = pyo.Param(m.scenario, within=pyo.NonNegativeReals, initialize=0.02778)

        m.cap_sv = pyo.Var(m.node, m.generator, m.year, m.rpdn, m.scenario, within=pyo.NonNegativeReals, doc='Generation capacity survived in scenario')
        m.cap_sv_line = pyo.Var(m.line, m.year, m.rpdn, m.scenario, within=pyo.NonNegativeReals, doc='Line capacity survived in scenario')
        m.cap_sv_avg = pyo.Var(m.node, m.generator, m.year, m.scenario, within=pyo.NonNegativeReals, doc='Average generation capacity survived in scenario')
        m.cap_sv_line_avg = pyo.Var(m.line, m.year, m.scenario, within=pyo.NonNegativeReals, doc='Average line capacity survived in scenario')
        
        m.ppd = pyo.Var(m.node, m.generator, m.year, m.rpdn, m.sub, m.scenario, within=pyo.NonNegativeReals, doc='Power produced in scenario')
        m.flow = pyo.Var(m.line, m.year, m.rpdn, m.sub, m.scenario, within=pyo.Reals, doc='Power flow in scenario')
        m.flow_pos = pyo.Var(m.line, m.year, m.rpdn, m.sub, m.scenario, within=pyo.NonNegativeReals, doc='Positive power flow in scenario')
        m.flow_neg = pyo.Var(m.line, m.year, m.rpdn, m.sub, m.scenario, within=pyo.NonPositiveReals, doc='Negative power flow in scenario')
        # m.over_gen = pyo.Var(m.node, m.year, m.rpdn, m.sub, m.scenario, within=pyo.NonNegativeReals, doc='Excess power in scenario')      
                        
    
        @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.scenario)
        def survived_capacity(m, i, k, t, n, sc):
            return m.cap_sv[i,k,t,n,sc] == m.scenario_indicator_gen[i,k,t,n,sc] * m.cap_ava[i,k,t]
        
        @m.Constraint(m.line, m.year, m.rpdn, m.scenario)
        def survived_capacity_line(m, l, t, n, sc):
            return m.cap_sv_line[l,t,n,sc] == m.scenario_indicator_line[l,t,n,sc] * m.cap_ava_line[l,t]        
        
        @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub, m.scenario)
        def power_generation_lb(m, i, k, t, n, b, sc):
            return m.min_opt_dpt[k] * m.cap_sv[i,k,t,n,sc] <= m.ppd[i,k,t,n,b,sc]
        
        @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub, m.scenario)
        def power_generation_ub(m, i, k, t, n, b, sc):
            return m.ppd[i,k,t,n,b,sc] <= m.max_opt_dpt[k] * m.cap_sv[i,k,t,n,sc]  

        @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub, m.scenario)
        def ramp_up_constraint_n1(m, i, k, t, n, b, sc):
            if b == 1:
                return m.ppd[i,k,t,n,b,sc] <= m.ramp_up[k] * m.cap_sv[i,k,t,n,sc]  
            else:
                return m.ppd[i,k,t,n,b,sc] - m.ppd[i,k,t,n,b-1,sc] <= m.ramp_up[k] * m.cap_sv[i,k,t,n,sc]    

        @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub, m.scenario)
        def ramp_down_constraint_n1(m, i, k, t, n, b, sc):
            if b == 1:
                return -m.ppd[i,k,t,n,b,sc] <= m.ramp_down[k] * m.cap_sv[i,k,t,n,sc] 
            else:
                return m.ppd[i,k,t,n,b-1,sc] - m.ppd[i,k,t,n,b,sc] <= m.ramp_down[k] * m.cap_sv[i,k,t,n,sc]  


        @m.Constraint(m.line, m.year, m.rpdn, m.sub, m.scenario)
        def flows_lb(m, l, t, n, b, sc):
            return -m.cap_sv_line[l,t,n,sc] <= m.flow[l,t,n,b,sc]
        
        @m.Constraint(m.line, m.year, m.rpdn, m.sub, m.scenario)
        def flows_ub(m, l, t, n, b, sc):
            return m.flow[l,t,n,b,sc] <= m.cap_sv_line[l,t,n,sc]   
        
        
        @m.Constraint(m.line, m.year, m.rpdn, m.sub, m.scenario)
        def flows_pos_neg(m, l, t, n, b, sc):
            return m.flow[l,t,n,b,sc] == m.flow_pos[l,t,n,b,sc] + m.flow_neg[l,t,n,b,sc]
        
        
        @m.Constraint(m.node, m.year, m.rpdn, m.sub, m.scenario)
        def nodal_power_balance(m, i, t, n, b, sc):
            return sum(m.ppd[i,k,t,n,b,sc] for k in m.generator) + sum(m.flow[l,t,n,b,sc] for l in m.line_to_node[i]) >= \
                    m.load_demand[i,t,n,b] + sum(m.flow[l,t,n,b,sc] for l in m.line_fr_node[i])
        # for i in m.node:
        #     m.nodal_power_balance[i,1,1,1,1].pprint()              
                
        @m.Constraint(m.node, m.generator, m.year, m.scenario)
        def aggregated_cap_gen(m, i, k, t, sc):
            return m.cap_sv_avg[i,k,t,sc] == sum(m.cap_sv[i,k,t,n,sc] for n in m.rpdn) / len(m.rpdn)
        
        @m.Constraint(m.line, m.year, m.scenario)
        def aggregated_cap_line(m, l, t, sc):
            return m.cap_sv_line_avg[l,t,sc] == sum(m.cap_sv_line[l,t,n,sc] for n in m.rpdn) / len(m.rpdn)                
        
        
        
        @m.Expression()  # unit: M$
        def capital_expenditure(m):
            return sum(m.IC[i,k,t] for i in m.node for k in m.generator for t in m.year)/1000 + sum(m.ICL[l,t] for l in m.line for t in m.year)/1000 

        @m.Expression()
        def IC_generator(m):
            return sum(m.IC[i,k,t] for i in m.node for k in m.generator for t in m.year)/1000
        
        @m.Expression()
        def IC_line(m):
            return sum(m.ICL[l,t] for l in m.line for t in m.year)/1000 
        
        @m.Expression() 
        def operating_expenses(m):
            return sum(m.scenario_rate[sc] * m.unit_FC[k,t] * m.cap_sv_avg[i,k,t,sc] for i in m.node for k in m.generator for t in m.year for sc in m.scenario)/1000 + \
                sum(m.scenario_rate[sc] * m.unit_FC_line[l,t] * m.cap_sv_line_avg[l,t,sc] for l in m.line for t in m.year for sc in m.scenario)/1000 +\
                    sum(m.scenario_rate[sc] * m.weight_time[n] * m.operation_time[b] * m.unit_VC[k,t] * m.ppd[i,k,t,n,b,sc] 
                        for i in m.node for k in m.generator for t in m.year for n in m.rpdn for b in m.sub for sc in m.scenario)/1000000  +\
                            sum(m.scenario_rate[sc] * m.weight_time[n] * m.operation_time[b] * m.unit_VC_line[l,t] * (m.flow_pos[l,t,n,b,sc] - m.flow_neg[l,t,n,b,sc]) 
                                for l in m.line for t in m.year for n in m.rpdn for b in m.sub for sc in m.scenario)/1000000 

        @m.Expression()
        def FOC_generator(m):
            return sum(m.scenario_rate[sc] * m.unit_FC[k,t] * m.cap_sv_avg[i,k,t,sc] for i in m.node for k in m.generator for t in m.year for sc in m.scenario)/1000

        @m.Expression()
        def FOC_line(m):
            return sum(m.scenario_rate[sc] * m.unit_FC_line[l,t] * m.cap_sv_line_avg[l,t,sc] for l in m.line for t in m.year for sc in m.scenario)/1000
        
        @m.Expression()
        def VOC_generator(m):
            return sum(m.scenario_rate[sc] * m.weight_time[n] * m.operation_time[b] * m.unit_VC[k,t] * m.ppd[i,k,t,n,b,sc] 
                       for i in m.node for k in m.generator for t in m.year for n in m.rpdn for b in m.sub for sc in m.scenario)/1000000 
        
        @m.Expression()
        def VOC_line(m):
            return sum(m.scenario_rate[sc] * m.weight_time[n] * m.operation_time[b] * m.unit_VC_line[l,t] * (m.flow_pos[l,t,n,b,sc] - m.flow_neg[l,t,n,b,sc])  
                       for l in m.line for t in m.year for n in m.rpdn for b in m.sub for sc in m.scenario)/1000000    
            
        # @m.Expression()
        # def OG_pen(m):
        #     return sum(m.scenario_rate[sc] * m.weight_time[n] * m.operation_time[b] * m.OG_penalty * m.over_gen[i,t,n,b,sc] 
        #                for i in m.node for t in m.year for n in m.rpdn for b in m.sub for sc in m.scenario)/1000    
                
        @m.Objective(sense=pyo.minimize)   # unit: M$
        def obj(m):
            return sum(m.IC[i,k,t] for i in m.node for k in m.generator for t in m.year)/1000 + sum(m.ICL[l,t] for l in m.line for t in m.year)/1000 +\
                sum(m.scenario_rate[sc] * m.unit_FC[k,t] * m.cap_sv_avg[i,k,t,sc] for i in m.node for k in m.generator for t in m.year for sc in m.scenario)/1000 + \
                    sum(m.scenario_rate[sc] * m.unit_FC_line[l,t] * m.cap_sv_line_avg[l,t,sc] for l in m.line for t in m.year for sc in m.scenario)/1000 +\
                        sum(m.scenario_rate[sc] * m.weight_time[n] * m.operation_time[b] * m.unit_VC[k,t] * m.ppd[i,k,t,n,b,sc] 
                            for i in m.node for k in m.generator for t in m.year for n in m.rpdn for b in m.sub for sc in m.scenario)/1000000 +\
                                sum(m.scenario_rate[sc] * m.weight_time[n] * m.operation_time[b] * m.unit_VC_line[l,t] * (m.flow_pos[l,t,n,b,sc] - m.flow_neg[l,t,n,b,sc]) 
                                    for l in m.line for t in m.year for n in m.rpdn for b in m.sub for sc in m.scenario)/1000000
                                        # sum(m.scenario_rate[sc] * m.weight_time[n] * m.operation_time[b] * m.OG_penalty * m.over_gen[i,t,n,b,sc] 
                                        #     for i in m.node for t in m.year for n in m.rpdn for b in m.sub for sc in m.scenario)/1000             



    if formulation == 'n-2':
        m.scenario = pyo.RangeSet(1,36)  # 1-36, a total of 36 scenarios
        
        # Read CSV files after defining file paths
        sc_ind_gen = pd.read_csv(os.path.join(curPath, 'sc_ind_gen_n2.csv'), header=0)

        scenario_indicator_gen = {}
        for a in range(sc_ind_gen.shape[0]):
            i = sc_ind_gen['i'].loc[a]
            k = sc_ind_gen['k'].loc[a]
            t = sc_ind_gen['t'].loc[a]
            n = sc_ind_gen['n'].loc[a]
            sc = sc_ind_gen['sc'].loc[a]
            sc_gen = sc_ind_gen['sc_gen'].loc[a]
            scenario_indicator_gen[(i,k,t,n,sc)] = sc_gen
        
        m.scenario_indicator_gen = pyo.Param(m.node, m.generator, m.year, m.rpdn, m.scenario, within=pyo.NonNegativeReals, initialize=scenario_indicator_gen)
        m.scenario_indicator_line = pyo.Param(m.line, m.year, m.rpdn, m.scenario, within=pyo.NonNegativeReals, initialize=1)
        m.scenario_rate = pyo.Param(m.scenario, within=pyo.NonNegativeReals, initialize=0.02778)

        m.cap_sv = pyo.Var(m.node, m.generator, m.year, m.rpdn, m.scenario, within=pyo.NonNegativeReals, doc='Generation capacity survived in scenario')
        m.cap_sv_line = pyo.Var(m.line, m.year, m.rpdn, m.scenario, within=pyo.NonNegativeReals, doc='Line capacity survived in scenario')
        m.cap_sv_avg = pyo.Var(m.node, m.generator, m.year, m.scenario, within=pyo.NonNegativeReals, doc='Average generation capacity survived in scenario')
        m.cap_sv_line_avg = pyo.Var(m.line, m.year, m.scenario, within=pyo.NonNegativeReals, doc='Average line capacity survived in scenario')
        
        m.ppd = pyo.Var(m.node, m.generator, m.year, m.rpdn, m.sub, m.scenario, within=pyo.NonNegativeReals, doc='Power produced in scenario')
        m.flow = pyo.Var(m.line, m.year, m.rpdn, m.sub, m.scenario, within=pyo.Reals, doc='Power flow in scenario')
        m.flow_pos = pyo.Var(m.line, m.year, m.rpdn, m.sub, m.scenario, within=pyo.NonNegativeReals, doc='Positive power flow in scenario')
        m.flow_neg = pyo.Var(m.line, m.year, m.rpdn, m.sub, m.scenario, within=pyo.NonPositiveReals, doc='Negative power flow in scenario')
        # m.over_gen = pyo.Var(m.node, m.year, m.rpdn, m.sub, m.scenario, within=pyo.NonNegativeReals, doc='Excess power in scenario')      
                        
    
        @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.scenario)
        def survived_capacity(m, i, k, t, n, sc):
            return m.cap_sv[i,k,t,n,sc] == m.scenario_indicator_gen[i,k,t,n,sc] * m.cap_ava[i,k,t]
        
        @m.Constraint(m.line, m.year, m.rpdn, m.scenario)
        def survived_capacity_line(m, l, t, n, sc):
            return m.cap_sv_line[l,t,n,sc] == m.scenario_indicator_line[l,t,n,sc] * m.cap_ava_line[l,t]        
        
        @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub, m.scenario)
        def power_generation_lb(m, i, k, t, n, b, sc):
            return m.min_opt_dpt[k] * m.cap_sv[i,k,t,n,sc] <= m.ppd[i,k,t,n,b,sc]
        
        @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub, m.scenario)
        def power_generation_ub(m, i, k, t, n, b, sc):
            return m.ppd[i,k,t,n,b,sc] <= m.max_opt_dpt[k] * m.cap_sv[i,k,t,n,sc]  

        @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub, m.scenario)
        def ramp_up_constraint_n1(m, i, k, t, n, b, sc):
            if b == 1:
                return m.ppd[i,k,t,n,b,sc] <= m.ramp_up[k] * m.cap_sv[i,k,t,n,sc]  
            else:
                return m.ppd[i,k,t,n,b,sc] - m.ppd[i,k,t,n,b-1,sc] <= m.ramp_up[k] * m.cap_sv[i,k,t,n,sc]    

        @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub, m.scenario)
        def ramp_down_constraint_n1(m, i, k, t, n, b, sc):
            if b == 1:
                return -m.ppd[i,k,t,n,b,sc] <= m.ramp_down[k] * m.cap_sv[i,k,t,n,sc] 
            else:
                return m.ppd[i,k,t,n,b-1,sc] - m.ppd[i,k,t,n,b,sc] <= m.ramp_down[k] * m.cap_sv[i,k,t,n,sc]  


        @m.Constraint(m.line, m.year, m.rpdn, m.sub, m.scenario)
        def flows_lb(m, l, t, n, b, sc):
            return -m.cap_sv_line[l,t,n,sc] <= m.flow[l,t,n,b,sc]
        
        @m.Constraint(m.line, m.year, m.rpdn, m.sub, m.scenario)
        def flows_ub(m, l, t, n, b, sc):
            return m.flow[l,t,n,b,sc] <= m.cap_sv_line[l,t,n,sc]   
        
        
        @m.Constraint(m.line, m.year, m.rpdn, m.sub, m.scenario)
        def flows_pos_neg(m, l, t, n, b, sc):
            return m.flow[l,t,n,b,sc] == m.flow_pos[l,t,n,b,sc] + m.flow_neg[l,t,n,b,sc]
        
        
        @m.Constraint(m.node, m.year, m.rpdn, m.sub, m.scenario)
        def nodal_power_balance(m, i, t, n, b, sc):
            return sum(m.ppd[i,k,t,n,b,sc] for k in m.generator) + sum(m.flow[l,t,n,b,sc] for l in m.line_to_node[i]) >= \
                    m.load_demand[i,t,n,b] + sum(m.flow[l,t,n,b,sc] for l in m.line_fr_node[i])
        # for i in m.node:
        #     m.nodal_power_balance[i,1,1,1,1].pprint()              
                
        @m.Constraint(m.node, m.generator, m.year, m.scenario)
        def aggregated_cap_gen(m, i, k, t, sc):
            return m.cap_sv_avg[i,k,t,sc] == sum(m.cap_sv[i,k,t,n,sc] for n in m.rpdn) / len(m.rpdn)
        
        @m.Constraint(m.line, m.year, m.scenario)
        def aggregated_cap_line(m, l, t, sc):
            return m.cap_sv_line_avg[l,t,sc] == sum(m.cap_sv_line[l,t,n,sc] for n in m.rpdn) / len(m.rpdn)                
        
        
        
        @m.Expression()  # unit: M$
        def capital_expenditure(m):
            return sum(m.IC[i,k,t] for i in m.node for k in m.generator for t in m.year)/1000 + sum(m.ICL[l,t] for l in m.line for t in m.year)/1000 

        @m.Expression()
        def IC_generator(m):
            return sum(m.IC[i,k,t] for i in m.node for k in m.generator for t in m.year)/1000
        
        @m.Expression()
        def IC_line(m):
            return sum(m.ICL[l,t] for l in m.line for t in m.year)/1000 
        
        @m.Expression() 
        def operating_expenses(m):
            return sum(m.scenario_rate[sc] * m.unit_FC[k,t] * m.cap_sv_avg[i,k,t,sc] for i in m.node for k in m.generator for t in m.year for sc in m.scenario)/1000 + \
                sum(m.scenario_rate[sc] * m.unit_FC_line[l,t] * m.cap_sv_line_avg[l,t,sc] for l in m.line for t in m.year for sc in m.scenario)/1000 +\
                    sum(m.scenario_rate[sc] * m.weight_time[n] * m.operation_time[b] * m.unit_VC[k,t] * m.ppd[i,k,t,n,b,sc] 
                        for i in m.node for k in m.generator for t in m.year for n in m.rpdn for b in m.sub for sc in m.scenario)/1000000  +\
                            sum(m.scenario_rate[sc] * m.weight_time[n] * m.operation_time[b] * m.unit_VC_line[l,t] * (m.flow_pos[l,t,n,b,sc] - m.flow_neg[l,t,n,b,sc]) 
                                for l in m.line for t in m.year for n in m.rpdn for b in m.sub for sc in m.scenario)/1000000 

        @m.Expression()
        def FOC_generator(m):
            return sum(m.scenario_rate[sc] * m.unit_FC[k,t] * m.cap_sv_avg[i,k,t,sc] for i in m.node for k in m.generator for t in m.year for sc in m.scenario)/1000

        @m.Expression()
        def FOC_line(m):
            return sum(m.scenario_rate[sc] * m.unit_FC_line[l,t] * m.cap_sv_line_avg[l,t,sc] for l in m.line for t in m.year for sc in m.scenario)/1000
        
        @m.Expression()
        def VOC_generator(m):
            return sum(m.scenario_rate[sc] * m.weight_time[n] * m.operation_time[b] * m.unit_VC[k,t] * m.ppd[i,k,t,n,b,sc] 
                       for i in m.node for k in m.generator for t in m.year for n in m.rpdn for b in m.sub for sc in m.scenario)/1000000 
        
        @m.Expression()
        def VOC_line(m):
            return sum(m.scenario_rate[sc] * m.weight_time[n] * m.operation_time[b] * m.unit_VC_line[l,t] * (m.flow_pos[l,t,n,b,sc] - m.flow_neg[l,t,n,b,sc])  
                       for l in m.line for t in m.year for n in m.rpdn for b in m.sub for sc in m.scenario)/1000000    
            
        # @m.Expression()
        # def OG_pen(m):
        #     return sum(m.scenario_rate[sc] * m.weight_time[n] * m.operation_time[b] * m.OG_penalty * m.over_gen[i,t,n,b,sc] 
        #                for i in m.node for t in m.year for n in m.rpdn for b in m.sub for sc in m.scenario)/1000    
                
        @m.Objective(sense=pyo.minimize)   # unit: M$
        def obj(m):
            return sum(m.IC[i,k,t] for i in m.node for k in m.generator for t in m.year)/1000 + sum(m.ICL[l,t] for l in m.line for t in m.year)/1000 +\
                sum(m.scenario_rate[sc] * m.unit_FC[k,t] * m.cap_sv_avg[i,k,t,sc] for i in m.node for k in m.generator for t in m.year for sc in m.scenario)/1000 + \
                    sum(m.scenario_rate[sc] * m.unit_FC_line[l,t] * m.cap_sv_line_avg[l,t,sc] for l in m.line for t in m.year for sc in m.scenario)/1000 +\
                        sum(m.scenario_rate[sc] * m.weight_time[n] * m.operation_time[b] * m.unit_VC[k,t] * m.ppd[i,k,t,n,b,sc] 
                            for i in m.node for k in m.generator for t in m.year for n in m.rpdn for b in m.sub for sc in m.scenario)/1000000 +\
                                sum(m.scenario_rate[sc] * m.weight_time[n] * m.operation_time[b] * m.unit_VC_line[l,t] * (m.flow_pos[l,t,n,b,sc] - m.flow_neg[l,t,n,b,sc]) 
                                    for l in m.line for t in m.year for n in m.rpdn for b in m.sub for sc in m.scenario)/1000000 
                                        # sum(m.scenario_rate[sc] * m.weight_time[n] * m.operation_time[b] * m.OG_penalty * m.over_gen[i,t,n,b,sc] 
                                        #     for i in m.node for t in m.year for n in m.rpdn for b in m.sub for sc in m.scenario)/1000  

    
    
    if formulation == 'prob':
        m.state = pyo.RangeSet(1,8)  # 1 -- 8

        min_ins_cap_backup = {k: 10 for k in m.generator} 
        m.min_ins_cap_backup = pyo.Param(m.generator, within=pyo.NonNegativeReals, initialize=min_ins_cap_backup)
        
        max_ins_cap_backup = {k: 1500 for k in m.generator} 
        m.max_ins_cap_backup = pyo.Param(m.generator, within=pyo.NonNegativeReals, initialize=max_ins_cap_backup)


        probability = pd.read_csv(os.path.join(curPath, 'prob.csv'), header=0)
        prob_state = {}
        for a in range(probability.shape[0]):
            st = probability['st'].loc[a]
            prob = probability['prob'].loc[a]
            prob_state[st] = prob
        m.prob = pyo.Param(m.state, within=pyo.NonNegativeReals, initialize=prob_state)
        
        state_ind_gen = pd.read_csv(os.path.join(curPath, 'state_ind_gen.csv'), header=0)        
        state_indicator = {}
        for a in range(state_ind_gen.shape[0]):
            i = state_ind_gen['i'].loc[a]
            k = state_ind_gen['k'].loc[a]
            st = state_ind_gen['st'].loc[a]
            state_gen = state_ind_gen['state_gen'].loc[a]
            state_indicator[(i,k,st)] = state_gen
        m.state_indicator_gen = pyo.Param(m.node, m.generator, m.state, within=pyo.NonNegativeReals, initialize=state_indicator)   


        state_ind_backup = pd.read_csv(os.path.join(curPath, 'state_ind_backup.csv'), header=0)        
        state_indicator_b = {}
        for a in range(state_ind_backup.shape[0]):
            i = state_ind_backup['i'].loc[a]
            k = state_ind_backup['k'].loc[a]
            st = state_ind_backup['st'].loc[a]
            state_backup = state_ind_backup['state_backup'].loc[a]
            state_indicator_b[(i,k,st)] = state_backup
        m.state_indicator_backup = pyo.Param(m.node, m.generator, m.state, within=pyo.NonNegativeReals, initialize=state_indicator_b)   

        m.state_indicator_line = pyo.Param(m.line, m.state, within=pyo.NonNegativeReals, initialize=1)
        
        unit_IC_backup = {}
        for k in m.generator:
            for t in m.year:
                unit_IC_backup[k,t] = 120
        m.unit_IC_backup = pyo.Param(m.generator, m.year, within=pyo.NonNegativeReals, initialize=unit_IC_backup) # unit: k$

        unit_FC_backup = {}
        for k in m.generator:
            for t in m.year:
                unit_FC_backup[k,t] = 12
        m.unit_FC_backup = pyo.Param(m.generator, m.year, within=pyo.NonNegativeReals, initialize=unit_FC_backup)  # unit: k$

        m.UD_penalty = pyo.Param(within=pyo.NonNegativeReals, initialize=9)  # unit: k$/MWh

    
        ub_IC_backup = {}
        for k in m.generator:
            for t in m.year:
                ub_IC_backup[k,t] = m.max_ins_cap_backup[k] * m.unit_IC_backup[k,t]
        m.ub_IC_backup = pyo.Param(m.generator, m.year, within=pyo.NonNegativeReals, initialize=ub_IC_backup) 

        def _bounds_cap_ins_backup_rule(m, i, k, t):
            return (0, m.max_ins_cap_backup[k])          
        
        def _bounds_IC_backup_rule(m, i, k, t):
            return (0, m.ub_IC_backup[k,t]) 
        
        def _bounds_load_shedding_rule(m, i, t, n, b, st):
            return (0, m.load_demand[i,t,n,b])
        
        def _bounds_EENS_rule(m, i, t, n, b, st):
            return (0, m.load_demand[i,t,n,b])
        
        def _bounds_LOLE_rule(m, i, t, n, b, st):
            return (0, m.operation_time[b])    


        m.cap_bn = pyo.Var(m.node, m.generator, m.year, within=pyo.NonNegativeReals, bounds=_bounds_cap_ins_backup_rule, doc='Capacity of backup generators')
        m.cap_b = pyo.Var(m.node, m.generator, m.year, within=pyo.NonNegativeReals, doc='Capacity of backup generators available')
        m.ICB = pyo.Var(m.node, m.generator, m.year, bounds=_bounds_IC_backup_rule, within=pyo.NonNegativeReals, doc='Investment cost of backup generator')
        
        m.cap_sv = pyo.Var(m.node, m.generator, m.year, m.state, within=pyo.NonNegativeReals, doc='Generation capacity survived in state')
        m.cap_sv_b = pyo.Var(m.node, m.generator, m.year, m.state, within=pyo.NonNegativeReals, doc='Backup capacity survived in state')
        m.cap_sv_line = pyo.Var(m.line, m.year, m.state, within=pyo.NonNegativeReals, doc='Line capacity survived in state')
        m.ppd = pyo.Var(m.node, m.generator, m.year, m.rpdn, m.sub, m.state, within=pyo.NonNegativeReals, doc='Power produced from the main generator in state')
        m.ppd_b = pyo.Var(m.node, m.generator, m.year, m.rpdn, m.sub, m.state, within=pyo.NonNegativeReals, doc='Power produced from the backup in state')
        m.flow = pyo.Var(m.line, m.year, m.rpdn, m.sub, m.state, within=pyo.Reals, doc='Power flow in state')
        m.flow_pos = pyo.Var(m.line, m.year, m.rpdn, m.sub, m.state, within=pyo.NonNegativeReals, doc='Positive power flow in state')
        m.flow_neg = pyo.Var(m.line, m.year, m.rpdn, m.sub, m.state, within=pyo.NonPositiveReals, doc='Negative power flow in state')            
        m.ls = pyo.Var(m.node, m.year, m.rpdn, m.sub, m.state, within=pyo.NonNegativeReals, bounds=_bounds_load_shedding_rule, doc='Load shedding in state')
        m.over_gen = pyo.Var(m.node, m.year, m.rpdn, m.sub, m.state, within=pyo.NonNegativeReals, doc='Over-generation in state')
        
        m.LOLE = pyo.Var(m.node, m.year, m.rpdn, m.sub, m.state, within=pyo.NonNegativeReals, bounds=_bounds_LOLE_rule, doc='LOLE in state')
        m.EENS = pyo.Var(m.node, m.year, m.rpdn, m.sub, m.state, within=pyo.NonNegativeReals, bounds=_bounds_EENS_rule, doc='EENS in state')
        m.TLOLE = pyo.Var(m.node, m.year, m.rpdn, m.sub, within=pyo.NonNegativeReals, doc='Total LOLE')
        m.TEENS = pyo.Var(m.node, m.year, m.rpdn, m.sub, within=pyo.NonNegativeReals, doc='Total EENS')        


        ## Installation of generators
        @m.Disjunct(m.node, m.generator, m.year)
        def backup_install(disj, i, k, t):
            disj.install_cap_res1 = pyo.Constraint(expr= m.min_ins_cap_backup[k] <= m.cap_bn[i,k,t])
            disj.install_cap_res2 = pyo.Constraint(expr= m.cap_bn[i,k,t] <= m.max_ins_cap_backup[k])
            disj.invest_cost_res =  pyo.Constraint(expr= m.ICB[i,k,t] == m.unit_IC_backup[k,t] * m.cap_bn[i,k,t])
        
        @m.Disjunct(m.node, m.generator, m.year)
        def backup_install_no(outer, i, k, t):
            outer.invest_cost_res_no = pyo.Constraint(expr= m.cap_bn[i,k,t] == 0)
            outer.install_cap_res_no = pyo.Constraint(expr= m.ICB[i,k,t] == 0)
            
        @m.Disjunction(m.node, m.generator, m.year)
        def Ornot_backup_install(m, i, k, t):
            return [m.backup_install[i,k,t], m.backup_install_no[i,k,t]]    


        ## Available capacity of backup generators         
        @m.Constraint(m.node, m.generator, m.year)
        def availability_capacity_backup(m, i, k, t):
            return m.cap_b[i,k,t] == sum(m.cap_bn[i,k,tq] for tq in range(1,t+1))
        # m.availability_capacity_gen.pprint()
        
        
        ## Capacity between main and backup         
        @m.Constraint(m.node, m.generator, m.year)
        def main_backup_capacity(m, i, k, t):
            return m.cap_b[i,k,t] <= m.cap_ava[i,k,t]
        # m.availability_capacity_gen.pprint()        
        
    
        @m.Constraint(m.node, m.generator, m.year, m.state)
        def survived_main_capacity(m, i, k, t, st):
            return m.cap_sv[i,k,t,st] == m.state_indicator_gen[i,k,st] * m.cap_ava[i,k,t] 
        
        @m.Constraint(m.node, m.generator, m.year, m.state)
        def survived_backup_capacity(m, i, k, t, st):
            return m.cap_sv_b[i,k,t,st] == m.state_indicator_backup[i,k,st] * m.cap_b[i,k,t]        
        
        @m.Constraint(m.line, m.year, m.state)
        def survived_capacity_line(m, l, t, st):
            return m.cap_sv_line[l,t,st] == m.state_indicator_line[l,st] * m.cap_ava_line[l,t]        
        
        @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub, m.state)
        def power_generation_lb(m, i, k, t, n, b, st):
            return m.min_opt_dpt[k] * m.cap_sv[i,k,t,st] <= m.ppd[i,k,t,n,b,st]
        
        @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub, m.state)
        def power_generation_ub(m, i, k, t, n, b, st):
            return m.ppd[i,k,t,n,b,st] <= m.max_opt_dpt[k] * m.cap_sv[i,k,t,st]  

        @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub, m.state)
        def backup_power_generation_lb(m, i, k, t, n, b, st):
            return m.min_opt_dpt[k] * m.cap_sv_b[i,k,t,st] <= m.ppd_b[i,k,t,n,b,st]
        
        @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub, m.state)
        def backup_power_generation_ub(m, i, k, t, n, b, st):
            return m.ppd_b[i,k,t,n,b,st] <= m.max_opt_dpt[k] * m.cap_sv_b[i,k,t,st]  
        
        
        @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub, m.state)
        def ramp_up_constraint_prob(m, i, k, t, n, b, st):
            if b == 1:
                return m.ppd[i,k,t,n,b,st] <= m.ramp_up[k] * m.cap_sv[i,k,t,st]  
            else:
                return m.ppd[i,k,t,n,b,st] - m.ppd[i,k,t,n,b-1,st] <= m.ramp_up[k] * m.cap_sv[i,k,t,st] 

        @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub, m.state)
        def ramp_down_constraint_prob(m, i, k, t, n, b, st):
            if b == 1:
                return -m.ppd[i,k,t,n,b,st] <= m.ramp_down[k] * m.cap_sv[i,k,t,st] 
            else:
                return m.ppd[i,k,t,n,b-1,st] - m.ppd[i,k,t,n,b,st] <= m.ramp_down[k] * m.cap_sv[i,k,t,st]          

        @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub, m.state)
        def backup_ramp_up_constraint_prob(m, i, k, t, n, b, st):
            if b == 1:
                return m.ppd_b[i,k,t,n,b,st] <= m.ramp_up[k] * m.cap_sv_b[i,k,t,st]  
            else:
                return m.ppd_b[i,k,t,n,b,st] - m.ppd_b[i,k,t,n,b-1,st] <= m.ramp_up[k] * m.cap_sv_b[i,k,t,st] 

        @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub, m.state)
        def backup_ramp_down_constraint_prob(m, i, k, t, n, b, st):
            if b == 1:
                return -m.ppd_b[i,k,t,n,b,st] <= m.ramp_down[k] * m.cap_sv_b[i,k,t,st] 
            else:
                return m.ppd_b[i,k,t,n,b-1,st] - m.ppd_b[i,k,t,n,b,st] <= m.ramp_down[k] * m.cap_sv_b[i,k,t,st]   
            

        @m.Constraint(m.line, m.year, m.rpdn, m.sub, m.state)
        def flows_lb(m, l, t, n, b, st):
            return -m.cap_sv_line[l,t,st] <= m.flow[l,t,n,b,st]
        
        @m.Constraint(m.line, m.year, m.rpdn, m.sub, m.state)
        def flows_ub(m, l, t, n, b, st):
            return m.flow[l,t,n,b,st] <= m.cap_sv_line[l,t,st]     
        

        @m.Constraint(m.line, m.year, m.rpdn, m.sub, m.state)
        def flows_pos_neg(m, l, t, n, b, st):
            return m.flow[l,t,n,b,st] == m.flow_pos[l,t,n,b,st] + m.flow_neg[l,t,n,b,st]           
            
        
        @m.Constraint(m.node, m.year, m.rpdn, m.sub, m.state)
        def nodal_power_balance(m, i, t, n, b, st):
            return sum(m.ppd[i,k,t,n,b,st] for k in m.generator) + sum(m.ppd_b[i,k,t,n,b,st] for k in m.generator) + sum(m.flow[l,t,n,b,st] for l in m.line_to_node[i]) + m.ls[i,t,n,b,st] == \
                    m.load_demand[i,t,n,b] + sum(m.flow[l,t,n,b,st] for l in m.line_fr_node[i]) + m.over_gen[i,t,n,b,st]
        # m.nodel_power_balance.pprint()           
        
        
        ## LOLE and EENS evaluation
        @m.Disjunct(m.node, m.year, m.rpdn, m.sub, m.state)
        def load_shdding_yes(disj, i, t, n, b, st):
            disj.load_shedding_state = pyo.Constraint(expr= m.ls[i,t,n,b,st] >= 0.00002)
            disj.LOLE_state = pyo.Constraint(expr= m.LOLE[i,t,n,b,st] == m.operation_time[b])
            disj.EENS_state = pyo.Constraint(expr= m.EENS[i,t,n,b,st] == m.ls[i,t,n,b,st])
        # m.load_shdding_yes[1,1,1,1,1].pprint()

        @m.Disjunct(m.node, m.year, m.rpdn, m.sub, m.state)
        def load_shdding_no(disj, i, t, n, b, st):
            disj.load_shedding_state_no = pyo.Constraint(expr= m.ls[i,t,n,b,st] <= 0.00001)
            disj.LOLE_state_no = pyo.Constraint(expr= m.LOLE[i,t,n,b,st] == 0)
            disj.EENS_state_no = pyo.Constraint(expr= m.EENS[i,t,n,b,st] == 0)
        # m.load_shdding_no[1,1,1,1,1].pprint()
            
        @m.Disjunction(m.node, m.year, m.rpdn, m.sub, m.state)
        def Ornot_load_shedding(m, i, t, n, b, st):
            return [m.load_shdding_yes[i,t,n,b,st], m.load_shdding_no[i,t,n,b,st]]        
 
        @m.Constraint(m.node, m.year, m.rpdn, m.sub)
        def total_LOLE(m, i, t, n, b):
            return m.TLOLE[i,t,n,b] == sum(m.prob[st] * m.LOLE[i,t,n,b,st] for st in m.state)

        @m.Constraint(m.node, m.year, m.rpdn, m.sub)
        def total_EENS(m, i, t, n, b):
            return m.TEENS[i,t,n,b] == sum(m.prob[st] * m.EENS[i,t,n,b,st] for st in m.state)

        # @m.Constraint(m.year)
        # def LOLE_limit(m, t):
        #     return sum(m.weight_time[n] * m.TLOLE[i,t,n,b] for i in m.node for n in m.rpdn for b in m.sub) <= 2.4 
        
        
        @m.Expression()  # unit: M$
        def capital_expenditure(m):
            return sum(m.IC[i,k,t] for i in m.node for k in m.generator for t in m.year)/1000 + sum(m.ICB[i,k,t] for i in m.node for k in m.generator for t in m.year)/1000 +\
                + sum(m.ICL[l,t] for l in m.line for t in m.year)/1000 

        @m.Expression()
        def IC_generator(m):
            return sum(m.IC[i,k,t] for i in m.node for k in m.generator for t in m.year)/1000 
        
        @m.Expression()
        def IC_line(m):
            return sum(m.ICL[l,t] for l in m.line for t in m.year)/1000 

        @m.Expression()
        def IC_backup(m):
            return sum(m.ICB[i,k,t] for i in m.node for k in m.generator for t in m.year)/1000
        
        @m.Expression() 
        def operating_expenses(m):
            return sum(m.prob[st] * m.unit_FC[k,t] * m.cap_sv[i,k,t,st] for i in m.node for k in m.generator for t in m.year for st in m.state)/1000 + \
                sum(m.prob[st] * m.unit_FC_line[l,t] * m.cap_sv_line[l,t,st] for l in m.line for t in m.year for st in m.state)/1000 +\
                    sum(m.prob[st] * m.unit_FC_backup[k,t] * m.cap_sv_b[i,k,t,st] for i in m.node for k in m.generator for t in m.year for st in m.state)/1000 +\
                        sum(m.prob[st] * m.weight_time[n] * m.operation_time[b] * m.unit_VC[k,t] * (m.ppd[i,k,t,n,b,st] + m.ppd_b[i,k,t,n,b,st]) 
                            for i in m.node for k in m.generator for t in m.year for n in m.rpdn for b in m.sub for st in m.state)/1000000 +\
                                sum(m.prob[st] * m.weight_time[n] * m.operation_time[b] * m.unit_VC_line[l,t] * (m.flow_pos[l,t,n,b,st] - m.flow_neg[l,t,n,b,st])  
                                    for l in m.line for t in m.year for n in m.rpdn for b in m.sub for st in m.state)/1000000

        @m.Expression()
        def FOC_generator(m):
            return sum(m.prob[st] * m.unit_FC[k,t] * m.cap_sv[i,k,t,st] for i in m.node for k in m.generator for t in m.year for st in m.state)/1000 

        @m.Expression()
        def FOC_line(m):
            return sum(m.prob[st] * m.unit_FC_line[l,t] * m.cap_sv_line[l,t,st] for l in m.line for t in m.year for st in m.state)/1000

        @m.Expression()
        def FOC_backup(m):
            return sum(m.prob[st] * m.unit_FC_backup[k,t] * m.cap_sv_b[i,k,t,st] for i in m.node for k in m.generator for t in m.year for st in m.state)/1000
        
        
        @m.Expression()
        def VOC_generator_backup(m):
            return sum(m.prob[st] * m.weight_time[n] * m.operation_time[b] * m.unit_VC[k,t] * (m.ppd[i,k,t,n,b,st] + m.ppd_b[i,k,t,n,b,st]) 
                       for i in m.node for k in m.generator for t in m.year for n in m.rpdn for b in m.sub for st in m.state)/1000000 

        @m.Expression()
        def VOC_line(m):
            return sum(m.prob[st] * m.weight_time[n] * m.operation_time[b] * m.unit_VC_line[l,t] * (m.flow_pos[l,t,n,b,st] - m.flow_neg[l,t,n,b,st])  
                       for l in m.line for t in m.year for n in m.rpdn for b in m.sub for st in m.state)/1000000  
        
        @m.Expression()
        def OG_pen(m):
            return sum(m.prob[st] * m.weight_time[n] * m.operation_time[b] * m.OG_penalty * m.over_gen[i,t,n,b,st] 
                       for i in m.node for t in m.year for n in m.rpdn for b in m.sub for st in m.state)/1000                 

        @m.Expression() # unit: M$
        def EENS_penalties(m):
            return sum(m.weight_time[n] * m.operation_time[b] * m.UD_penalty * m.TEENS[i,t,n,b] for i in m.node for t in m.year for n in m.rpdn for b in m.sub)/1000     
                
        @m.Objective(sense=pyo.minimize)   # unit: M$
        def obj(m):
            return sum(m.IC[i,k,t] for i in m.node for k in m.generator for t in m.year)/1000 + \
                sum(m.ICB[i,k,t] for i in m.node for k in m.generator for t in m.year)/1000 + sum(m.ICL[l,t] for l in m.line for t in m.year)/1000 +\
                    sum(m.prob[st] * m.unit_FC[k,t] * m.cap_sv[i,k,t,st] for i in m.node for k in m.generator for t in m.year for st in m.state)/1000 + \
                        sum(m.prob[st] * m.unit_FC_line[l,t] * m.cap_sv_line[l,t,st] for l in m.line for t in m.year for st in m.state)/1000 +\
                            sum(m.prob[st] * m.unit_FC_backup[k,t] * m.cap_sv_b[i,k,t,st] for i in m.node for k in m.generator for t in m.year for st in m.state)/1000 +\
                                sum(m.prob[st] * m.weight_time[n] * m.operation_time[b] * m.unit_VC[k,t] * (m.ppd[i,k,t,n,b,st] + m.ppd_b[i,k,t,n,b,st]) 
                                    for i in m.node for k in m.generator for t in m.year for n in m.rpdn for b in m.sub for st in m.state)/1000000 +\
                                        sum(m.prob[st] * m.weight_time[n] * m.operation_time[b] * m.unit_VC_line[l,t] * (m.flow_pos[l,t,n,b,st] - m.flow_neg[l,t,n,b,st]) 
                                            for l in m.line for t in m.year for n in m.rpdn for b in m.sub for st in m.state)/1000000 +\
                                                sum(m.prob[st] * m.weight_time[n] * m.operation_time[b] * m.OG_penalty * m.over_gen[i,t,n,b,st] 
                                                    for i in m.node for t in m.year for n in m.rpdn for b in m.sub for st in m.state)/1000 +\
                                                        sum(m.weight_time[n] * m.operation_time[b] * m.UD_penalty * m.TEENS[i,t,n,b] for i in m.node for t in m.year for n in m.rpdn for b in m.sub)/1000     


        # @m.Objective(sense=pyo.minimize)
        # def LOLE_obj(m):
        #     return sum(m.weight_time[n] * m.TLOLE[i,t,n,b] for i in m.node for t in m.year for n in m.rpdn for b in m.sub)  


    if formulation == 'prob-dual':
        m.state = pyo.RangeSet(1,8)  # 1 -- 8

        min_ins_cap_backup = {k: 10 for k in m.generator} 
        m.min_ins_cap_backup = pyo.Param(m.generator, within=pyo.NonNegativeReals, initialize=min_ins_cap_backup)
        
        max_ins_cap_backup = {k: 1500 for k in m.generator} 
        m.max_ins_cap_backup = pyo.Param(m.generator, within=pyo.NonNegativeReals, initialize=max_ins_cap_backup)


        probability = pd.read_csv(os.path.join(curPath, 'prob.csv'), header=0)
        prob_state = {}
        for a in range(probability.shape[0]):
            st = probability['st'].loc[a]
            prob = probability['prob'].loc[a]
            prob_state[st] = prob
        m.prob = pyo.Param(m.state, within=pyo.NonNegativeReals, initialize=prob_state)
        
        state_ind_gen = pd.read_csv(os.path.join(curPath, 'state_ind_gen.csv'), header=0)        
        state_indicator = {}
        for a in range(state_ind_gen.shape[0]):
            i = state_ind_gen['i'].loc[a]
            k = state_ind_gen['k'].loc[a]
            st = state_ind_gen['st'].loc[a]
            state_gen = state_ind_gen['state_gen'].loc[a]
            state_indicator[(i,k,st)] = state_gen
        m.state_indicator_gen = pyo.Param(m.node, m.generator, m.state, within=pyo.NonNegativeReals, initialize=state_indicator)   

        m.state_indicator_backup = pyo.Param(m.node, m.generator, m.state, within=pyo.NonNegativeReals, initialize=1)   
        m.state_indicator_line = pyo.Param(m.line, m.state, within=pyo.NonNegativeReals, initialize=1)
        
        unit_IC_backup = {}
        for k in m.generator:
            for t in m.year:
                unit_IC_backup[k,t] = 120
        m.unit_IC_backup = pyo.Param(m.generator, m.year, within=pyo.NonNegativeReals, initialize=unit_IC_backup) # unit: k$

        unit_FC_backup = {}
        for k in m.generator:
            for t in m.year:
                unit_FC_backup[k,t] = 12
        m.unit_FC_backup = pyo.Param(m.generator, m.year, within=pyo.NonNegativeReals, initialize=unit_FC_backup)  # unit: k$

        m.UD_penalty = pyo.Param(within=pyo.NonNegativeReals, initialize=9)
    
        ub_IC_backup = {}
        for k in m.generator:
            for t in m.year:
                ub_IC_backup[k,t] = m.max_ins_cap_backup[k] * m.unit_IC_backup[k,t]
        m.ub_IC_backup = pyo.Param(m.generator, m.year, within=pyo.NonNegativeReals, initialize=ub_IC_backup) 

        def _bounds_cap_ins_backup_rule(m, i, k, t):
            return (0, m.max_ins_cap_backup[k])          
        
        def _bounds_IC_backup_rule(m, i, k, t):
            return (0, m.ub_IC_backup[k,t]) 
        
        def _bounds_load_shedding_rule(m, i, t, n, b, st):
            return (0, m.load_demand[i,t,n,b])
        
        def _bounds_EENS_rule(m, i, t, n, b, st):
            return (0, m.load_demand[i,t,n,b])
        
        def _bounds_LOLE_rule(m, i, t, n, b, st):
            return (0, m.operation_time[b])    


        m.cap_bn = pyo.Var(m.node, m.generator, m.year, within=pyo.NonNegativeReals, bounds=_bounds_cap_ins_backup_rule, doc='Capacity of backup generators')
        m.cap_b = pyo.Var(m.node, m.generator, m.year, within=pyo.NonNegativeReals, doc='Capacity of backup generators available')
        m.ICB = pyo.Var(m.node, m.generator, m.year, bounds=_bounds_IC_backup_rule, within=pyo.NonNegativeReals, doc='Investment cost of backup generator')
        
        m.cap_sv = pyo.Var(m.node, m.generator, m.year, m.state, within=pyo.NonNegativeReals, doc='Generation capacity survived in state')
        m.cap_sv_b = pyo.Var(m.node, m.generator, m.year, m.state, within=pyo.NonNegativeReals, doc='Backup capacity survived in state')
        m.cap_sv_line = pyo.Var(m.line, m.year, m.state, within=pyo.NonNegativeReals, doc='Line capacity survived in state')
        m.ppd = pyo.Var(m.node, m.generator, m.year, m.rpdn, m.sub, m.state, within=pyo.NonNegativeReals, doc='Power produced from the main generator in state')
        m.ppd_b = pyo.Var(m.node, m.generator, m.year, m.rpdn, m.sub, m.state, within=pyo.NonNegativeReals, doc='Power produced from the backup in state')
        m.flow = pyo.Var(m.line, m.year, m.rpdn, m.sub, m.state, within=pyo.Reals, doc='Power flow in state')
        m.flow_pos = pyo.Var(m.line, m.year, m.rpdn, m.sub, m.state, within=pyo.NonNegativeReals, doc='Positive power flow in state')
        m.flow_neg = pyo.Var(m.line, m.year, m.rpdn, m.sub, m.state, within=pyo.NonPositiveReals, doc='Negative power flow in state')            
        m.ls = pyo.Var(m.node, m.year, m.rpdn, m.sub, m.state, within=pyo.NonNegativeReals, bounds=_bounds_load_shedding_rule, doc='Load shedding in state')
        m.over_gen = pyo.Var(m.node, m.year, m.rpdn, m.sub, m.state, within=pyo.NonNegativeReals, doc='Over-generation in state')
        
        m.LOLE = pyo.Var(m.node, m.year, m.rpdn, m.sub, m.state, within=pyo.NonNegativeReals, bounds=_bounds_LOLE_rule, doc='LOLE in state')
        m.EENS = pyo.Var(m.node, m.year, m.rpdn, m.sub, m.state, within=pyo.NonNegativeReals, bounds=_bounds_EENS_rule, doc='EENS in state')
        m.TLOLE = pyo.Var(m.node, m.year, m.rpdn, m.sub, within=pyo.NonNegativeReals, doc='Total LOLE')
        m.TEENS = pyo.Var(m.node, m.year, m.rpdn, m.sub, within=pyo.NonNegativeReals, doc='Total EENS')        


        ## Installation of generators
        @m.Disjunct(m.node, m.generator, m.year)
        def backup_install(disj, i, k, t):
            disj.install_cap_res1 = pyo.Constraint(expr= m.min_ins_cap_backup[k] <= m.cap_bn[i,k,t])
            disj.install_cap_res2 = pyo.Constraint(expr= m.cap_bn[i,k,t] <= m.max_ins_cap_backup[k])
            disj.invest_cost_res =  pyo.Constraint(expr= m.ICB[i,k,t] == m.unit_IC_backup[k,t] * m.cap_bn[i,k,t])
        
        @m.Disjunct(m.node, m.generator, m.year)
        def backup_install_no(outer, i, k, t):
            outer.invest_cost_res_no = pyo.Constraint(expr= m.cap_bn[i,k,t] == 0)
            outer.install_cap_res_no = pyo.Constraint(expr= m.ICB[i,k,t] == 0)
            
        @m.Disjunction(m.node, m.generator, m.year)
        def Ornot_backup_install(m, i, k, t):
            return [m.backup_install[i,k,t], m.backup_install_no[i,k,t]]    


        ## Available capacity of backup generators         
        @m.Constraint(m.node, m.generator, m.year)
        def availability_capacity_backup(m, i, k, t):
            return m.cap_b[i,k,t] == sum(m.cap_bn[i,k,tq] for tq in range(1,t+1))
        # m.availability_capacity_gen.pprint()
        
        
        ## Capacity between main and backup         
        @m.Constraint(m.node, m.generator, m.year)
        def main_backup_capacity(m, i, k, t):
            return m.cap_b[i,k,t] <= m.cap_ava[i,k,t]
        # m.availability_capacity_gen.pprint()        
        
    
        @m.Constraint(m.node, m.generator, m.year, m.state)
        def survived_main_capacity(m, i, k, t, st):
            return m.cap_sv[i,k,t,st] == m.state_indicator_gen[i,k,st] * m.cap_ava[i,k,t] 
        
        @m.Constraint(m.node, m.generator, m.year, m.state)
        def survived_backup_capacity(m, i, k, t, st):
            return m.cap_sv_b[i,k,t,st] == m.state_indicator_backup[i,k,st] * m.cap_b[i,k,t]        
        
        @m.Constraint(m.line, m.year, m.state)
        def survived_capacity_line(m, l, t, st):
            return m.cap_sv_line[l,t,st] == m.state_indicator_line[l,st] * m.cap_ava_line[l,t]        
        
        @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub, m.state)
        def power_generation_lb(m, i, k, t, n, b, st):
            return m.min_opt_dpt[k] * m.cap_sv[i,k,t,st] <= m.ppd[i,k,t,n,b,st]
        
        @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub, m.state)
        def power_generation_ub(m, i, k, t, n, b, st):
            return m.ppd[i,k,t,n,b,st] <= m.max_opt_dpt[k] * m.cap_sv[i,k,t,st]  

        @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub, m.state)
        def backup_power_generation_lb(m, i, k, t, n, b, st):
            return m.min_opt_dpt[k] * m.cap_sv_b[i,k,t,st] <= m.ppd_b[i,k,t,n,b,st]
        
        @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub, m.state)
        def backup_power_generation_ub(m, i, k, t, n, b, st):
            return m.ppd_b[i,k,t,n,b,st] <= m.max_opt_dpt[k] * m.cap_sv_b[i,k,t,st]  
        
        
        @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub, m.state)
        def ramp_up_constraint_prob(m, i, k, t, n, b, st):
            if b == 1:
                return m.ppd[i,k,t,n,b,st] <= m.ramp_up[k] * m.cap_sv[i,k,t,st]  
            else:
                return m.ppd[i,k,t,n,b,st] - m.ppd[i,k,t,n,b-1,st] <= m.ramp_up[k] * m.cap_sv[i,k,t,st] 

        @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub, m.state)
        def ramp_down_constraint_prob(m, i, k, t, n, b, st):
            if b == 1:
                return -m.ppd[i,k,t,n,b,st] <= m.ramp_down[k] * m.cap_sv[i,k,t,st] 
            else:
                return m.ppd[i,k,t,n,b-1,st] - m.ppd[i,k,t,n,b,st] <= m.ramp_down[k] * m.cap_sv[i,k,t,st]          

        @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub, m.state)
        def backup_ramp_up_constraint_prob(m, i, k, t, n, b, st):
            if b == 1:
                return m.ppd_b[i,k,t,n,b,st] <= m.ramp_up[k] * m.cap_sv_b[i,k,t,st]  
            else:
                return m.ppd_b[i,k,t,n,b,st] - m.ppd_b[i,k,t,n,b-1,st] <= m.ramp_up[k] * m.cap_sv_b[i,k,t,st] 

        @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub, m.state)
        def backup_ramp_down_constraint_prob(m, i, k, t, n, b, st):
            if b == 1:
                return -m.ppd_b[i,k,t,n,b,st] <= m.ramp_down[k] * m.cap_sv_b[i,k,t,st] 
            else:
                return m.ppd_b[i,k,t,n,b-1,st] - m.ppd_b[i,k,t,n,b,st] <= m.ramp_down[k] * m.cap_sv_b[i,k,t,st]   
            

        @m.Constraint(m.line, m.year, m.rpdn, m.sub, m.state)
        def flows_lb(m, l, t, n, b, st):
            return -m.cap_sv_line[l,t,st] <= m.flow[l,t,n,b,st]
        
        @m.Constraint(m.line, m.year, m.rpdn, m.sub, m.state)
        def flows_ub(m, l, t, n, b, st):
            return m.flow[l,t,n,b,st] <= m.cap_sv_line[l,t,st]     
        

        @m.Constraint(m.line, m.year, m.rpdn, m.sub, m.state)
        def flows_pos_neg(m, l, t, n, b, st):
            return m.flow[l,t,n,b,st] == m.flow_pos[l,t,n,b,st] + m.flow_neg[l,t,n,b,st]           
            
        
        @m.Constraint(m.node, m.year, m.rpdn, m.sub, m.state)
        def nodal_power_balance(m, i, t, n, b, st):
            return sum(m.ppd[i,k,t,n,b,st] for k in m.generator) + sum(m.ppd_b[i,k,t,n,b,st] for k in m.generator) + sum(m.flow[l,t,n,b,st] for l in m.line_to_node[i]) + m.ls[i,t,n,b,st] == \
                    m.load_demand[i,t,n,b] + sum(m.flow[l,t,n,b,st] for l in m.line_fr_node[i]) + m.over_gen[i,t,n,b,st]
        # m.nodel_power_balance.pprint()           
        
        
        ## LOLE and EENS evaluation
        @m.Disjunct(m.node, m.year, m.rpdn, m.sub, m.state)
        def load_shdding_yes(disj, i, t, n, b, st):
            disj.load_shedding_state = pyo.Constraint(expr= m.ls[i,t,n,b,st] >= 0.00002)
            disj.LOLE_state = pyo.Constraint(expr= m.LOLE[i,t,n,b,st] == m.operation_time[b])
            disj.EENS_state = pyo.Constraint(expr= m.EENS[i,t,n,b,st] == m.ls[i,t,n,b,st])
        # m.load_shdding_yes[1,1,1,1,1].pprint()

        @m.Disjunct(m.node, m.year, m.rpdn, m.sub, m.state)
        def load_shdding_no(disj, i, t, n, b, st):
            disj.load_shedding_state_no = pyo.Constraint(expr= m.ls[i,t,n,b,st] <= 0.00001)
            disj.LOLE_state_no = pyo.Constraint(expr= m.LOLE[i,t,n,b,st] == 0)
            disj.EENS_state_no = pyo.Constraint(expr= m.EENS[i,t,n,b,st] == 0)
        # m.load_shdding_no[1,1,1,1,1].pprint()
            
        @m.Disjunction(m.node, m.year, m.rpdn, m.sub, m.state)
        def Ornot_load_shedding(m, i, t, n, b, st):
            return [m.load_shdding_yes[i,t,n,b,st], m.load_shdding_no[i,t,n,b,st]]        
 
        @m.Constraint(m.node, m.year, m.rpdn, m.sub)
        def total_LOLE(m, i, t, n, b):
            return m.TLOLE[i,t,n,b] == sum(m.prob[st] * m.LOLE[i,t,n,b,st] for st in m.state)

        @m.Constraint(m.node, m.year, m.rpdn, m.sub)
        def total_EENS(m, i, t, n, b):
            return m.TEENS[i,t,n,b] == sum(m.prob[st] * m.EENS[i,t,n,b,st] for st in m.state)

        @m.Constraint(m.year)
        def LOLE_limit(m, t):
            return sum(m.weight_time[n] * m.TLOLE[i,t,n,b] for i in m.node for n in m.rpdn for b in m.sub) <= 2.4 


        
        @m.Expression()  # unit: M$
        def capital_expenditure(m):
            return sum(m.IC[i,k,t] for i in m.node for k in m.generator for t in m.year)/1000 + sum(m.ICB[i,k,t] for i in m.node for k in m.generator for t in m.year)/1000 +\
                + sum(m.ICL[l,t] for l in m.line for t in m.year)/1000 

        @m.Expression()
        def IC_generator(m):
            return sum(m.IC[i,k,t] for i in m.node for k in m.generator for t in m.year)/1000 
        
        @m.Expression()
        def IC_line(m):
            return sum(m.ICL[l,t] for l in m.line for t in m.year)/1000 

        @m.Expression()
        def IC_backup(m):
            return sum(m.ICB[i,k,t] for i in m.node for k in m.generator for t in m.year)/1000
        
        @m.Expression() 
        def operating_expenses(m):
            return sum(m.prob[st] * m.unit_FC[k,t] * m.cap_sv[i,k,t,st] for i in m.node for k in m.generator for t in m.year for st in m.state)/1000 + \
                sum(m.prob[st] * m.unit_FC_line[l,t] * m.cap_sv_line[l,t,st] for l in m.line for t in m.year for st in m.state)/1000 +\
                    sum(m.prob[st] * m.unit_FC_backup[k,t] * m.cap_sv_b[i,k,t,st] for i in m.node for k in m.generator for t in m.year for st in m.state)/1000 +\
                        sum(m.prob[st] * m.weight_time[n] * m.operation_time[b] * m.unit_VC[k,t] * (m.ppd[i,k,t,n,b,st] + m.ppd_b[i,k,t,n,b,st]) 
                            for i in m.node for k in m.generator for t in m.year for n in m.rpdn for b in m.sub for st in m.state)/1000000 +\
                                sum(m.prob[st] * m.weight_time[n] * m.operation_time[b] * m.unit_VC_line[l,t] * (m.flow_pos[l,t,n,b,st] - m.flow_neg[l,t,n,b,st])  
                                    for l in m.line for t in m.year for n in m.rpdn for b in m.sub for st in m.state)/1000000

        @m.Expression()
        def FOC_generator(m):
            return sum(m.prob[st] * m.unit_FC[k,t] * m.cap_sv[i,k,t,st] for i in m.node for k in m.generator for t in m.year for st in m.state)/1000 

        @m.Expression()
        def FOC_line(m):
            return sum(m.prob[st] * m.unit_FC_line[l,t] * m.cap_sv_line[l,t,st] for l in m.line for t in m.year for st in m.state)/1000

        @m.Expression()
        def FOC_backup(m):
            return sum(m.prob[st] * m.unit_FC_backup[k,t] * m.cap_sv_b[i,k,t,st] for i in m.node for k in m.generator for t in m.year for st in m.state)/1000
        
        
        @m.Expression()
        def VOC_generator_backup(m):
            return sum(m.prob[st] * m.weight_time[n] * m.operation_time[b] * m.unit_VC[k,t] * (m.ppd[i,k,t,n,b,st] + m.ppd_b[i,k,t,n,b,st]) 
                       for i in m.node for k in m.generator for t in m.year for n in m.rpdn for b in m.sub for st in m.state)/1000000 

        @m.Expression()
        def VOC_line(m):
            return sum(m.prob[st] * m.weight_time[n] * m.operation_time[b] * m.unit_VC_line[l,t] * (m.flow_pos[l,t,n,b,st] - m.flow_neg[l,t,n,b,st])  
                       for l in m.line for t in m.year for n in m.rpdn for b in m.sub for st in m.state)/1000000  
        
        @m.Expression()
        def OG_pen(m):
            return sum(m.prob[st] * m.weight_time[n] * m.operation_time[b] * m.OG_penalty * m.over_gen[i,t,n,b,st] 
                       for i in m.node for t in m.year for n in m.rpdn for b in m.sub for st in m.state)/1000                 

        @m.Expression() # unit: M$
        def EENS_penalties(m):
            return sum(m.weight_time[n] * m.operation_time[b] * m.UD_penalty * m.TEENS[i,t,n,b] for i in m.node for t in m.year for n in m.rpdn for b in m.sub)/1000     
                
        @m.Objective(sense=pyo.minimize)   # unit: M$
        def obj(m):
            return sum(m.IC[i,k,t] for i in m.node for k in m.generator for t in m.year)/1000 + \
                sum(m.ICB[i,k,t] for i in m.node for k in m.generator for t in m.year)/1000 + sum(m.ICL[l,t] for l in m.line for t in m.year)/1000 +\
                    sum(m.prob[st] * m.unit_FC[k,t] * m.cap_sv[i,k,t,st] for i in m.node for k in m.generator for t in m.year for st in m.state)/1000 + \
                        sum(m.prob[st] * m.unit_FC_line[l,t] * m.cap_sv_line[l,t,st] for l in m.line for t in m.year for st in m.state)/1000 +\
                            sum(m.prob[st] * m.unit_FC_backup[k,t] * m.cap_sv_b[i,k,t,st] for i in m.node for k in m.generator for t in m.year for st in m.state)/1000 +\
                                sum(m.prob[st] * m.weight_time[n] * m.operation_time[b] * m.unit_VC[k,t] * (m.ppd[i,k,t,n,b,st] + m.ppd_b[i,k,t,n,b,st]) 
                                    for i in m.node for k in m.generator for t in m.year for n in m.rpdn for b in m.sub for st in m.state)/1000000 +\
                                        sum(m.prob[st] * m.weight_time[n] * m.operation_time[b] * m.unit_VC_line[l,t] * (m.flow_pos[l,t,n,b,st] - m.flow_neg[l,t,n,b,st]) 
                                            for l in m.line for t in m.year for n in m.rpdn for b in m.sub for st in m.state)/1000000 +\
                                                sum(m.prob[st] * m.weight_time[n] * m.operation_time[b] * m.OG_penalty * m.over_gen[i,t,n,b,st] 
                                                    for i in m.node for t in m.year for n in m.rpdn for b in m.sub for st in m.state)/1000 +\
                                                        sum(m.weight_time[n] * m.operation_time[b] * m.UD_penalty * m.TEENS[i,t,n,b] for i in m.node for t in m.year for n in m.rpdn for b in m.sub)/1000   


    # No reliability design results   
    # m.cap_ins[1,'ng',1].fix(344.7)
    # m.cap_ins[1,'ng',2].fix(45.9)
    # m.cap_ins[1,'ng',3].fix(68.2)
    # m.cap_ins[2,'ng',1].fix(574.1)
    # m.cap_ins[2,'ng',2].fix(76.5)
    # m.cap_ins[2,'ng',3].fix(114.1)   
    # m.cap_ins[3,'ng',1].fix(0) 
    # m.cap_ins[3,'ng',2].fix(0) 
    # m.cap_ins[3,'ng',3].fix(0) 
    
    # for i in m.node:
    #     for k in m.generator:
    #         for t in m.year:
    #             m.cap_b[i,k,t].fix(0.0)
                
    # for l in m.line:
    #     for t in m.year:
    #         m.cap_ins_line[l,t].fix(0.0)


    # Reserve design results   
    # m.cap_ins[1,'ng',1].fix(418.0)
    # m.cap_ins[1,'ng',2].fix(55.6)
    # m.cap_ins[1,'ng',3].fix(82.7)
    # m.cap_ins[2,'ng',1].fix(696.1)
    # m.cap_ins[2,'ng',2].fix(92.7)
    # m.cap_ins[2,'ng',3].fix(138.4)   
    # m.cap_ins[3,'ng',1].fix(0) 
    # m.cap_ins[3,'ng',2].fix(0) 
    # m.cap_ins[3,'ng',3].fix(0) 
    
    # for i in m.node:
    #     for k in m.generator:
    #         for t in m.year:
    #             m.cap_b[i,k,t].fix(0.0)
                
    # for l in m.line:
    #     for t in m.year:
    #         m.cap_ins_line[l,t].fix(0.0)


    # N-1 design results   
    # m.cap_ins[1,'ng',1].fix(459.4)
    # m.cap_ins[1,'ng',2].fix(61.2)
    # m.cap_ins[1,'ng',3].fix(91.2)
    # m.cap_ins[2,'ng',1].fix(459.4)
    # m.cap_ins[2,'ng',2].fix(61.2)
    # m.cap_ins[2,'ng',3].fix(91.2)   
    # m.cap_ins[3,'ng',1].fix(459.4) 
    # m.cap_ins[3,'ng',2].fix(61.2) 
    # m.cap_ins[3,'ng',3].fix(91.2)
    
    # for i in m.node:
    #     for k in m.generator:
    #         for t in m.year:
    #             m.cap_b[i,k,t].fix(0.0)
        
    # m.cap_ins_line[1,1].fix(195.3)    
    # m.cap_ins_line[1,2].fix(26.0)    
    # m.cap_ins_line[1,3].fix(38.8)
    # m.cap_ins_line[2,1].fix(292.8)       
    # m.cap_ins_line[2,2].fix(39.0)   
    # m.cap_ins_line[2,3].fix(58.3)    
    # m.cap_ins_line[3,1].fix(97.8)       
    # m.cap_ins_line[3,2].fix(13.0)   
    # m.cap_ins_line[3,3].fix(19.3)
    
    
    # N-2 design results   
    # m.cap_ins[1,'ng',1].fix(918.8)
    # m.cap_ins[1,'ng',2].fix(122.4)
    # m.cap_ins[1,'ng',3].fix(182.4)
    # m.cap_ins[2,'ng',1].fix(918.8)
    # m.cap_ins[2,'ng',2].fix(122.4)
    # m.cap_ins[2,'ng',3].fix(182.4)   
    # m.cap_ins[3,'ng',1].fix(918.8) 
    # m.cap_ins[3,'ng',2].fix(122.4) 
    # m.cap_ins[3,'ng',3].fix(182.4)
    
    # for i in m.node:
    #     for k in m.generator:
    #         for t in m.year:
    #             m.cap_b[i,k,t].fix(0.0)
        
    # m.cap_ins_line[1,1].fix(97.5)    
    # m.cap_ins_line[1,2].fix(13.0)    
    # m.cap_ins_line[1,3].fix(19.5)
    # m.cap_ins_line[2,1].fix(390.5)       
    # m.cap_ins_line[2,2].fix(52.0)   
    # m.cap_ins_line[2,3].fix(77.5)    
    # m.cap_ins_line[3,1].fix(390.5)       
    # m.cap_ins_line[3,2].fix(52.0)   
    # m.cap_ins_line[3,3].fix(77.5)          


    transformation_string = 'gdp.' + transformation 
    pyo.TransformationFactory(transformation_string).apply_to(m)

       
    return m

if __name__ == "__main__":
    m = Reliability_model(transformation='bigm', formulation='no', datafolder='Illustrative')

    opt = pyo.SolverFactory('gurobi')
    opt.options['Threads'] = 8
    opt.options['MIPGap'] = 0.003
    opt.options['TimeLimit'] = 3600
    # opt.options['NonConvex'] = 2
    results = opt.solve(m, tee=True)
    # filename = os.path.join(os.path.dirname(__file__), 'model.lp')
    # RGTEP_CEC_model.write(filename, io_options={'symbolic_solver_labels':True})



    results = {}
    # tot_results = [m.ls, m.LOLE, m.EENS, m.TLOLE, m.TEENS]
    # tot_results = [m.cap_ins, m.cap_ins_line, m.cap_bn, m.cap_ava, m.cap_ava_line, m.cap_b, m.ppd, m.ppd_b, m.flow, m.over_gen]
    tot_results = [m.cap_ins, m.cap_ins_line, m.cap_ava, m.cap_ava_line, m.ppd, m.flow]
    
    
    for var_group in tot_results:
        for key in var_group:
            var_name = var_group[key].name
            if var_name not in results:
                results[var_name] = []
            results[var_name].append(round(var_group[key].value, 2))
        

    df_results = pd.DataFrame(results)
    df_results_transpose = df_results.transpose()
    df_results_transpose.to_excel("opt_results.xlsx")  
            
    # for t in m.year:
    #     print("LOLE every year", round(sum(m.weight_time[n] * m.TLOLE[i,t,n,b].value for i in m.node for n in m.rpdn for b in m.sub), 3),
    #           "EENS every year", round(sum(m.weight_time[n] * m.operation_time[b] * m.TEENS[i,t,n,b].value for i in m.node for n in m.rpdn for b in m.sub), 3),
    #           "Demand every year", round(sum(m.weight_time[n] * m.operation_time[b] * m.load_demand[i,t,n,b] for i in m.node for n in m.rpdn for b in m.sub), 3)  
    #     )
            
    # print("CAPEX", round(value(m.capital_expenditure()), 2), "| IC_Gen", round(value(m.IC_generator()), 2), "| IC_Line", round(value(m.IC_line()), 2), "| IC_backup", round(value(m.IC_backup()), 2),
    #       "| OPEX", round(value(m.operating_expenses()), 2), "| FC_Gen", round(value(m.FOC_generator()), 2), "| FC_Line", round(value(m.FOC_line()), 2), "| FC_backup", round(value(m.FOC_backup()), 2),
    #       "| VC_Gen", round(value(m.VOC_generator_backup()), 2), "| VC_Line", round(value(m.VOC_line()), 2),
    #       "| Over-gen penalty", round(value(m.OG_pen()), 2), "| Over generation", round(sum(m.over_gen[i,t,n,b,st].value for i in m.node for t in m.year for n in m.rpdn for b in m.sub for st in m.state), 2),
    #       "| EENS penalty", round(value(m.EENS_penalties()), 2)
    #       )

    for t in m.year:
        print("Demand every year", round(sum(m.weight_time[n] * m.operation_time[b] * m.load_demand[i,t,n,b] for i in m.node for n in m.rpdn for b in m.sub), 3)  
        )
    
    print("CAPEX", round(value(m.capital_expenditure()), 2), "| IC_Gen", round(value(m.IC_generator()), 2), "| IC_Line", round(value(m.IC_line()), 2), 
          "| OPEX", round(value(m.operating_expenses()), 2), "| FC_Gen", round(value(m.FOC_generator()), 2), "| FC_Line", round(value(m.FOC_line()), 2),
          "| VC_Gen", round(value(m.VOC_generator()), 2), "| VC_Line", round(value(m.VOC_line()), 2)
          )    



