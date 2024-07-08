# THIS IS NOT FINISHED

import json
import os
import gmsh
import numpy as np
from qiskit_metal import designs
from SQDMetal.Utilities.QUtilities import QUtilities
from SQDMetal.PALACE.SQDGmshRenderer import Palace_Gmsh_Renderer

class Material:
    def __init__(self, name):
        self.name = name
        if name == "silicon":
            self.permittivity = 11.45 
            self.permeability = 1.0
        else:
            self.permittivity = 1.0
            self.permeability = 1.0

class PALACE_Model:
    def __init__(self, name, metal_design, sim_parent_directory, mode, meshing, user_options={}, view_design_gmsh_gui=False, create_files=True):
        self.name = name
        self.metal_design = metal_design
        self.sim_parent_directory = sim_parent_directory
        self.mode = mode
        self.user_options = user_options
        self.view_design_gmsh_gui = view_design_gmsh_gui
        self.create_files = create_files
        self._ports = []
        self.meshing = meshing
        self._metallic_layers = []
        self._ground_plane = {'omit': True}
        self._fine_meshes = []
        self._sim_config = ""
        self._input_dir = ""
        self._output_subdir = ""
        self.set_farfield()

        if mode == 'HPC':
            with open(user_options["HPC_Parameters_JSON"], "r") as f:
                self.hpc_options = json.load(f)
        else:
            self.palace_dir = user_options.get('palace_dir', 'palace')
            self.hpc_options = {"input_dir": ""}

    def create_config_file(self, gmsh_render_attrs):
        raise NotImplementedError("This method should be implemented in the subclass.")

    def create_batch_file(self):
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

        parent_simulation_dir = self._check_simulation_mode()
        simulation_dir = os.path.join(parent_simulation_dir, self.name)
        sim_file_name = self.name + '.sbatch'
        file = os.path.join(simulation_dir, sim_file_name)

        with open(file, "w+", newline='\n') as f:
            for value in sbatch.values():
                f.write('{}\n'.format(value))

    def add_metallic(self, layer_id, **kwargs):
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
        self._ground_plane = {'omit': False, 'threshold': kwargs.get('threshold', -1)}

    def set_farfield(self, ff_type='absorbing'):
        ff_type = ff_type.lower()
        assert ff_type == 'pec' or ff_type == 'absorbing', "ff_type must be: 'absorbing' or 'pec'"
        self._ff_type = ff_type

    def create_port_CPW_on_Launcher(self, launcher_name, width):
        self._ports.append({
            'port_name': launcher_name,
            'portAcoords': [0, 0],  # Example coordinates, update accordingly
            'portBcoords': [width, 0]  # Example coordinates, update accordingly
        })

    def fine_mesh_along_path(self, length, path_name, mesh_sampling, mesh_min, mesh_max):
        unit_conv = QUtilities.get_units(self.metal_design)
        lePath = QUtilities.calc_points_on_path(length/unit_conv, self.metal_design, path_name)[0] * unit_conv
        self._fine_meshes.append({
            'type': 'path',
            'path': lePath * 1e3,  # Convert to mm
            'mesh_sampling': mesh_sampling,
            'min_size': mesh_min,
            'max_size': mesh_max
        })

    def fine_mesh_in_rectangle(self, x_min, y_min, x_max, y_max, mesh_sampling, mesh_min, mesh_max):
        self._fine_meshes.append({
            'type': 'box',
            'x_bnds': (x_min * 1e3, x_max * 1e3),  # Convert to mm
            'y_bnds': (y_min * 1e3, y_max * 1e3),  # Convert to mm
            'mesh_sampling': mesh_sampling,
            'min_size': mesh_min,
            'max_size': mesh_max
        })

    def _prepare_simulation(self, metallic_layers, ground_plane):
        if self.meshing == 'GMSH':
            pgr = Palace_Gmsh_Renderer(self.metal_design)
            lePorts = [(cur_port['port_name'] + 'a', cur_port['portAcoords']) for cur_port in self._ports]
            lePorts += [(cur_port['port_name'] + 'b', cur_port['portBcoords']) for cur_port in self._ports]

            gmsh_render_attrs = pgr._prepare_design(metallic_layers, ground_plane, lePorts, self.user_options['fillet_resolution'], 'eigenmode_simulation')

            if self.create_files:
                self._create_directory(self.name)
                self.create_config_file(gmsh_render_attrs=gmsh_render_attrs)

                if self.mode == 'HPC':
                    self.create_batch_file()

                pgr.fine_mesh(self._fine_meshes)
                self._save_mesh_gmsh()

            if self.view_design_gmsh_gui:
                pgr.view_design_components()

    def prepare_simulation(self):
        self._prepare_simulation(self._metallic_layers, self._ground_plane)

    def _check_simulation_mode(self):
        if self.mode == "HPC":
            return self.sim_parent_directory
        elif self.mode in ["simPC", "PC"]:
            return self.sim_parent_directory
        else:
            raise Exception('Invalid simulation mode entered.')

    def _create_directory(self, directory_name):
        parent_simulation_dir = self._check_simulation_mode()
        path = os.path.join(parent_simulation_dir, directory_name)
        if not os.path.exists(path):
            os.mkdir(path)
            print(f"Directory '{directory_name}' created")

    def _save_mesh_gmsh(self):
        if self.create_files:
            parent_simulation_dir = self._check_simulation_mode()
            file_name = self.name + "/" + self.name + ".msh"
            path = os.path.join(parent_simulation_dir, file_name)
            gmsh.write(path)

    def _get_folder_prefix(self):
        return self.hpc_options["input_dir"] + self.name + "/" if self.hpc_options["input_dir"] else ""

    def set_local_output_subdir(self, name):
        self._output_subdir = str(name)
        self._output_dir = self._get_folder_prefix() + "outputFiles"
        if self._output_subdir:
            self._output_dir += "/" + self._output_subdir
        if self._sim_config:
            with open(self._sim_config, "r") as f:
                config_json = json.loads(f.read())
            config_json['Problem']['Output'] = self._output_dir
            with open(self._sim_config, "w") as f:
                json.dump(config_json, f, indent=2)
            self._output_data_dir = os.path.dirname(os.path.realpath(self._sim_config)) + "/" + self._output_dir

    def _process_ports(self, ports):
        config_ports = []
        for m, cur_port in enumerate(self._ports):
            port_name, vec_field = cur_port['port_name'], cur_port['vec_field']
            leDict = {
                "Index": m + 1,
            }
            if port_name + 'a' in ports:
                leDict['Elements'] = [
                    {
                        "Attributes": [ports[port_name + 'a']],
                        "Direction": vec_field[0]
                    },
                    {
                        "Attributes": [ports[port_name + 'b']],
                        "Direction": vec_field[1]
                    }
                ]
            else:
                leDict['Attributes'] = [ports[port_name]]
                leDict['Direction'] = vec_field

            if 'impedance_R' in cur_port:
                leDict['R'] = cur_port['impedance_R']
            if 'impedance_L' in cur_port:
                leDict['L'] = cur_port['impedance_L']
            if 'impedance_C' in cur_port:
                leDict['C'] = cur_port['impedance_C']
            config_ports.append(leDict)
        return config_ports


class PALACE_Eigenmode_Simulation(PALACE_Model):
    default_user_options = {
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
        "HPC_Parameters_JSON": ""
    }

    def __init__(self, name, metal_design, sim_parent_directory, mode, meshing, user_options={}, view_design_gmsh_gui=False, create_files=True):
        super().__init__(name, metal_design, sim_parent_directory, mode, meshing, user_options, view_design_gmsh_gui, create_files)

    def create_config_file(self, gmsh_render_attrs):
        material_air = [gmsh_render_attrs['air_box']]
        material_dielectric = [gmsh_render_attrs['dielectric']]
        PEC_metals = gmsh_render_attrs['metals']
        far_field = [gmsh_render_attrs['far_field']]
        ports = gmsh_render_attrs['ports']
        l0 = 1e-3

        dielectric = Material(self.user_options["dielectric_material"])

        config_ports = self._process_ports(ports)
        config_ports[0]["Excitation"] = True

        config = {
            "Problem": {
                "Type": "Eigenmode",
                "Verbose": 2,
                "Output": self._get_folder_prefix() + "outputFiles"
            },
            "Model": {
                "Mesh": self._get_folder_prefix() + self.name + '.msh',
                "L0": l0,
                "Refinement": {"UniformLevels": self.user_options["mesh_refinement"]},
            },
            "Domains": {
                "Materials": [
                    {"Attributes": material_air, "Permeability": 1.0, "Permittivity": 1.0, "LossTan": 0.0},
                    {"Attributes": material_dielectric, "Permeability": dielectric.permeability, "Permittivity": dielectric.permittivity, "LossTan": 1.2e-5}
                ]
            },
            "Boundaries": {
                "PEC": {"Attributes": PEC_metals},
                "LumpedPort": config_ports
            },
            "Solver": {
                "Order": self.user_options["solver_order"],
                "Eigenmode": {
                    "N": self.user_options["number_of_freqs"],
                    "Tol": self.user_options["solver_tol"],
                    "Target": self.user_options["starting_freq"],
                    "Save": self.user_options["solns_to_save"]
                },
                "Linear": {
                    "Type": "SuperLU",
                    "KSPType": "FGMRES",
                    "Tol": self.user_options["solver_tol"],
                    "MaxIts": self.user_options["solver_maxits"]
                }
            }
        }

        if self._ff_type == 'absorbing':
            config['Boundaries']['Absorbing'] = {"Attributes": far_field, "Order": 1}
        else:
            config['Boundaries']['PEC']['Attributes'] += far_field

        parent_simulation_dir = self._check_simulation_mode()
        simulation_dir = os.path.join(parent_simulation_dir, self.name)
        sim_file_name = self.name + '.json'
        file = os.path.join(simulation_dir, sim_file_name)

        with open(file, "w+") as f:
            json.dump(config, f, indent=2)

        self._sim_config = file
        self.set_local_output_subdir(self._output_subdir)


class PALACE_Capacitance_Simulation(PALACE_Model):
    default_user_options = {
        "fillet_resolution": 4,
        "mesh_refinement": 0,
        "dielectric_material": "silicon",
        "solns_to_save": 3,
        "solver_order": 2,
        "solver_tol": 1.0e-8,
        "solver_maxits": 100,
        "HPC_Parameters_JSON": ""
    }

    def __init__(self, name, metal_design, sim_parent_directory, mode, meshing, user_options={}, view_design_gmsh_gui=False, create_files=True):
        super().__init__(name, metal_design, sim_parent_directory, mode, meshing, user_options, view_design_gmsh_gui, create_files)

    def create_config_file(self, gmsh_render_attrs):
        material_air = [gmsh_render_attrs['air_box']]
        material_dielectric = [gmsh_render_attrs['dielectric']]
        far_field = [gmsh_render_attrs['far_field']]
        terminals = [{"Index": i+1, "Attributes": [value]} for i, value in enumerate(gmsh_render_attrs['metals'])]
        l0 = 1e-3

        dielectric = Material(self.user_options["dielectric_material"])

        config = {
            "Problem": {
                "Type": "Electrostatic",
                "Verbose": 2,
                "Output": self._get_folder_prefix() + "outputFiles"
            },
            "Model": {
                "Mesh": self._get_folder_prefix() + self.name + '.msh',
                "L0": l0,
                "Refinement": {"UniformLevels": self.user_options["mesh_refinement"]},
            },
            "Domains": {
                "Materials": [
                    {"Attributes": material_air, "Permeability": 1.0, "Permittivity": 1.0, "LossTan": 0.0},
                    {"Attributes": material_dielectric, "Permeability": dielectric.permeability, "Permittivity": dielectric.permittivity, "LossTan": 1.2e-5}
                ]
            },
            "Boundaries": {
                "Ground": {"Attributes": far_field},
                "Terminal": terminals,
                "Postprocessing": {"Capacitance": terminals}
            },
            "Solver": {
                "Order": self.user_options["solver_order"],
                "Electrostatic": {"Save": self.user_options["solns_to_save"]},
                "Linear": {
                    "Type": "BoomerAMG",
                    "KSPType": "CG",
                    "Tol": self.user_options["solver_tol"],
                    "MaxIts": self.user_options["solver_maxits"]
                }
            }
        }

        parent_simulation_dir = self._check_simulation_mode()
        simulation_dir = os.path.join(parent_simulation_dir, self.name)
        sim_file_name = self.name + '.json'
        file = os.path.join(simulation_dir, sim_file_name)

        with open(file, "w+") as f:
            json.dump(config, f, indent=2)

        self._sim_config = file
        self.set_local_output_subdir(self._output_subdir)


# Example usage
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
    "HPC_Parameters_JSON": "path/to/HPC_Parameters.json"
}

# Define the paths
metal_design_path = 'path/to/your/qiskit_metal_design.json'  # Update this path
sim_parent_directory = 'path/to/simulations'  # Update this path

# Load the Qiskit Metal design
metal_design = designs.DesignPlanar()
metal_design.load(metal_design_path)

# Function to setup and run the simulation
def setup_palace_simulation(simulation_type, sim_name):
    if simulation_type == 'eigenmode':
        sim = PALACE_Eigenmode_Simulation(
            name=sim_name,
            metal_design=metal_design,
            sim_parent_directory=sim_parent_directory,
            mode='HPC',
            meshing='GMSH',
            user_options=user_options,
            view_design_gmsh_gui=False,
            create_files=True
        )
    elif simulation_type == 'capacitance':
        sim = PALACE_Capacitance_Simulation(
            name=sim_name,
            metal_design=metal_design,
            sim_parent_directory=sim_parent_directory,
            mode='HPC',
            meshing='GMSH',
            user_options=user_options,
            view_design_gmsh_gui=False,
            create_files=True
        )
    else:
        raise ValueError("Unsupported simulation type. Choose 'eigenmode' or 'capacitance'.")

    # Add necessary components and ground planes
    sim.add_metallic(layer_id=1)
    sim.add_ground_plane()

    # Add in the RF ports (for eigenmode only)
    if simulation_type == 'eigenmode':
        sim.create_port_CPW_on_Launcher('LP1', 20e-3)
        sim.create_port_CPW_on_Launcher('LP2', 20e-3)

    # Fine-mesh routed paths
    sim.fine_mesh_along_path(100e-6, 'resonator1', mesh_sampling=130, mesh_min=5e-3, mesh_max=120e-3)
    sim.fine_mesh_along_path(100e-6, 'TL', mesh_sampling=130, mesh_min=7e-3, mesh_max=120e-3)

    # Fine-mesh a rectangular region
    sim.fine_mesh_in_rectangle(-0.14e-3, -1.33e-3, 0.14e-3, -1.56e-3, mesh_sampling=130, mesh_min=5e-3, mesh_max=120e-3)

    # Prepare the simulation (generates config and batch files)
    sim.prepare_simulation()

# Run the setup function
setup_palace_simulation('eigenmode', 'single_resonator_example_eigen')
setup_palace_simulation('capacitance', 'single_resonator_example_capacitance')
