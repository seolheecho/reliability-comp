__author__ = "Seolhee Cho"

import pyomo.environ as pyo
from pyomo.environ import value
from pyomo.gdp import Disjunction, Disjunct
import pandas as pd
from b_SD_data import read_data
import csv


def Reliability_model(data, transformation, formulation):
    
    m = pyo.ConcreteModel()
    
    # Sets   
    m.node = pyo.Set(initialize=data['node'])
    m.generator = pyo.Set(initialize=data['generator'])
    m.gen_pn = pyo.Set(within=m.generator, initialize=data['gen_pn'])
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
    m.min_opt_dpt = pyo.Param(m.generator, within=pyo.NonNegativeReals, initialize=data['min_opt_dpt'])
    m.max_opt_dpt = pyo.Param(m.generator, within=pyo.NonNegativeReals, initialize=data['max_opt_dpt'])
    m.ramp_up = pyo.Param(m.generator, within=pyo.NonNegativeReals, initialize=data['ramp_up'])
    m.ramp_down = pyo.Param(m.generator, within=pyo.NonNegativeReals, initialize=data['ramp_down'])
    m.pre_cap = pyo.Param(m.node, m.gen_ex, within=pyo.NonNegativeReals, initialize=data['pre_cap'])
    m.pre_cap_line = pyo.Param(m.line_ex, within=pyo.NonNegativeReals, initialize=data['pre_cap_line'])

    m.unit_IC = pyo.Param(m.gen_pn, m.year, within=pyo.NonNegativeReals, initialize=data['unit_IC']) # unit: M$/MW
    m.unit_IC_line = pyo.Param(m.line_pn, m.year, within=pyo.NonNegativeReals, initialize=data['unit_IC_line']) # unit: M$/MW 
    m.unit_FC = pyo.Param(m.generator, m.year, within=pyo.NonNegativeReals, initialize=data['unit_FC']) # unit: M$/MW 
    m.unit_FC_line = pyo.Param(m.line, m.year, within=pyo.NonNegativeReals, initialize=data['unit_FC_line']) # unit: M$/MW    
    m.unit_VC = pyo.Param(m.generator, m.year, within=pyo.NonNegativeReals, initialize=data['unit_VC'])   # unit: $/MWh  
    m.unit_VC_line = pyo.Param(m.line, m.year, within=pyo.NonNegativeReals, initialize=data['unit_VC_line'])   # unit: $/MWh
    m.OG_penalty = pyo.Param(within=pyo.NonNegativeReals, initialize=data['OG_penalty'])   # unit: $/MWh
    
   
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

    if formulation == 'no':    
        m.ppd = pyo.Var(m.node, m.generator, m.year, m.rpdn, m.sub, within=pyo.NonNegativeReals, doc='Power produced')
        m.flow = pyo.Var(m.line, m.year, m.rpdn, m.sub, within=pyo.NonNegativeReals, doc='Power flow')
        m.flow_pos = pyo.Var(m.line, m.year, m.rpdn, m.sub, within=pyo.NonNegativeReals, doc='Positive power flow')
        m.flow_neg = pyo.Var(m.line, m.year, m.rpdn, m.sub, within=pyo.NonPositiveReals, doc='Negative power flow') 
        
        @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub)
        def power_generation_lb(m, i, k, t, n, b):
            return m.min_opt_dpt[k] * m.cap_ava[i,k,t] <= m.ppd[i,k,t,n,b]
        
        @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub)
        def power_generation_ub(m, i, k, t, n, b):
            return m.ppd[i,k,t,n,b] <= m.max_opt_dpt[k] * m.cap_ava[i,k,t]  

        @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub)
        def ramp_up_constraint_rv(m, i, k, t, n, b):
            if b == 1:
                return m.ppd[i,k,t,n,b] <= m.ramp_up[k] * m.cap_ava[i,k,t]  
            else:
                return m.ppd[i,k,t,n,b] - m.ppd[i,k,t,n,b-1] <= m.ramp_up[k] * m.cap_ava[i,k,t]    

        @m.Constraint(m.node, m.generator, m.year, m.rpdn, m.sub)
        def ramp_down_constraint_rv(m, i, k, t, n, b):
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
            return sum(m.IC[i,k,t] for i in m.node for k in m.gen_pn for t in m.year) + sum(m.ICL[l,t] for l in m.line_pn for t in m.year)
        
        @m.Expression()
        def IC_generator(m):
            return sum(m.IC[i,k,t] for i in m.node for k in m.gen_pn for t in m.year)
        
        @m.Expression()
        def IC_line(m):
            return sum(m.ICL[l,t] for l in m.line_pn for t in m.year) 
        
        @m.Expression() # unit: M$
        def operating_expenses(m):
            return sum(m.unit_FC[k,t] * m.cap_ava[i,k,t] for i in m.node for k in m.generator for t in m.year) + \
                sum(m.unit_FC_line[l,t] * m.cap_ava_line[l,t] for l in m.line for t in m.year) +\
                    sum(m.weight_time[n] * m.operation_time[b] * m.unit_VC[k,t] * m.ppd[i,k,t,n,b] 
                        for i in m.node for k in m.generator for t in m.year for n in m.rpdn for b in m.sub)/1000000 +\
                        sum(m.weight_time[n] * m.operation_time[b] * m.unit_VC_line[l,t] * (m.flow_pos[l,t,n,b] - m.flow_neg[l,t,n,b])  
                            for l in m.line for t in m.year for n in m.rpdn for b in m.sub)/1000000

        @m.Expression() # unit: M$
        def FOC_generator(m):
            return sum(m.unit_FC[k,t] * m.cap_ava[i,k,t] for i in m.node for k in m.generator for t in m.year)

        @m.Expression() # unit: M$
        def FOC_line(m):
            return sum(m.unit_FC_line[l,t] * m.cap_ava_line[l,t] for l in m.line for t in m.year)
        
        @m.Expression() # unit: M$
        def VOC_generator(m):
            return sum(m.weight_time[n] * m.operation_time[b] * m.unit_VC[k,t] * m.ppd[i,k,t,n,b] 
                       for i in m.node for k in m.generator for t in m.year for n in m.rpdn for b in m.sub)/1000000 
        
        @m.Expression() # unit: M$
        def VOC_line(m):
            return sum(m.weight_time[n] * m.operation_time[b] * m.unit_VC_line[l,t] * (m.flow_pos[l,t,n,b] - m.flow_neg[l,t,n,b])  
                       for l in m.line for t in m.year for n in m.rpdn for b in m.sub)/1000000       

                
        @m.Objective(sense=pyo.minimize)   # unit: M$
        def obj(m):
            return sum(m.IC[i,k,t] for i in m.node for k in m.gen_pn for t in m.year) + sum(m.ICL[l,t] for l in m.line_pn for t in m.year) +\
                    sum(m.unit_FC[k,t] * m.cap_ava[i,k,t] for i in m.node for k in m.generator for t in m.year) + \
                        sum(m.unit_FC_line[l,t] * m.cap_ava_line[l,t] for l in m.line for t in m.year) +\
                            sum(m.weight_time[n] * m.operation_time[b] * m.unit_VC[k,t] * m.ppd[i,k,t,n,b] 
                                for i in m.node for k in m.generator for t in m.year for n in m.rpdn for b in m.sub)/1000000 +\
                                    sum(m.weight_time[n] * m.operation_time[b] * m.unit_VC_line[l,t] * (m.flow_pos[l,t,n,b] - m.flow_neg[l,t,n,b]) 
                                        for l in m.line for t in m.year for n in m.rpdn for b in m.sub)/1000000


    if formulation == 'reserve':    
        m.reserve_ratio = pyo.Param(within=pyo.NonNegativeReals, initialize=0.25)
        
        m.cap_opt = pyo.Var(m.node, m.generator, m.year, m.rpdn, m.sub, within=pyo.NonNegativeReals, doc='Operation capacity')
        m.cap_rev = pyo.Var(m.node, m.generator, m.year, m.rpdn, m.sub, within=pyo.NonNegativeReals, doc='Reserve capacity')
        m.ppd = pyo.Var(m.node, m.generator, m.year, m.rpdn, m.sub, within=pyo.NonNegativeReals, doc='Power produced')
        m.flow = pyo.Var(m.line, m.year, m.rpdn, m.sub, within=pyo.NonNegativeReals, doc='Power flow')
        m.flow_pos = pyo.Var(m.line, m.year, m.rpdn, m.sub, within=pyo.NonNegativeReals, doc='Positive power flow')
        m.flow_neg = pyo.Var(m.line, m.year, m.rpdn, m.sub, within=pyo.NonPositiveReals, doc='Negative power flow') 

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
            return sum(m.IC[i,k,t] for i in m.node for k in m.gen_pn for t in m.year) + sum(m.ICL[l,t] for l in m.line_pn for t in m.year)
        
        @m.Expression()
        def IC_generator(m):
            return sum(m.IC[i,k,t] for i in m.node for k in m.gen_pn for t in m.year)
        
        @m.Expression()
        def IC_line(m):
            return sum(m.ICL[l,t] for l in m.line_pn for t in m.year) 
        
        @m.Expression() # unit: M$
        def operating_expenses(m):
            return sum(m.unit_FC[k,t] * m.cap_ava[i,k,t] for i in m.node for k in m.generator for t in m.year) + \
                sum(m.unit_FC_line[l,t] * m.cap_ava_line[l,t] for l in m.line for t in m.year) +\
                    sum(m.weight_time[n] * m.operation_time[b] * m.unit_VC[k,t] * m.ppd[i,k,t,n,b] 
                        for i in m.node for k in m.generator for t in m.year for n in m.rpdn for b in m.sub)/1000000 +\
                        sum(m.weight_time[n] * m.operation_time[b] * m.unit_VC_line[l,t] * (m.flow_pos[l,t,n,b] - m.flow_neg[l,t,n,b])  
                            for l in m.line for t in m.year for n in m.rpdn for b in m.sub)/1000000

        @m.Expression() # unit: M$
        def FOC_generator(m):
            return sum(m.unit_FC[k,t] * m.cap_ava[i,k,t] for i in m.node for k in m.generator for t in m.year)

        @m.Expression() # unit: M$
        def FOC_line(m):
            return sum(m.unit_FC_line[l,t] * m.cap_ava_line[l,t] for l in m.line for t in m.year)
        
        @m.Expression() # unit: M$
        def VOC_generator(m):
            return sum(m.weight_time[n] * m.operation_time[b] * m.unit_VC[k,t] * m.ppd[i,k,t,n,b] 
                       for i in m.node for k in m.generator for t in m.year for n in m.rpdn for b in m.sub)/1000000 
        
        @m.Expression() # unit: M$
        def VOC_line(m):
            return sum(m.weight_time[n] * m.operation_time[b] * m.unit_VC_line[l,t] * (m.flow_pos[l,t,n,b] - m.flow_neg[l,t,n,b])  
                       for l in m.line for t in m.year for n in m.rpdn for b in m.sub)/1000000      

                
        @m.Objective(sense=pyo.minimize)   # unit: M$
        def obj(m):
            return sum(m.IC[i,k,t] for i in m.node for k in m.gen_pn for t in m.year) + sum(m.ICL[l,t] for l in m.line_pn for t in m.year) +\
                    sum(m.unit_FC[k,t] * m.cap_ava[i,k,t] for i in m.node for k in m.generator for t in m.year) + \
                        sum(m.unit_FC_line[l,t] * m.cap_ava_line[l,t] for l in m.line for t in m.year) +\
                            sum(m.weight_time[n] * m.operation_time[b] * m.unit_VC[k,t] * m.ppd[i,k,t,n,b] 
                                for i in m.node for k in m.generator for t in m.year for n in m.rpdn for b in m.sub)/1000000 +\
                                    sum(m.weight_time[n] * m.operation_time[b] * m.unit_VC_line[l,t] * (m.flow_pos[l,t,n,b] - m.flow_neg[l,t,n,b]) 
                                        for l in m.line for t in m.year for n in m.rpdn for b in m.sub)/1000000

    

    if formulation == 'n-k':
        m.scenario = pyo.Set(initialize=data['scenario'])   
        
        m.scenario_indicator_gen = pyo.Param(m.node, m.gen_pn, m.year, m.rpdn, m.scenario, within=pyo.NonNegativeReals, initialize=data['scenario_indicator_gen'])
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
       
       
        # Potential generators
        @m.Constraint(m.node, m.gen_pn, m.year, m.rpdn, m.scenario)
        def survived_capacity_pn(m, i, k, t, n, sc):
            return m.cap_sv[i,k,t,n,sc] == m.scenario_indicator_gen[i,k,t,n,sc] * m.cap_ava[i,k,t]

        @m.Constraint(m.node, m.gen_pn, m.year, m.rpdn, m.sub, m.scenario)
        def power_generation_lb_pn(m, i, k, t, n, b, sc):
            return m.min_opt_dpt[k] * m.cap_sv[i,k,t,n,sc] <= m.ppd[i,k,t,n,b,sc]
        
        @m.Constraint(m.node, m.gen_pn, m.year, m.rpdn, m.sub, m.scenario)
        def power_generation_ub_pn(m, i, k, t, n, b, sc):
            return m.ppd[i,k,t,n,b,sc] <= m.max_opt_dpt[k] * m.cap_sv[i,k,t,n,sc]  

        @m.Constraint(m.node, m.gen_pn, m.year, m.rpdn, m.sub, m.scenario)
        def ramp_up_constraint_pn(m, i, k, t, n, b, sc):
            if b == 1:
                return m.ppd[i,k,t,n,b,sc] <= m.ramp_up[k] * m.cap_sv[i,k,t,n,sc]  
            else:
                return m.ppd[i,k,t,n,b,sc] - m.ppd[i,k,t,n,b-1,sc] <= m.ramp_up[k] * m.cap_sv[i,k,t,n,sc]    

        @m.Constraint(m.node, m.gen_pn, m.year, m.rpdn, m.sub, m.scenario)
        def ramp_down_constraint_pn(m, i, k, t, n, b, sc):
            if b == 1:
                return -m.ppd[i,k,t,n,b,sc] <= m.ramp_down[k] * m.cap_sv[i,k,t,n,sc] 
            else:
                return m.ppd[i,k,t,n,b-1,sc] - m.ppd[i,k,t,n,b,sc] <= m.ramp_down[k] * m.cap_sv[i,k,t,n,sc]         
        
        @m.Constraint(m.node, m.gen_pn, m.year, m.scenario)
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
            return sum(m.ppd[i,k,t,n,b,sc] for k in m.generator) + sum(m.flow[l,t,n,b,sc] for l in m.line_to_node[i]) >= \
                    m.load_demand[i,t,n,b] + sum(m.flow[l,t,n,b,sc] for l in m.line_fr_node[i])         
                            
        
        
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
    
    
    
    if formulation == 'prob':
        m.state = pyo.Set(initialize=data['state']) 
        
        m.min_ins_cap_backup = pyo.Param(m.gen_pn, within=pyo.NonNegativeReals, initialize=data['min_ins_cap_backup'])
        m.max_ins_cap_backup = pyo.Param(m.gen_pn, within=pyo.NonNegativeReals, initialize=data['max_ins_cap_backup'])

        m.unit_IC_backup = pyo.Param(m.gen_pn, m.year, within=pyo.NonNegativeReals, initialize=data['unit_IC_backup']) # unit: M$/MW
        m.unit_FC_backup = pyo.Param(m.gen_pn, m.year, within=pyo.NonNegativeReals, initialize=data['unit_FC_backup']) # unit: M$/MW 

        m.prob = pyo.Param(m.state, within=pyo.NonNegativeReals, initialize=data['prob'])
        m.state_indicator_gen = pyo.Param(m.node, m.gen_pn, m.state, within=pyo.NonNegativeReals, initialize=data['state_indicator_gen'])   
        m.state_indicator_line = pyo.Param(m.line, m.state, within=pyo.NonNegativeReals, initialize=data['state_indicator_line'])
        m.state_indicator_backup = pyo.Param(m.node, m.gen_pn, m.state, within=pyo.NonNegativeReals, initialize=data['state_indicator_backup'])   

        m.UD_penalty = pyo.Param(within=pyo.NonNegativeReals, initialize=data['UD_penalty'])

        # Bounds
        m.ub_IC_backup = pyo.Param(m.gen_pn, m.year, within=pyo.NonNegativeReals, initialize=data['ub_IC_backup'])

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

        m.cap_bn = pyo.Var(m.node, m.gen_pn, m.year, within=pyo.NonNegativeReals, bounds=_bounds_cap_ins_backup_rule, doc='Capacity of backup generators')
        m.cap_b = pyo.Var(m.node, m.gen_pn, m.year, within=pyo.NonNegativeReals, doc='Capacity of backup generators available')
        m.ICB = pyo.Var(m.node, m.gen_pn, m.year, bounds=_bounds_IC_backup_rule, within=pyo.NonNegativeReals, doc='Investment cost of backup generator')

        m.cap_sv = pyo.Var(m.node, m.generator, m.year, m.state, within=pyo.NonNegativeReals, doc='Generation capacity survived in state')
        m.cap_sv_b = pyo.Var(m.node, m.gen_pn, m.year, m.state, within=pyo.NonNegativeReals, doc='Backup capacity survived in state')
        m.cap_sv_line = pyo.Var(m.line, m.year, m.state, within=pyo.NonNegativeReals, doc='Line capacity survived in state')
        m.ppd = pyo.Var(m.node, m.generator, m.year, m.rpdn, m.sub, m.state, within=pyo.NonNegativeReals, doc='Power produced from the main generator in state')
        m.ppd_b = pyo.Var(m.node, m.gen_pn, m.year, m.rpdn, m.sub, m.state, within=pyo.NonNegativeReals, doc='Power produced from the backup in state')
        m.flow = pyo.Var(m.line, m.year, m.rpdn, m.sub, m.state, within=pyo.Reals, doc='Power flow in state')
        m.flow_pos = pyo.Var(m.line, m.year, m.rpdn, m.sub, m.state, within=pyo.NonNegativeReals, doc='Positive power flow in state')
        m.flow_neg = pyo.Var(m.line, m.year, m.rpdn, m.sub, m.state, within=pyo.NonPositiveReals, doc='Negative power flow in state')            
        m.ls = pyo.Var(m.node, m.year, m.rpdn, m.sub, m.state, within=pyo.NonNegativeReals, bounds=_bounds_load_shedding_rule, doc='Load shedding in state')
        m.over_gen = pyo.Var(m.node, m.year, m.rpdn, m.sub, m.state, within=pyo.NonNegativeReals, doc='Over-generation in state')
        
        m.LOLE = pyo.Var(m.node, m.year, m.rpdn, m.sub, m.state, within=pyo.NonNegativeReals, bounds=_bounds_LOLE_rule, doc='LOLE in state')
        m.EENS = pyo.Var(m.node, m.year, m.rpdn, m.sub, m.state, within=pyo.NonNegativeReals, bounds=_bounds_EENS_rule, doc='EENS in state')
        m.TLOLE = pyo.Var(m.node, m.year, m.rpdn, m.sub, within=pyo.NonNegativeReals, doc='Total LOLE')
        m.TEENS = pyo.Var(m.node, m.year, m.rpdn, m.sub, within=pyo.NonNegativeReals, doc='Total EENS')        
    
                
    
        ## Installation of backup generators
        @m.Disjunct(m.node, m.gen_pn, m.year)
        def backup_install(disj, i, k, t):
            disj.install_cap_bk1 = pyo.Constraint(expr= m.min_ins_cap_backup[k] <= m.cap_bn[i,k,t])
            disj.install_cap_bk2 = pyo.Constraint(expr= m.cap_bn[i,k,t] <= m.max_ins_cap_backup[k])
            disj.invest_cost_bk =  pyo.Constraint(expr= m.ICB[i,k,t] == m.unit_IC_backup[k,t] * m.cap_bn[i,k,t])
        
        @m.Disjunct(m.node, m.gen_pn, m.year)
        def backup_install_no(outer, i, k, t):
            outer.invest_cost_bk_no = pyo.Constraint(expr= m.cap_bn[i,k,t] == 0)
            outer.install_cap_bk_no = pyo.Constraint(expr= m.ICB[i,k,t] == 0)
            
        @m.Disjunction(m.node, m.gen_pn, m.year)
        def Ornot_backup_install(m, i, k, t):
            return [m.backup_install[i,k,t], m.backup_install_no[i,k,t]]    


        ## Available capacity of backup generators         
        @m.Constraint(m.node, m.gen_pn, m.year)
        def availability_capacity_backup(m, i, k, t):
            return m.cap_b[i,k,t] == sum(m.cap_bn[i,k,tq] for tq in range(1,t+1))
        # m.availability_capacity_gen.pprint()
        
        
        ## Capacity between main and backup         
        @m.Constraint(m.node, m.gen_pn, m.year)
        def main_backup_capacity(m, i, k, t):
            return m.cap_b[i,k,t] <= m.cap_ava[i,k,t]
        # m.availability_capacity_gen.pprint()        
        
    
        @m.Constraint(m.node, m.gen_pn, m.year, m.state)
        def survived_main_capacity_pn(m, i, k, t, st):
            return m.cap_sv[i,k,t,st] == m.state_indicator_gen[i,k,st] * m.cap_ava[i,k,t] 
        
        @m.Constraint(m.node, m.gen_ex, m.year, m.state)
        def survived_main_capacity_ex(m, i, k, t, st):
            return m.cap_sv[i,k,t,st] == m.cap_ava[i,k,t]         
        
        
        @m.Constraint(m.node, m.gen_pn, m.year, m.state)
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


        @m.Constraint(m.node, m.gen_pn, m.year, m.rpdn, m.sub, m.state)
        def backup_power_generation_lb(m, i, k, t, n, b, st):
            return m.min_opt_dpt[k] * m.cap_sv_b[i,k,t,st] <= m.ppd_b[i,k,t,n,b,st]
        
        @m.Constraint(m.node, m.gen_pn, m.year, m.rpdn, m.sub, m.state)
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



        @m.Constraint(m.node, m.gen_pn, m.year, m.rpdn, m.sub, m.state)
        def backup_ramp_up_constraint_prob(m, i, k, t, n, b, st):
            if b == 1:
                return m.ppd_b[i,k,t,n,b,st] <= m.ramp_up[k] * m.cap_sv_b[i,k,t,st]  
            else:
                return m.ppd_b[i,k,t,n,b,st] - m.ppd_b[i,k,t,n,b-1,st] <= m.ramp_up[k] * m.cap_sv_b[i,k,t,st] 

        @m.Constraint(m.node, m.gen_pn, m.year, m.rpdn, m.sub, m.state)
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
            return sum(m.ppd[i,k,t,n,b,st] for k in m.generator) + sum(m.ppd_b[i,k,t,n,b,st] for k in m.gen_pn) + sum(m.flow[l,t,n,b,st] for l in m.line_to_node[i]) + m.ls[i,t,n,b,st] == \
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
            return sum(m.IC[i,k,t] for i in m.node for k in m.gen_pn for t in m.year) + sum(m.ICB[i,k,t] for i in m.node for k in m.gen_pn for t in m.year) +\
                + sum(m.ICL[l,t] for l in m.line_pn for t in m.year)

        @m.Expression()
        def IC_generator(m):
            return sum(m.IC[i,k,t] for i in m.node for k in m.gen_pn for t in m.year)
        
        @m.Expression()
        def IC_line(m):
            return sum(m.ICL[l,t] for l in m.line_pn for t in m.year)

        @m.Expression()
        def IC_backup(m):
            return sum(m.ICB[i,k,t] for i in m.node for k in m.gen_pn for t in m.year)
        
        @m.Expression() 
        def operating_expenses(m):
            return sum(m.prob[st] * m.unit_FC[k,t] * m.cap_sv[i,k,t,st] for i in m.node for k in m.generator for t in m.year for st in m.state) + \
                sum(m.prob[st] * m.unit_FC_line[l,t] * m.cap_sv_line[l,t,st] for l in m.line for t in m.year for st in m.state) +\
                    sum(m.prob[st] * m.unit_FC_backup[k,t] * m.cap_sv_b[i,k,t,st] for i in m.node for k in m.gen_pn for t in m.year for st in m.state) +\
                        sum(m.prob[st] * m.weight_time[n] * m.operation_time[b] * m.unit_VC[k,t] * m.ppd[i,k,t,n,b,st] 
                            for i in m.node for k in m.generator for t in m.year for n in m.rpdn for b in m.sub for st in m.state)/1000000 +\
                                sum(m.prob[st] * m.weight_time[n] * m.operation_time[b] * m.unit_VC[k,t] * m.ppd_b[i,k,t,n,b,st]
                                    for i in m.node for k in m.gen_pn for t in m.year for n in m.rpdn for b in m.sub for st in m.state)/1000000 +\
                                        sum(m.prob[st] * m.weight_time[n] * m.operation_time[b] * m.unit_VC_line[l,t] * (m.flow_pos[l,t,n,b,st] - m.flow_neg[l,t,n,b,st])  
                                            for l in m.line for t in m.year for n in m.rpdn for b in m.sub for st in m.state)/1000000

        @m.Expression()
        def FOC_generator(m):
            return sum(m.prob[st] * m.unit_FC[k,t] * m.cap_sv[i,k,t,st] for i in m.node for k in m.generator for t in m.year for st in m.state) 

        @m.Expression()
        def FOC_line(m):
            return sum(m.prob[st] * m.unit_FC_line[l,t] * m.cap_sv_line[l,t,st] for l in m.line for t in m.year for st in m.state)

        @m.Expression()
        def FOC_backup(m):
            return sum(m.prob[st] * m.unit_FC_backup[k,t] * m.cap_sv_b[i,k,t,st] for i in m.node for k in m.gen_pn for t in m.year for st in m.state)
        
        
        @m.Expression()
        def VOC_generator(m):
            return sum(m.prob[st] * m.weight_time[n] * m.operation_time[b] * m.unit_VC[k,t] * m.ppd[i,k,t,n,b,st] 
                       for i in m.node for k in m.generator for t in m.year for n in m.rpdn for b in m.sub for st in m.state)/1000000 

        @m.Expression()
        def VOC_backup(m):
            return sum(m.prob[st] * m.weight_time[n] * m.operation_time[b] * m.unit_VC[k,t] * m.ppd_b[i,k,t,n,b,st]
                       for i in m.node for k in m.gen_pn for t in m.year for n in m.rpdn for b in m.sub for st in m.state)/1000000 

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
            return sum(m.IC[i,k,t] for i in m.node for k in m.gen_pn for t in m.year) + \
                sum(m.ICB[i,k,t] for i in m.node for k in m.gen_pn for t in m.year) + sum(m.ICL[l,t] for l in m.line_pn for t in m.year) +\
                    sum(m.prob[st] * m.unit_FC[k,t] * m.cap_sv[i,k,t,st] for i in m.node for k in m.generator for t in m.year for st in m.state) + \
                        sum(m.prob[st] * m.unit_FC_line[l,t] * m.cap_sv_line[l,t,st] for l in m.line for t in m.year for st in m.state) +\
                            sum(m.prob[st] * m.unit_FC_backup[k,t] * m.cap_sv_b[i,k,t,st] for i in m.node for k in m.gen_pn for t in m.year for st in m.state) +\
                                sum(m.prob[st] * m.weight_time[n] * m.operation_time[b] * m.unit_VC[k,t] * m.ppd[i,k,t,n,b,st] 
                                    for i in m.node for k in m.generator for t in m.year for n in m.rpdn for b in m.sub for st in m.state)/1000000 +\
                                        sum(m.prob[st] * m.weight_time[n] * m.operation_time[b] * m.unit_VC[k,t] * m.ppd_b[i,k,t,n,b,st]
                                            for i in m.node for k in m.gen_pn for t in m.year for n in m.rpdn for b in m.sub for st in m.state)/1000000 +\
                                                sum(m.prob[st] * m.weight_time[n] * m.operation_time[b] * m.unit_VC_line[l,t] * (m.flow_pos[l,t,n,b,st] - m.flow_neg[l,t,n,b,st]) 
                                                    for l in m.line for t in m.year for n in m.rpdn for b in m.sub for st in m.state)/1000000 +\
                                                        sum(m.prob[st] * m.weight_time[n] * m.operation_time[b] * m.OG_penalty * m.over_gen[i,t,n,b,st] 
                                                            for i in m.node for t in m.year for n in m.rpdn for b in m.sub for st in m.state)/1000 +\
                                                                sum(m.weight_time[n] * m.operation_time[b] * m.UD_penalty * m.TEENS[i,t,n,b] for i in m.node for t in m.year for n in m.rpdn for b in m.sub)/1000     


    # No reliability design results 
    # m.cap_ins[1,'ng-p',1].fix(24.9)
    # m.cap_ins[1,'ng-p',2].fix(57.5)
    # m.cap_ins[1,'ng-p',3].fix(60.0)
    # m.cap_ins[1,'ng-p',4].fix(62.8)
    # m.cap_ins[1,'ng-p',5].fix(65.9)       
    # m.cap_ins[2,'ng-p',1].fix(0.0)
    # m.cap_ins[2,'ng-p',2].fix(0.0)
    # m.cap_ins[2,'ng-p',3].fix(0.0)
    # m.cap_ins[2,'ng-p',4].fix(0.0)
    # m.cap_ins[2,'ng-p',5].fix(0.0)    
    # m.cap_ins[3,'ng-p',1].fix(0.0)
    # m.cap_ins[3,'ng-p',2].fix(0.0)
    # m.cap_ins[3,'ng-p',3].fix(0.0)
    # m.cap_ins[3,'ng-p',4].fix(0.0)
    # m.cap_ins[3,'ng-p',5].fix(0.0)   
    # m.cap_ins[4,'ng-p',1].fix(681.4)
    # m.cap_ins[4,'ng-p',2].fix(86.1)
    # m.cap_ins[4,'ng-p',3].fix(90.2)
    # m.cap_ins[4,'ng-p',4].fix(94.2)
    # m.cap_ins[4,'ng-p',5].fix(98.8)   

    # for i in m.node:
    #     for k in m.gen_pn:
    #         for t in m.year:
    #             m.cap_b[i,k,t].fix(0.0)

    # m.cap_ins_line[2,1].fix(0.0)                   
    # m.cap_ins_line[2,2].fix(0.0)   
    # m.cap_ins_line[2,3].fix(0.0)   
    # m.cap_ins_line[2,4].fix(0.0)   
    # m.cap_ins_line[2,5].fix(0.0)   
    # m.cap_ins_line[3,1].fix(0.0)                   
    # m.cap_ins_line[3,2].fix(0.0)   
    # m.cap_ins_line[3,3].fix(0.0)   
    # m.cap_ins_line[3,4].fix(0.0)   
    # m.cap_ins_line[3,5].fix(0.0)   
    # m.cap_ins_line[4,1].fix(0.0)                   
    # m.cap_ins_line[4,2].fix(0.0)   
    # m.cap_ins_line[4,3].fix(0.0)   
    # m.cap_ins_line[4,4].fix(0.0)   
    # m.cap_ins_line[4,5].fix(0.0)   
    # m.cap_ins_line[5,1].fix(0.0)                   
    # m.cap_ins_line[5,2].fix(0.0)   
    # m.cap_ins_line[5,3].fix(0.0)   
    # m.cap_ins_line[5,4].fix(0.0)   
    # m.cap_ins_line[5,5].fix(0.0)   


    # Reserve design results   
    # m.cap_ins[1,'ng-p',1].fix(481.77)
    # m.cap_ins[1,'ng-p',2].fix(0.0)
    # m.cap_ins[1,'ng-p',3].fix(0.0)
    # m.cap_ins[1,'ng-p',4].fix(0.0)
    # m.cap_ins[1,'ng-p',5].fix(0.0)    
    # m.cap_ins[2,'ng-p',1].fix(0.0)
    # m.cap_ins[2,'ng-p',2].fix(0.0)
    # m.cap_ins[2,'ng-p',3].fix(0.0)
    # m.cap_ins[2,'ng-p',4].fix(0.0)
    # m.cap_ins[2,'ng-p',5].fix(0.0)    
    # m.cap_ins[3,'ng-p',1].fix(0.0)
    # m.cap_ins[3,'ng-p',2].fix(0.0)
    # m.cap_ins[3,'ng-p',3].fix(0.0)
    # m.cap_ins[3,'ng-p',4].fix(0.0)
    # m.cap_ins[3,'ng-p',5].fix(0.0)   
    # m.cap_ins[4,'ng-p',1].fix(643.34)
    # m.cap_ins[4,'ng-p',2].fix(723.39)
    # m.cap_ins[4,'ng-p',3].fix(0.0)
    # m.cap_ins[4,'ng-p',4].fix(0.0)
    # m.cap_ins[4,'ng-p',5].fix(0.0)    

    # for i in m.node:
    #     for k in m.gen_pn:
    #         for t in m.year:
    #             m.cap_b[i,k,t].fix(0.0)

    # m.cap_ins_line[2,1].fix(0.0)                   
    # m.cap_ins_line[2,2].fix(0.0)   
    # m.cap_ins_line[2,3].fix(0.0)   
    # m.cap_ins_line[2,4].fix(0.0)   
    # m.cap_ins_line[2,5].fix(0.0)   
    # m.cap_ins_line[3,1].fix(0.0)                   
    # m.cap_ins_line[3,2].fix(0.0)   
    # m.cap_ins_line[3,3].fix(0.0)   
    # m.cap_ins_line[3,4].fix(0.0)   
    # m.cap_ins_line[3,5].fix(0.0)   
    # m.cap_ins_line[4,1].fix(0.0)                   
    # m.cap_ins_line[4,2].fix(0.0)   
    # m.cap_ins_line[4,3].fix(0.0)   
    # m.cap_ins_line[4,4].fix(0.0)   
    # m.cap_ins_line[4,5].fix(0.0)   
    # m.cap_ins_line[5,1].fix(0.0)                   
    # m.cap_ins_line[5,2].fix(0.0)   
    # m.cap_ins_line[5,3].fix(0.0)   
    # m.cap_ins_line[5,4].fix(0.0)   
    # m.cap_ins_line[5,5].fix(0.0)   


    # N-1 reliability design results   
    # m.cap_ins[1,'ng-p',1].fix(235.5)
    # m.cap_ins[1,'ng-p',2].fix(47.9)
    # m.cap_ins[1,'ng-p',3].fix(50.1)
    # m.cap_ins[1,'ng-p',4].fix(52.4)
    # m.cap_ins[1,'ng-p',5].fix(54.9)   
    # m.cap_ins[2,'ng-p',1].fix(235.5)
    # m.cap_ins[2,'ng-p',2].fix(47.9)
    # m.cap_ins[2,'ng-p',3].fix(50.1)
    # m.cap_ins[2,'ng-p',4].fix(52.4)
    # m.cap_ins[2,'ng-p',5].fix(54.9)    
    # m.cap_ins[3,'ng-p',1].fix(235.5)
    # m.cap_ins[3,'ng-p',2].fix(47.9)
    # m.cap_ins[3,'ng-p',3].fix(50.1)
    # m.cap_ins[3,'ng-p',4].fix(52.4)
    # m.cap_ins[3,'ng-p',5].fix(54.9)   
    # m.cap_ins[4,'ng-p',1].fix(235.5)
    # m.cap_ins[4,'ng-p',2].fix(47.9)
    # m.cap_ins[4,'ng-p',3].fix(50.1)
    # m.cap_ins[4,'ng-p',4].fix(52.4)
    # m.cap_ins[4,'ng-p',5].fix(54.9) 

    # for i in m.node:
    #     for k in m.gen_pn:
    #         for t in m.year:
    #             m.cap_b[i,k,t].fix(0.0)

    # m.cap_ins_line[2,1].fix(155.9)                   
    # m.cap_ins_line[2,2].fix(0.0)   
    # m.cap_ins_line[2,3].fix(0.0)   
    # m.cap_ins_line[2,4].fix(0.0)   
    # m.cap_ins_line[2,5].fix(0.0)   
    # m.cap_ins_line[3,1].fix(0.0)                   
    # m.cap_ins_line[3,2].fix(0.0)   
    # m.cap_ins_line[3,3].fix(0.0)   
    # m.cap_ins_line[3,4].fix(0.0)   
    # m.cap_ins_line[3,5].fix(0.0)   
    # m.cap_ins_line[4,1].fix(79.1)                   
    # m.cap_ins_line[4,2].fix(32.5)   
    # m.cap_ins_line[4,3].fix(34.1)   
    # m.cap_ins_line[4,4].fix(35.6)   
    # m.cap_ins_line[4,5].fix(37.3)   
    # m.cap_ins_line[5,1].fix(200.1)                   
    # m.cap_ins_line[5,2].fix(40.7)   
    # m.cap_ins_line[5,3].fix(42.6)   
    # m.cap_ins_line[5,4].fix(44.5)   
    # m.cap_ins_line[5,5].fix(46.7)   
    
    # N-2 reliability design results   
    m.cap_ins[1,'ng-p',1].fix(353.2)
    m.cap_ins[1,'ng-p',2].fix(71.8)
    m.cap_ins[1,'ng-p',3].fix(75.1)
    m.cap_ins[1,'ng-p',4].fix(78.5)
    m.cap_ins[1,'ng-p',5].fix(82.4)    
    m.cap_ins[2,'ng-p',1].fix(353.2)
    m.cap_ins[2,'ng-p',2].fix(71.8)
    m.cap_ins[2,'ng-p',3].fix(75.1)
    m.cap_ins[2,'ng-p',4].fix(78.5)
    m.cap_ins[2,'ng-p',5].fix(82.4)    
    m.cap_ins[3,'ng-p',1].fix(353.2)
    m.cap_ins[3,'ng-p',2].fix(71.8)
    m.cap_ins[3,'ng-p',3].fix(75.1)
    m.cap_ins[3,'ng-p',4].fix(78.5)
    m.cap_ins[3,'ng-p',5].fix(82.4)   
    m.cap_ins[4,'ng-p',1].fix(353.2)
    m.cap_ins[4,'ng-p',2].fix(71.8)
    m.cap_ins[4,'ng-p',3].fix(75.1)
    m.cap_ins[4,'ng-p',4].fix(78.5)
    m.cap_ins[4,'ng-p',5].fix(82.4)   

    for i in m.node:
        for k in m.gen_pn:
            for t in m.year:
                m.cap_b[i,k,t].fix(0.0)

    m.cap_ins_line[2,1].fix(140.6)                   
    m.cap_ins_line[2,2].fix(48.9)   
    m.cap_ins_line[2,3].fix(23.1)   
    m.cap_ins_line[2,4].fix(50.7)   
    m.cap_ins_line[2,5].fix(17.7)   
    m.cap_ins_line[3,1].fix(119.6)                   
    m.cap_ins_line[3,2].fix(61.1)   
    m.cap_ins_line[3,3].fix(35.9)   
    m.cap_ins_line[3,4].fix(29.4)   
    m.cap_ins_line[3,5].fix(66.4)   
    m.cap_ins_line[4,1].fix(159.6)                   
    m.cap_ins_line[4,2].fix(12.2)   
    m.cap_ins_line[4,3].fix(40.8)   
    m.cap_ins_line[4,4].fix(50.7)   
    m.cap_ins_line[4,5].fix(17.7)   
    m.cap_ins_line[5,1].fix(180.6)                   
    m.cap_ins_line[5,2].fix(0.0)   
    m.cap_ins_line[5,3].fix(35.9)   
    m.cap_ins_line[5,4].fix(29.4)   
    m.cap_ins_line[5,5].fix(66.4)       

    transformation_string = 'gdp.' + transformation 
    pyo.TransformationFactory(transformation_string).apply_to(m)

       
    return m

if __name__ == "__main__":
    d = read_data(datafolder="San Diego", example='dual-yes')
    m = Reliability_model(d, transformation='bigm', formulation='prob')

    opt = pyo.SolverFactory('gurobi')

    # Set up Gurobi's log file
    log_file = "gurobi_log.txt"
    opt.options['logfile'] = log_file
    
    # Scaling options / numbers of threads, optimality gap, and solution time
    opt.options['Threads'] = 8
    opt.options['MIPGap'] = 0.01
    opt.options['TimeLimit'] = 10800   # 3 hours 
    
    # Solve the optimization model
    results = opt.solve(m, tee=True)
    # filename = os.path.join(os.path.dirname(__file__), 'model.lp')
    # RGTEP_CEC_model.write(filename, io_options={'symbolic_solver_labels':True})    
    
    
    # Read the log file and write its contents to a .csv file
    csv_file = "gurobi_log.csv"
    with open(log_file, "r") as infile, open(csv_file, "w", newline="") as outfile:
        writer = csv.writer(outfile)
        for line in infile:
            writer.writerow([line.strip()])


    results = {}
    tot_results = [m.cap_ins, m.cap_ins_line, m.cap_bn, m.cap_ava, m.cap_ava_line, m.cap_b]
    # tot_results = [m.cap_ins, m.cap_ins_line, m.cap_ava, m.cap_ava_line]
    
    
    for var_group in tot_results:
        for key in var_group:
            var_name = var_group[key].name
            if var_name not in results:
                results[var_name] = []
            results[var_name].append(round(var_group[key].value, 2))
        

    df_results = pd.DataFrame(results)
    df_results_transpose = df_results.transpose()
    df_results_transpose.to_excel("opt_results.xlsx")  

    for t in m.year:
        print("LOLE every year", round(sum(m.weight_time[n] * m.TLOLE[i,t,n,b].value for i in m.node for n in m.rpdn for b in m.sub), 3),
              "EENS every year", round(sum(m.weight_time[n] * m.operation_time[b] * m.TEENS[i,t,n,b].value for i in m.node for n in m.rpdn for b in m.sub), 3),
              "Demand every year", round(sum(m.weight_time[n] * m.operation_time[b] * m.load_demand[i,t,n,b] for i in m.node for n in m.rpdn for b in m.sub), 3)  
        )
            
    print("CAPEX", round(value(m.capital_expenditure()), 2), "| IC_Gen", round(value(m.IC_generator()), 2), "| IC_Line", round(value(m.IC_line()), 2), "| IC_backup", round(value(m.IC_backup()), 2),
          "| OPEX", round(value(m.operating_expenses()), 2), "| FC_Gen", round(value(m.FOC_generator()), 2), "| FC_Line", round(value(m.FOC_line()), 2), "| FC_backup", round(value(m.FOC_backup()), 2),
          "| VC_Gen", round(value(m.VOC_generator()), 2), "| VC_Line", round(value(m.VOC_line()), 2), "| VC_Backup", round(value(m.VOC_backup()), 2),
          "| Over-gen penalty", round(value(m.OG_pen()), 2), "| Over generation", round(sum(m.over_gen[i,t,n,b,st].value for i in m.node for t in m.year for n in m.rpdn for b in m.sub for st in m.state), 2),
          "| EENS penalty", round(value(m.EENS_penalties()), 2)
          )
    
    # for t in m.year:
    #     print("Demand every year", round(sum(m.weight_time[n] * m.operation_time[b] * m.load_demand[i,t,n,b] for i in m.node for n in m.rpdn for b in m.sub), 3)  
    #     )    
    
    # print("CAPEX", round(value(m.capital_expenditure()), 2), "| IC_Gen", round(value(m.IC_generator()), 2), "| IC_Line", round(value(m.IC_line()), 2), 
    #       "| OPEX", round(value(m.operating_expenses()), 2), "| FC_Gen", round(value(m.FOC_generator()), 2), "| FC_Line", round(value(m.FOC_line()), 2),
    #       "| VC_Gen", round(value(m.VOC_generator()), 2), "| VC_Line", round(value(m.VOC_line()), 2)
    #       )    


