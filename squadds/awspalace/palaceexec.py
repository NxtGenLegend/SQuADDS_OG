#from SQDMetal.PALACE.Eigenmode_Simulation import PALACE_Eigenmode_Simulation
#from SQDMetal.PALACE.SQDGmshRenderer import Palace_Gmsh_Renderer
from eigenmodesim import PALACE_Eigenmode_Simulation
from GMeshRenderer import Palace_Gmsh_Renderer

# This code appears to be a part of a larger project related to electromagnetic simulations using the PALACE framework. 
# Let's break down the code and understand what each part is doing:
# Importing Modules: The code begins by importing the necessary modules, including PALACE_Eigenmode_Simulation and Palace_Gmsh_Renderer.
# Class Definition: The code defines a class called Palace. 
# This class has an __init__ method that takes a user_defined_options dictionary as input. 
# It checks if all the required options are present in the dictionary, and if not, raises a ValueError with a corresponding error message. 
# It then sets the attributes of the class based on the key-value pairs in the user_defined_options dictionary.
# Function Definitions: The code includes several function definitions, such as setattr, add_metallic, add_ground_plane, create_port_CPW_on_Launcher, fine_mesh_along_path, fine_mesh_in_rectangle, and prepare_simulation. 
# These functions perform various operations related to the PALACE simulation, such as adding metallic conductors, adding a ground plane, creating RF ports, defining fine meshing along a path or within a rectangle, and preparing the simulation.
# PALACE_Eigenmode_Simulation Class: The code also includes the definition of the PALACE_Eigenmode_Simulation class, which inherits from the PALACE_Model_RF_Base class. 
# This class represents a specific type of simulation called eigenmode simulation. 
# It has a constructor that takes various parameters, including the simulation name, the metal design, the simulation parent directory, the simulation mode, the meshing type, and user-defined options. 
# It initializes the attributes of the class based on the input parameters.
# Additional Methods: The PALACE_Eigenmode_Simulation class includes additional methods such as create_config_file, set_freq_search, and retrieve_data. 
# These methods are responsible for creating the configuration file for the simulation, setting the frequency search parameters, and retrieving the simulation data, respectively.
# Overall, this code defines classes and functions that are used to set up and perform electromagnetic simulations using the PALACE framework. 
# It provides functionality for defining simulation options, adding conductors and ground planes, creating RF ports, specifying fine meshing, and preparing and retrieving simulation data.

class Palace():
    def __init__(self, user_defined_options: dict):
        required_options = [
            "mesh_refinement",
            "dielectric_material",
            "starting_freq",
            "number_of_freqs",
            "solns_to_save",
            "solver_order",
            "solver_tol",
            "solver_maxits",
            "comsol_meshing",
            "mesh_max",
            "mesh_min",
            "mesh_sampling",
            "sim_memory",
            "sim_time",
            "HPC_nodes",
            "fillet_resolution"
        ]
        for option in required_options:
            if option not in user_defined_options:
                raise ValueError(f"Missing required option: {option}")
        for key, value in user_defined_options.items():
            setattr(self, key, value)

    
#Eigenmode Simulation Options
# user_defined_options = {
#                  "mesh_refinement":  0,                             #refines mesh in PALACE - essetially divides every mesh element in half
#                  "dielectric_material": "silicon",                  #choose dielectric material - 'silicon' or 'sapphire'
#                  "starting_freq": 7.5,                              #starting frequency in GHz 
#                  "number_of_freqs": 4,                              #number of eigenmodes to find
#                  "solns_to_save": 4,                                #number of electromagnetic field visualizations to save
#                  "solver_order": 2,                                 #increasing solver order increases accuracy of simulation, but significantly increases sim time
#                  "solver_tol": 1.0e-8,                              #error residual tolerance foriterative solver
#                  "solver_maxits": 100,                              #number of solver iterations
#                  "comsol_meshing": "Extremely fine",                #level of COMSOL meshing: 'Extremely fine', 'Extra fine', 'Finer', 'Fine', 'Normal'
#                  "mesh_max": 120e-3,                                #maxiumum element size for the mesh in mm
#                  "mesh_min": 10e-3,                                 #minimum element size for the mesh in mm
#                  "mesh_sampling": 130,                              #number of points to mesh along a geometry
#                  "sim_memory": '300G',                              #amount of memory for each HPC node i.e. 4 nodes x 300 GB = 1.2 TB
#                  "sim_time": '20:00:00',                            #allocated time for simulation 
#                  "HPC_nodes": '4',                                  #number of Bunya nodes. By default 20 cpus per node are selected, then total cores = 20 x HPC_nodes
#                  "fillet_resolution":12                             #Number of vertices per quarter turn on a filleted path
#                 }

#eigenmode simulation options
user_options = {
                "fillet_resolution": 4,
                "mesh_refinement":  0,
                "dielectric_material": "silicon",
                "starting_freq": 5.5,
                "number_of_freqs": 5,
                "solns_to_save": 5,
                "solver_order": 2,
                "solver_tol": 1.0e-8,
                "solver_maxits": 100,
                "mesh_max": 100e-3,
                "mesh_min": 10e-3,
                "mesh_sampling": 120,
                "comsol_meshing": "Extremely fine",
                "HPC_Parameters_JSON": ""
            }

#Creat the Palace Eigenmode simulation
eigen_sim = PALACE_Eigenmode_Simulation(name ='single_resonator_example_eigen',                     #name of simulation
                                        #metal_design = design,                                      #feed in qiskit metal design
                                        sim_parent_directory = "",            #choose directory where mesh file, config file and HPC batch file will be saved
                                        mode = 'HPC',                                               #choose simulation mode 'HPC' or 'simPC'                                          
                                        meshing = 'GMSH',                                           #choose meshing 'GMSH' or 'COMSOL'
                                        user_options = user_defined_options,                        #provide options chosen above
                                        view_design_gmsh_gui = False,                               #view design in GMSH gui 
                                        create_files = True)                                        #create mesh, config and HPC batch files
eigen_sim.add_metallic(1)
eigen_sim.add_ground_plane()

#Add in the RF ports
eigen_sim.create_port_CPW_on_Launcher('LP1', 20e-3)
eigen_sim.create_port_CPW_on_Launcher('LP2', 20e-3)
#Fine-mesh routed paths
eigen_sim.fine_mesh_along_path(100e-6, 'resonator1', mesh_sampling=130, mesh_min=5e-3, mesh_max=120e-3)
eigen_sim.fine_mesh_along_path(100e-6, 'TL', mesh_sampling=130, mesh_min=7e-3, mesh_max=120e-3)
#Fine-mesh a rectangular region
eigen_sim.fine_mesh_in_rectangle(-0.14e-3, -1.33e-3, 0.14e-3, -1.56e-3, mesh_sampling=130, mesh_min=5e-3, mesh_max=120e-3)

eigen_sim.prepare_simulation()