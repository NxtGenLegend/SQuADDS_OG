# This code defines a class called PALACE_Model that represents a model for chip simulations. Let's go through the code step by step:
# The __init__ method is the constructor of the class. 
# It initializes various attributes of the PALACE_Model object, such as meshing, _metallic_layers, _ground_plane, _fine_meshes, _sim_config, _input_dir, and _output_subdir. 
# It also calls the set_farfield method.
# The create_batch_file and create_config_file methods are empty and don't have any implementation. 
# You can add the necessary code inside these methods to create batch files and configuration files for the chip simulation.
# The _prepare_simulation method is a private method that takes metallic_layers and ground_plane as parameters. 
# It raises a NotImplementedError to indicate that this method should be overridden in the derived classes.
# The prepare_simulation method calls the _prepare_simulation method with the _metallic_layers and _ground_plane attributes as arguments. 
# This method is responsible for preparing the simulation by setting up the metallic layers and ground plane.
# The add_metallic method adds metallic conductors to the chip simulation. 
# It takes the layer_id as a required parameter and additional optional parameters such as threshold, fuse_threshold, evap_mode, group_by_evaporations, and evap_trim. 
# These parameters control various aspects of how the metallic conductors are added to the simulation.
# The add_ground_plane method adds a metallic ground plane to the chip simulation. 
# It takes optional parameters such as threshold to control the simplification of the ground plane geometry.
# The set_farfield method sets the type of farfield boundary condition for the simulation. 
# The ff_type parameter can be either 'absorbing' or 'pec'. It raises an assertion error if an invalid ff_type is provided.
# The run method runs the chip simulation. It first checks if the simulation configuration file (_sim_config) has been set. 
# If not, it raises an assertion error. Then, it sets up the necessary commands to run the simulation using a subprocess. 
# The output of the simulation is redirected to a log file. The method waits for the simulation to complete or handles a keyboard interrupt. 
# Finally, it returns the retrieved data from the simulation. The retrieve_data method is empty and doesn't have any implementation. 
# You can add the necessary code inside this method to retrieve data from the completed simulation.
# The create_batch_file method creates a batch file for running the simulation on a high-performance computing (HPC) system. 
# It generates the content of the batch file based on the provided sbatch dictionary and writes it to a file.
# The _check_simulation_mode method checks the type of simulation being run and returns the parent directory to store the simulation files. 
# It checks the mode attribute and returns the appropriate parent directory based on the simulation mode.
# The _create_directory method creates a directory to hold the simulation files. 
# It takes the directory_name as a parameter and creates the directory under the parent simulation directory based on the simulation mode.
# The _save_mesh_gmsh method saves the Gmsh mesh file. 
# It checks if the create_files attribute is True and then saves the mesh file using the gmsh.write function.
# The _save_mesh_comsol method saves the COMSOL mesh file. 
# It checks if the create_files attribute is True and then saves the mesh file using the comsol_obj.save function. 
# It also exports the mesh file in COMSOL format using the COMSOL export commands.
# The _get_folder_prefix method returns the folder prefix for the simulation output directory. 
# It checks if the input_dir attribute is not empty and returns the concatenation of input_dir, name, and a forward slash. 
# Otherwise, it returns an empty string. The set_local_output_subdir method sets the local output subdirectory for the simulation. 
# It takes the name as a parameter and updates the _output_subdir and _output_dir attributes accordingly. 
# It also updates the simulation configuration file to reflect the new output directory.
# Overall, this code provides a framework for setting up and running chip simulations using the PALACE modeling tool. 
# It allows for the addition of metallic layers, ground planes, and setting various simulation parameters. 
# It also provides methods for creating batch files, saving mesh files, and retrieving simulation data.

from GMeshRenderer import Palace_Gmsh_Renderer as gmsh
import os
import json

class PALACE_Model:
    def __init__(self, meshing, mode, options):
        self.meshing = meshing
        self._metallic_layers = []
        self._ground_plane = {'omit': True}
        self._fine_meshes = []
        self._sim_config = ""
        self._input_dir = ""
        self._output_subdir = ""
        self.set_farfield()

        if mode == 'HPC':
            # with open(options["HPC_Parameters_JSON"], "r") as f:
            #     self.hpc_options = json.loads(f.read())
            with open(options["HPC_Parameters_JSON"], "r") as f:
                self.hpc_options = json.load(f.read())
        else:
            self.palace_dir = options.get('palace_dir', 'palace')                
            self.hpc_options = {"input_dir":""}

    def create_batch_file(self):
        pass
    def create_config_file(self):
        pass
    def _prepare_simulation(self, metallic_layers, ground_plane):
        raise NotImplementedError()

    def prepare_simulation(self):
        self._prepare_simulation(self._metallic_layers, self._ground_plane)

    def add_metallic(self, layer_id, **kwargs):
        '''
        Adds metallic conductors from the Qiskit-Metal design object onto the surface layer of the chip simulation. If the particular layer has
        fancy PVD evaporation steps, the added metallic layer will account for said steps and merge the final result. In addition, all metallic
        elements that are contiguous are merged into single blobs.

        Inputs:
            - layer_id - The index of the layer from which to take the metallic polygons
            - threshold - (Optional) Defaults to -1. This is the threshold in metres, below which consecutive vertices along a given polygon are
                          combined into a single vertex. This simplification helps with meshing as COMSOL will not overdo the meshing. If this
                          argument is negative, the argument is ignored.
            - fuse_threshold - (Optional) Defaults to 1e-12. This is the minimum distance between metallic elements, below which they are considered
                               to be a single polygon and thus, the polygons are merged with the gap filled. This accounts for floating-point errors
                               that make adjacent elements fail to merge as a single element, due to infinitesimal gaps between them.
            - evap_mode - (Optional) Defaults to 'separate_delete_below'. These are the methods upon which to separate or merge overlapping elements
                          across multiple evaporation steps. See documentation on PVD_Shadows for more details on the available options.
            - group_by_evaporations - (Optional) Defaults to False. If set to True, if elements on a particular evaporation step are separated due
                                      to the given evap_mode, they will still be selected as a part of the same conductor (useful for example, in
                                      capacitance matrix simulations).
            - evap_trim - (Optional) Defaults to 20e-9. This is the trimming distance used in certain evap_mode profiles. See documentation on
                          PVD_Shadows for more details on its definition.
        '''
        self._metallic_layers += [{
            'type': 'design_layer',
            'layer_id': layer_id,
            'threshold': kwargs.get('threshold', -1),
            'fuse_threshold': kwargs.get('fuse_threshold', 1e-12),
            'evap_mode': kwargs.get('evap_mode', 'separate_delete_below'),
            'group_by_evaporations': kwargs.get('group_by_evaporations', False),
            'evap_trim': kwargs.get('evap_trim', 20e-9),
        }]

    def add_ground_plane(self, **kwargs):
        '''
        Adds metallic ground-plane from the Qiskit-Metal design object onto the surface layer of the chip simulation.

        Inputs:
            - threshold - (Optional) Defaults to -1. This is the threshold in metres, below which consecutive vertices along a given polygon are
                          combined into a single vertex. This simplification helps with meshing as COMSOL will not overdo the meshing. If this
                          argument is negative, the argument is ignored.
        '''
        self._ground_plane = {'omit':False, 'threshold':kwargs.get('threshold', -1)}

    def set_farfield(self, ff_type='absorbing'):
        #ff_type can be: 'absorbing' or 'pec'
        ff_type = ff_type.lower()
        assert ff_type == 'pec' or ff_type == 'absorbing', "ff_type must be: 'absorbing' or 'pec'"
        self._ff_type = ff_type

    def run(self):
        assert self._sim_config != "", "Must run prepare_simulation at least once."

        config_file = self._sim_config
        leFile = os.path.basename(os.path.realpath(config_file))
        leDir = os.path.dirname(os.path.realpath(config_file))

        log_location = f"{self._output_data_dir}/out.log"
        with open("temp.sh", "w+") as f:
            f.write(f"cd \"{leDir}\"\n")
            f.write(f"\"{self.palace_dir}\" -np 16 {leFile} | tee \"{log_location}\"\n")
        os.makedirs(self._output_data_dir)
        with open(log_location, 'w') as fp:
            pass

        self.cur_process = subprocess.Popen("./temp.sh", shell=True)
        try:
            self.cur_process.wait()
        except KeyboardInterrupt:
            self.cur_process.kill()
        self.cur_process = None

        return self.retrieve_data()

    def retrieve_data(self):
        pass

    def create_batch_file(self):
        
        #note: I have disabled naming the output file by setting '# SBATCH' instead of '#SBATCH' 
        #so I can get the slurm job number to use for testing

        sbatch = {
                "header": "#!/bin/bash --login",
                "job_name": "#SBATCH --job-name=" + self.name,
                "output_loc": "# SBATCH --output=" + self.name + ".out",
                "error_out": "#SBATCH --error=" + self.name + ".err",
                "partition": "#SBATCH --partition=general",
                "nodes": "#SBATCH --nodes=" + self.hpc_options["HPC_nodes"],
                "tasks": "#SBATCH --ntasks-per-node=20",
                "cpus": "#SBATCH --cpus-per-task=1",
                "memory": "#SBATCH --mem=" + self.hpc_options["sim_memory"],
                "time": "#SBATCH --time=" + self.hpc_options['sim_time'],
                "account": "#SBATCH --account=" + self.hpc_options['account_name'],
                "foss": "module load foss/2021a",
                "cmake": "module load cmake/3.20.1-gcccore-10.3.0",
                "pkgconfig": "module load pkgconfig/1.5.4-gcccore-10.3.0-python",
                "run_command": f"srun {self.hpc_options['palace_location']} " + self.hpc_options["input_dir"] + self.name + "/" + self.name + ".json"
        }
    
        #check simulation mode and return appropriate parent directory 
        parent_simulation_dir = self._check_simulation_mode()

        #create sbatch file name
        sim_file_name = self.name + '.sbatch'

        #destination for config file
        simulation_dir = parent_simulation_dir + str(self.name)

        #save to created directory
        file = os.path.join(simulation_dir, sim_file_name)

        #write sbatch dictionary to file
        with open(file, "w+", newline = '\n') as f:
            for value in sbatch.values():
                f.write('{}\n'.format(value))

    def _check_simulation_mode(self):
        '''method to check the type of simualtion being run and return
            the parent directory to store the simulation files'''

        parent_simulation_dir = None

        if self.mode == "HPC":
            parent_simulation_dir = self.sim_parent_directory
        elif self.mode == "simPC" or self.mode == "PC":
            parent_simulation_dir = self.sim_parent_directory
        else:
            Exception('Invalid simulation mode entered.')
        
        return parent_simulation_dir



    def _create_directory(self, directory_name):
        '''create a directory to hold the simulation files'''

        parent_simulation_dir = self._check_simulation_mode()

        # Directory
        directory = directory_name
  
        # Path
        path = os.path.join(parent_simulation_dir, directory)
  
        # Create the directory
        if not os.path.exists(path):
            os.mkdir(path)
            print("Directory '% s' created" % directory)


    def _save_mesh_gmsh(self):
        '''function used to save the gmsh mesh file'''
        if self.create_files == True:
            parent_simulation_dir = self._check_simulation_mode()

            # file_name
            file_name = self.name + "/" + self.name + ".msh"
    
            # Path
            path = os.path.join(parent_simulation_dir, file_name)
            gmsh.write(path)
            
    def _get_folder_prefix(self):
        return self.hpc_options["input_dir"]  + self.name + "/" if self.hpc_options["input_dir"] != "" else ""

    def set_local_output_subdir(self, name, update_config_file=True):
        self._output_subdir = str(name)
        self._output_dir = self._get_folder_prefix()  + "outputFiles"
        if self._output_subdir != "":
            self._output_dir += "/" + self._output_subdir
        if self._sim_config != "":
            with open(self._sim_config, "r") as f:
                config_json = json.loads(f.read())
            config_json['Problem']['Output'] = self._output_dir
            with open(self._sim_config, "w") as f:
                json.dump(config_json, f, indent=2)
            self._output_data_dir = os.path.dirname(os.path.realpath(self._sim_config)) + "/" + self._output_dir
