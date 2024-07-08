import os
import json
import gmsh
import pandas as pd
from qiskit_metal import designs
from SQDMetal.Utilities.QUtilities import QUtilities
from SQDMetal.PALACE.Model import PALACE_Model_RF_Base
from SQDMetal.PALACE.SQDGmshRenderer import Palace_Gmsh_Renderer
from SQDMetal.PALACE.Eigenmode_Simulation import PALACE_Eigenmode_Simulation
from SQDMetal.Utilities.Materials import Material

def setup_palace_simulation(metal_design_path, sim_parent_directory, user_options, sim_name):
    # Load the Qiskit Metal design
    metal_design = designs.DesignPlanar()
    metal_design.load(metal_design_path)

    # Create the simulation object
    eigen_sim = PALACE_Eigenmode_Simulation(
        name=sim_name, 
        metal_design=metal_design,
        sim_parent_directory=sim_parent_directory,
        mode='HPC',
        meshing='GMSH',
        user_options=user_options,
        view_design_gmsh_gui=False,
        create_files=True
    )

    # Add necessary components and ground planes
    eigen_sim.add_metallic(layer_id=1)  # Adding metallic layer with ID 1
    eigen_sim.add_ground_plane()        # Adding ground plane

    # Add in the RF ports
    eigen_sim.create_port_CPW_on_Launcher('LP1', 20e-3)
    eigen_sim.create_port_CPW_on_Launcher('LP2', 20e-3)

    # Fine-mesh routed paths
    eigen_sim.fine_mesh_along_path(100e-6, 'resonator1', mesh_sampling=130, mesh_min=5e-3, mesh_max=120e-3)
    eigen_sim.fine_mesh_along_path(100e-6, 'TL', mesh_sampling=130, mesh_min=7e-3, mesh_max=120e-3)

    # Fine-mesh a rectangular region
    eigen_sim.fine_mesh_in_rectangle(-0.14e-3, -1.33e-3, 0.14e-3, -1.56e-3, mesh_sampling=130, mesh_min=5e-3, mesh_max=120e-3)

    # Prepare the simulation (generates config and batch files)
    eigen_sim.prepare_simulation()

    # If needed, you can run the simulation (this will depend on your environment setup)
    # eigen_sim.run()

# Example user options
user_options = {
    "fillet_resolution": 4,
    "mesh_refinement": 0,
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

# Define the paths
metal_design_path = 'path/to/your/qiskit_metal_design.json'  
sim_parent_directory = 'path/to/simulations'  

# Run the setup function
setup_palace_simulation(metal_design_path, sim_parent_directory, user_options)
