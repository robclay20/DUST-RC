#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue May 14 09:28:35 2019

@author: rob

UKF with one state
"""


import os
os.chdir("/home/rob/DUST-RC/Python Scripts")
import numpy as np
from StationSim_UKF import Model, Agent
from filterpy.kalman import MerweScaledSigmaPoints as MSSP
from filterpy.kalman import UnscentedKalmanFilter as UNKF
from filterpy.common import Q_discrete_white_noise as QDWN
from scipy.spatial import distance as dist
import matplotlib.pyplot as plt
import datetime
from tqdm import tqdm as tqdm
import pandas as pd

sqrt2 = np.sqrt(2)
    
class UKF:
    """
    individually assign a UKF wrapper to each agent 
    update each agent individually depending on whether it is currently active within the model
    whether KF updates is determined by the "activity matrix" sourced at each time step from agent.active propertysqrt2 = np.sqrt(2)

    if active, update KF using standard steps
    this allows for comphrehensive histories to be stored in KF objects
    
    """
    
    def __init__(self,Model,params):
        self.params = params
        self.pop_total = self.params["pop_total"]
        self.time_id = 0
        self.number_of_iterations = params['batch_iterations']
        self.base_model = Model(params)
        self.UKF = None #dictionary of KFs for each agent
        self.UKF_histories = []
        self.finished = 0 #number of finished agents
        self.sample_rate = self.params["sample_rate"]
        
  

    def F_x(x,dt,self):
        """
        Transition function for each agent. where it is predicted to be.
        For station sim this is essentially gradient * v *dt assuming no collisions
        with some algebra to get it into cartesian plane.
        
        !to generalise this to every agent need to find the "ideal move" for each I.E  assume no collisions
        will make class agent_ideal which essential is the same as station sim class agent but no collisions in move phase
        """
        loc = [agent.ideal_location for agent in self.base_model.agents]
        loc = np.array(loc)
        loc = loc.flatten()
        return loc
        
        
    def H_x(location,z):
        """
        Measurement function for agent.
        !im guessing this is just the output from base_model.step
        """
        return z
    
    
    
    def init_ukf(self):
        
        """
        either updates or initialises UKF else ignores agent depending on activity status
        """
        
        "init UKF"
        
        state = self.base_model.agents2state(self)
        sigmas = MSSP(n=len(state),alpha=.00001,beta=.2,kappa=1) #sigmapoints
        self.ukf =  UNKF(dim_x=len(state),dim_z=len(state),fx = self.F_x, hx=self.H_x, dt=1, points=sigmas)#init UKF
        self.ukf.x = state #initial state
        self.ukf.R = np.eye(len(state))*self.params["Sensor_Noise"] #sensor noise. larger noise implies less trust in sensor and to favour prediction
        self.ukf.Q = np.zeros((len(state),len(state)))
        self.ukf.P = np.eye(len(state))
        
        for i in range(int(len(state)/2)):  #! initialise process noise as blocked structure of discrete white noise. cant think of any better way to do this
            i1 = 2*i
            i2 = (2*(i+1))
            self.ukf.Q[i1:i2,i1:i2] =  QDWN(2,dt=1,var=self.params["Process_Noise"])
             
        self.ukf.Q = np.eye(len(state))


    def updates(self):
        """
        step agents. step UKF. calculate gain using predictions and actual and update UKF agent positions
        """
        self.base_model.step() #jump agents forward using actual position
        agents = self.base_model.agents
        
        self.ukf.predict(self)
        state = self.base_model.agents2state()
        self.ukf.update(z=state)
        self.UKF_histories.append(self.ukf.x)
        #self.finished = 0
        #for agent in agents:
        #    if agent.active==2:
        #        self.finished+=1
       
            
        return
                
    
    def batch(self):
        time1 = datetime.datetime.now()
        self.init_ukf() #init UKF
        #self.F_x(dt=1,agents = self.base_model.agents)
        
        for _ in tqdm(range(self.number_of_iterations-1)): #cycle over batch iterations. tqdm gives progress bar on for loop.
            self.updates()
            
            f = []
            for j in range(self.pop_total):
                f.append(self.base_model.agents[j].active)
            g=np.array(f)
            
            if np.sum(g==2) == self.pop_total:
                break
                
        time2 = datetime.datetime.now()
        
        print(time2-time1)
        return
    

    def plots(self):
        a = np.vstack(self.UKF_histories)
        b = {}
        for k in range(model_params["pop_total"]):
            b[k] =  self.base_model.agents[k].history_loc
            
        b2= np.zeros(a.shape)
    

        for i in range(int(a.shape[1]/2)):
            
            b3 = np.vstack(list(b.values())[i])
            b2[:b3.shape[0],(2*i):(2*i)+2] = b3
            b2[b3.shape[0]:,(2*i):(2*i)+2] = np.NaN
        b = b2


        plt.figure()
        for j in range(model_params["pop_total"]):
            plt.plot(a[:,2*j],a[:,(2*j)+1])    
        
        plt.figure()
        for j in range(model_params["pop_total"]):
            plt.plot(b[:,2*j],b[:,(2*j)+1])    

            
        errors = True
        if errors:
            
            "find mean error between agent and prediction"
            c = {}
            c_means = []
            
            
            for i in range(int(b.shape[1]/2)):
                a_2 =   a[:,(2*i):(2*i)+2] 
                b_2 =   b[:,(2*i):(2*i)+2] 
        
    
                c[i] = []
                for k in range(a_2.shape[0]):
                    if np.isnan(b_2[k,0]) or np.isnan(b_2[k,1]):
                        c[i].append(np.nan)
                    else:                       
                        c[i].append(dist.euclidean(a_2[k,:],b_2[k,:]))
                    
                c_means.append(np.nanmean(c[i]))
            
            c = np.vstack(c.values())
            time_means = np.nanmean(c,axis=0)
            plt.figure()
            plt.plot(time_means)
                
        
                
                
            index = np.where(c_means == np.nanmax(c_means))[0][0]
            print(index)
            a1 = a[:,(2*index):(2*index)+2]
            b1 = b[:,(2*index):(2*index)+2]
            plt.figure()
            plt.plot(b1[:,0],b1[:,1],label= "True Path")
            plt.plot(a1[:,0],a1[:,1],label = "KF Prediction")
            plt.legend()
            
        return a1,b1

    def save_histories(self):
        a = np.vstack(self.UKF_histories)
        b = {}
        for k in range(model_params["pop_total"]):
            b[k] =  self.base_model.agents[k].history_loc
            
        b2= np.zeros(a.shape)
    

        for i in range(int(a.shape[1]/2)):
            
            b3 = np.vstack(list(b.values())[i])
            b2[:b3.shape[0],(2*i):(2*i)+2] = b3
            b2[b3.shape[0]:,(2*i):(2*i)+2] = np.NaN
        b = b2
       
        
         
         
        

                
        return a,b
    
    
    
if __name__ == "__main__":
    runs = 10
    
    model_params = {
                    'width': 200,
                    'height': 100,
                    'pop_total': 10,
                    'entrances': 3,
                    'entrance_space': 2,
                    'entrance_speed': 1,
                    'exits': 2,
                    'exit_space': 1,
                    'speed_min': .1,
                    'speed_desire_mean': 1,
                    'speed_desire_std': 1,
                    'separation': 4,
                    'wiggle': 1,
                    "Sensor_Noise": 2,
                    "Process_Noise": 2,
                    'batch_iterations': 10000,
                    'sample_rate': 5,
                    'do_save': True,
                    'do_plot': True,
                    'do_ani': False
                    }
        
    

    
    for i in range(runs):
       
        U = UKF(Model, model_params)
        U.batch()
        #U.plots()
        a,b = U.save_histories()
        pop = model_params["pop_total"]
        np.save(f"UKF_TRACKS_{pop}_{i}",a)
        np.save(f"ACTUAL_TRACKS_{pop}_{i}",b)
