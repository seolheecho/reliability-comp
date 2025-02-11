from example_data import read_data, read_prod_data
from utilities import solve_model, solve_prob_model, export_results
from no_model import no_reliability_model
from reserve_model import reserve_reliability_model
from n_k_model import n_k_reliability_model
from prob_model import prob_reliability_model


def solution_algorithm(datafolder, advanced, renewable, time_limit, abs_gap):
    """
    Solves the optimization problem using a two-level modeling approach.
    
    Parameters:
        datafolder (str): Type of case studies -> 'Illustrative' or 'San Diego'
        advanced (str): Type of reliability modelings -> 'no', 'reserve', 'n-1', 'n-2', 'prob'
        renewable (str): Whether the renewable constraint is included or not -> True or False
        time_limit (num): Computational time limit
        abs_gap (num): Optimality gap
    
    Returns:
        dict: A dictionary containing upper- and lower-level results.
    """

    # Call the corresponding data
    data = read_data(datafolder, advanced)


    # Call the upper models
    if advanced == 'no':
        print('Planning without reliability is selected...')
        upper_model = no_reliability_model(data, renewable)

    elif advanced == 'reserve':
        print('Planning using reserve margin is selected...')
        upper_model = reserve_reliability_model(data, renewable)

    elif advanced in ['n-1','n-2']:
        print('Planning using n-k reliability is selected...')
        upper_model = n_k_reliability_model(data, renewable)

    else:
        print('Planning using the probability of failure is selected...')
        upper_model = prob_reliability_model(data, renewable)    


    # Solve the models of interest and print the results 
    print("Solving upper-level model...")
    upper_model = solve_model(upper_model, advanced, renewable, time_limit, abs_gap)



    # Export results to excel for further analysis
    if advanced in ['no','reserve','n-1','n-2']:
        variables_dict = {"cap_ins_gen": upper_model.cap_ins,
                          "cap_ins_line": upper_model.cap_ins_line,
                          "cap_ava_gen": upper_model.cap_ava,
                          "cap_ava_line": upper_model.cap_ava_line,
                          "prod_gen": upper_model.ppd,
                          "flow_line": upper_model.flow,
                          "over_gen": upper_model.over_gen
        }

    else:
        variables_dict = {"cap_ins_gen": upper_model.cap_ins,
                          "cap_ins_line": upper_model.cap_ins_line,
                          "cap_ins_backup": upper_model.cap_bn,
                          "cap_ava_gen": upper_model.cap_ava,
                          "cap_ava_line": upper_model.cap_ava_line,
                          "cap_ava_backup": upper_model.cap_b,
                          "prod_gen": upper_model.ppd,
                          "prod_back": upper_model.ppd_b,
                          "flow_line": upper_model.flow,
                          "over_gen": upper_model.over_gen
        }

    export_results(datafolder, variables_dict, advanced, renewable)



    ##################          Solution strategy          ################## 

    if advanced in ['no','reserve','n-1','n-2']:
        # Export capacity results
        capacity_gen = {(i,k,t): upper_model.cap_ins[i,k,t].value 
                        for i in upper_model.node 
                        for k in upper_model.gen_pn 
                        for t in upper_model.year
                    }
        capacity_line = {(l,t): upper_model.cap_ins_line[l,t].value 
                            for l in upper_model.line_pn
                            for t in upper_model.year
                    }
        capacity_backup = {(i,k,t): 0 
                            for i in upper_model.node 
                            for k in upper_model.dis_pn 
                            for t in upper_model.year
                        }
        
        
        # Call data & probabilistic models
        prob_data = read_prod_data(datafolder)
        lower_model = prob_reliability_model(prob_data, renewable)

        
        # Fix the investment results using the upper models' results
        for i in lower_model.node:
            for k in lower_model.gen_pn:
                for t in lower_model.year:
                    lower_model.cap_ins[i,k,t].fix(capacity_gen[i,k,t])
        
        for i in lower_model.node:
            for k in lower_model.dis_pn:
                for t in lower_model.year:
                    lower_model.cap_b[i,k,t].fix(capacity_backup[i,k,t])

        for l in lower_model.line_pn:
            for t in lower_model.year:
                lower_model.cap_ins_line[l,t].fix(capacity_line[l,t])


        # Deactivate LOLE constraint as this is not possible to be met with the fixed design
        print("Deactivating LOLE constraint...")
        lower_model.LOLE_limit.deactivate()

        if renewable == True:
            print("Deactivating renewable generation constraint...")
            lower_model.renewable_gen_power.deactivate()

        
        # Run the lower model (probabilistic model)
        print("Solving lower-level model...")
        lower_model = solve_prob_model(lower_model, renewable, time_limit, abs_gap)


        return {
            "upper-level results": upper_model.results,
            "lower-level results": lower_model.results
        }


    else: 
        print("Stop the solution algorithm..")

        return {
            "reliability results": upper_model.results
        }


# Example usage
datafolder = 'San Diego'    # case_studies -> 'Illustrative','San Diego'
advanced = 'dual-yes'        # reliability formulation -> 'no', 'reserve', 'n-1', 'n-2', 'dual-no', 'dual-yes'
renewable = True           # renewable constraint -> True, False
time_limit = 1000
abs_gap = 0.01

results = solution_algorithm(datafolder, advanced, renewable, time_limit, abs_gap)