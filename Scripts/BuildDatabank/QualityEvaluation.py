import os
import sys
import yaml
import json
import matplotlib.pyplot as plt
import numpy as np
import math
import argparse
import decimal as dc

from random import randint

from matplotlib import cm
from scipy.stats import norm

import urllib.request
from urllib.error import URLError,HTTPError,ContentTooShortError

sys.path.insert(1, '../BuildDatabank/')
from databankLibrary import download_link, lipids_dict, read_trajs_calc_OPs, parse_op_input, find_OP, OrderParameter
import buildH_calcOP_test


#order parameters or quality analysis
parser = argparse.ArgumentParser(description="")
parser.add_argument("-op",action='store_true', help="Calculate order parameters for simulations in data bank "
                        "format.")
parser.add_argument("-q",action='store_true', help="Quality evaluation of simulated order parameters "
                        "format.")
args = parser.parse_args()

lipid_numbers_list = lipids_dict.keys() # should contain all lipid names
#################################
class Simulation:
    def __init__(self, readme, data, indexingPath):
        self.readme = readme
        self.data = data #dictionary where key is the lipid type and value is order parameter file
        self.indexingPath = indexingPath
        
    def getLipids(self, molecules=lipid_numbers_list):
        lipids = []
        
        for key in self.readme['COMPOSITION'].keys():
            if key in molecules:
                lipids.append(key)
        return lipids
        
class Experiment:
    pass

#class Data:
#    def __init__(self, molecule, data_path):
#        self.molecule = molecule
#        self.data = {}
#        self.__load_data__(data_path)
#    
#    def __load_data__(self,data_path):
#        with open(data_path) as json_file:
#            self.data = json.load(json_file)
#        json_file.close()

#Quality evaluation of simulated data


def prob_S_in_g(OP_exp, exp_error, OP_sim, op_sim_sd):
    #normal distribution N(s, OP_sim, op_sim_sd)
    a = OP_exp - exp_error
    b = OP_exp + exp_error
    #P_S = norm.cdf(b, loc=OP_sim, scale=op_sim_sd) - norm.cdf(a, loc=OP_sim, scale=op_sim_sd)
    #changing to survival function to increase precision, note scaling. Must be recoded to increase precision still
    P_S = -norm.sf(b, loc=OP_sim, scale=op_sim_sd) + norm.sf(a, loc=OP_sim, scale=op_sim_sd)

    if math.isnan(P_S) :
     return P_S

    #this is an attempt to deal with precision, max set manually to 70
    dc.getcontext().prec=70
    precise_log=-dc.Decimal(P_S).log10()

    #print("difference of two prec logs",float(foo)+math.log10(P_S))

    return float(precise_log)


def OPquality(OP_exp, OP_sim):
    quality = np.absolute(OP_exp - OP_sim)
    return quality
    
# quality of molecule fragments

def evaluated_percentage(fragments, exp_op_data):
    count_value = 0
    fragment_size = 0
    for key, value in exp_op_data.items():
        for f in fragments:
             if f in key:
                 fragment_size += 1
                 if value[0][0] != 'nan':
                     count_value += 1
    if fragment_size != 0:
        return count_value / fragment_size
    else:
        return 0
    
#def carbonError(OP_sim, OP_exp):
    
#    E_i = 0
#    quality = OPquality(OP_exp, OP_sim)

#    if quality > 0.02:
#        E_i = quality - 0.02
#    else:
#        E_i = 0
#    return E_i  



def fragmentQuality(fragments, exp_op_data, sim_op_data):
    print("fragment quality")
    p_F = evaluated_percentage(fragments, exp_op_data)
    #warning, hard coded experimental error
    exp_error=0.02
    E_sum = 0
    if p_F != 0:
        for fr in fragments:
            for key_exp, value_exp in exp_op_data.items():
            #    print(key_exp)
            #    print(value_exp[0][0])
                if (fr in key_exp) and value_exp[0][0] != 'nan':
                    OP_exp = value_exp[0][0]
                   # print(OP_exp)
                    OP_sim = sim_op_data[key_exp][0]
                   # print(OP_sim)
                    op_sim_STEM=sim_op_data[key_exp][0][2]
                    
               #change here if you want to use shitness(TM) scale for fragments. Warning big umbers will dominate
                    E_sum+= prob_S_in_g(OP_exp, exp_error, OP_sim, op_sim_STEM)
        E_F = E_sum / p_F
        return E_F
    else:
        return 'nan'
        
def loadSimulations():
    simulations = []
    for subdir, dirs, files in os.walk(r'../../Data/Simulations/'): #
        for filename1 in files:
            filepath = subdir + os.sep + filename1
        
            if filepath.endswith("README.yaml"):
                READMEfilepathSimulation = subdir + '/README.yaml'
                readmeSim = {}
                with open(READMEfilepathSimulation) as yaml_file_sim:
                    readmeSim = yaml.load(yaml_file_sim, Loader=yaml.FullLoader)
                yaml_file_sim.close()    
                indexingPath = "/".join(filepath.split("/")[4:8])
                print(indexingPath)
                print(filepath)
                print(readmeSim)
                try:
                    experiments = readmeSim['EXPERIMENT']
                except KeyError:
                    # print("No matching experimental data for system " + readmeSim['SYSTEM'] + " in directory " + indexingPath)
                    continue
                else:
                    if any(experiments.values()): #if experiments is not empty
                        print(any(experiments))
                        simOPdata = {} #order parameter files for each type of lipid
                        for filename2 in files:
                            if filename2.endswith('OrderParameters.json'):
                                lipid_name = filename2.replace('OrderParameters.json', '')
                             #  print(lipid_name)
                                dataPath = subdir + "/" + filename2
                                OPdata = {}
                                with open(dataPath) as json_file:
                                    OPdata = json.load(json_file)
                                json_file.close()
                                simOPdata[lipid_name] = OPdata
                                    
                        simulations.append(Simulation(readmeSim, simOPdata, indexingPath))
                    else:
                        print("The simulation does not have experimental data.")
                        continue
                
                    
    return simulations

    
###################################################################################################
simulations = loadSimulations()

if (not os.path.isdir('../../Data/QualityEvaluation/')): 
    os.system('mkdir ../../Data/QualityEvaluation/')

for simulation in simulations:
    sub_dirs = simulation.indexingPath.split("/")
   # os.system('mkdir ../../Data/QualityEvaluation/' + sub_dirs[0])
   # os.system('mkdir ../../Data/QualityEvaluation/' + sub_dirs[0] + '/' + sub_dirs[1])
   # os.system('mkdir ../../Data/QualityEvaluation/' + sub_dirs[0] + '/' + sub_dirs[1] + '/' + sub_dirs[2])    
   # os.system('mkdir ../../Data/QualityEvaluation/' + sub_dirs[0] + '/' + sub_dirs[1] + '/' + sub_dirs[2] + '/' + sub_dirs[3])
    
    #save OP quality here
    DATAdir = '../../Data/Simulations/' + str(sub_dirs[0]) + '/' + str(sub_dirs[1]) + '/' + str(sub_dirs[2]) + '/' + str(sub_dirs[3])
   # print(DATAdir)
     

    for lipid1 in simulation.getLipids():
        #print(lipid1)
        print(simulation.indexingPath)
        #print(simulation.data.keys())
        
        # OP_data_lipid = simulation.data[lipid1]
        OP_data_lipid = {}
        #convert elements to float because in some files the elements are strings
        for key, value in simulation.data[lipid1].items():
            OP_array = [float(x) for x in simulation.data[lipid1][key][0]]  
            OP_data_lipid[key] = OP_array
            
        
        
        # go through file paths in simulation.readme['EXPERIMENT']
        print(simulation.readme['EXPERIMENT'].values())
        exit()
        
        for lipid, experiments in simulation.readme['EXPERIMENT'].items():
            data_dict = {}
            fragment_qual_dict = {}
            for doi, path in experiments.items():
                OP_qual_data = {}
            # get readme file of the experiment
                experimentFilepath = "../../Data/experiments/" + path
                print(experimentFilepath)
                READMEfilepathExperiment  = experimentFilepath + '/README.yaml'
                experiment = Experiment()
                with open(READMEfilepathExperiment) as yaml_file_exp:
                    readmeExp = yaml.load(yaml_file_exp, Loader=yaml.FullLoader)
                    experiment.readme = readmeExp
                    print(experiment.readme)
                yaml_file_exp.close()

                exp_OP_filepath = experimentFilepath + '/' + lipid1 + '_Order_Parameters.json'
                print(exp_OP_filepath)
                lipidExpOPdata = {}
                try:
                    with open(exp_OP_filepath) as json_file:
                        lipidExpOPdata = json.load(json_file)
                    json_file.close()
                except FileNotFoundError:
                    print("Experimental order parameter data do not exist for lipid " + lipid1 + ".")
                    break


                exp_error = 0.02
           
                for key in OP_data_lipid.keys():
                    OP_array = OP_data_lipid[key].copy()
                    try:
                        OP_exp = lipidExpOPdata[key][0][0]
                    except KeyError:
     #                   OP_array.append('NaN')
     #                   OP_qual_data[key] = OP_array
                        continue
                    else:
                        if OP_exp is not 'NaN':
                            OP_sim = OP_array[0]
                            op_sim_STEM = OP_array[2]
                            #changing to use shitness(TM) scale. This code needs to be cleaned
                            op_quality = prob_S_in_g(OP_exp, exp_error, OP_sim, op_sim_STEM)
                            OP_array.append(OP_exp)
                            OP_array.append(exp_error)   #hardcoded!!!! 0.02 for all experiments
                            OP_array.append(op_quality)
                      #  else:
                        #    OP_array.append(OP_exp)
                        #    OP_array.append(exp_error)  #hardcoded!!!! 0.02 for all experiments
                       #     OP_array.append('NaN')
                
                    OP_qual_data[key] = OP_array    
                
                print(OP_qual_data)
                
                data_dict[doi] = OP_qual_data
                
                # calculate quality for molecule fragments headgroup, sn-1, sn-2
                headgroup = fragmentQuality(['M_G3','M_G1_','M_G2_'], lipidExpOPdata, OP_data_lipid)
                sn1 = fragmentQuality(['M_G1C'], lipidExpOPdata, OP_data_lipid)
                sn2 = fragmentQuality(['M_G2C'], lipidExpOPdata, OP_data_lipid)
            
                fragment_quality = {}
                fragment_quality['headgroup'] = headgroup
                fragment_quality['sn-1'] = sn1
                fragment_quality['sn-2'] = sn2
                
                fragment_qual_dict[doi] = fragment_quality
              #  print('headgroup ')
              #  print(headgroup)
              #  print('sn1 ') 
              #  print(sn1)
              #  print('sn2 ') 
              #  print(sn2) 
            
                fragment_quality_file = DATAdir + '/' + lipid1 + '_FragmentQuality.json'
            
                with open(fragment_quality_file, 'w') as f:
                    json.dump(fragment_qual_dict,f)
                f.close()
                
                
                
        

        #write into the OrderParameters_quality.json quality data file                  
            outfile = DATAdir + '/' + lipid1 + '_OrderParameters_quality.json'
        #doi : {'carbon hydrogen': [op_sim, sd_sim, stem_sim, op_exp, exp_error, quality] ... }
            with open(outfile, 'w') as f:
                json.dump(data_dict,f)
            f.close()

            
        

        
        
     #   print(OP_qual_data)                        
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
