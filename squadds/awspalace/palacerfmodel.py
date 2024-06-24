# This code defines a class called PALACE_Model_RF_Base that inherits from another class called PALACE_Model. 
# Within the PALACE_Model_RF_Base class, there is a method called _prepare_simulation which sets up a simulation based on the provided parameters metallic_layers and ground_plane.
# The code first checks the value of self.meshing to determine the type of simulation to perform. If it is set to 'GMSH', the code proceeds with GMSH simulation. 
# It creates an instance of the Palace_Gmsh_Renderer class and prepares the ports for the simulation. 
# It then converts the provided shapely geometries to Gmsh geometries using the _prepare_design method of the Palace_Gmsh_Renderer class. 
# If the create_files flag is set to True, it creates a directory to store simulation files, creates a config file using the create_config_file method, and performs a fine mesh using the fine_mesh method of the Palace_Gmsh_Renderer class. 
# Finally, it saves the mesh using the _save_mesh_gmsh method.
# If self.meshing is set to 'COMSOL', the code proceeds with COMSOL simulation. 
# It initializes the COMSOL engine and creates an instance of the COMSOL_Model class. It then creates a COMSOL RF simulation object and initializes the model with the provided parameters. 
# The code adds metallic layers and ground planes to the model. It assigns ports based on the type of port specified. It performs fine meshing based on the provided parameters. 
# The model is built using the build_geom_mater_elec_mesh method. 
# If the create_files flag is set to True, it creates a directory to store simulation files, creates a config file using the create_config_file method, and creates a batch file if the mode is set to 'HPC'. 
# Finally, it saves the mesh using the _save_mesh_comsol method.
# If any exception occurs during the simulation process, the code saves the COMSOL model with an error message and raises an assertion error.
# Overall, this code sets up and performs either a GMSH or COMSOL simulation based on the provided parameters, prepares the necessary files and directories, and saves the simulation results.

from palacemodel import PALACE_Model
from GMeshRenderer import Palace_Gmsh_Renderer

class PALACE_Model_RF_Base(PALACE_Model):
    def _prepare_simulation(self, metallic_layers, ground_plane):
        '''set-up the simulation'''
        
        if self.meshing == 'GMSH':

            #Create the gmsh renderer to convert qiskit metal geomentry to gmsh geometry
            pgr = Palace_Gmsh_Renderer(self.metal_design)

            #Prepare the ports...
            assert len(self._ports) > 0, "There must be at least one port in the RF simulation - do so via the create_port_CPW_on_Launcher or create_port_CPW_on_Route function."
            lePorts = []
            for cur_port in self._ports:
                lePorts += [(cur_port['port_name'] + 'a', cur_port['portAcoords'])]
                lePorts += [(cur_port['port_name'] + 'b', cur_port['portBcoords'])]

            #prepare design by converting shapely geometries to Gmsh geometries
            gmsh_render_attrs = pgr._prepare_design(metallic_layers, ground_plane, lePorts, options['fillet_resolution'], 'eigenmode_simulation')

            if self.create_files == True:
                #create directory to store simulation files
                self._create_directory(self.name)

                #create config file
                self.create_config_file(gmsh_render_attrs = gmsh_render_attrs)

                #create batch file - QUESTIONABLE
                if self.mode == 'HPC':
                    self.create_batch_file()
                
                #create mesh
                # pgr._intelligent_mesh('eigenmode_simulation', 
                #                 min_size = self.user_options['mesh_min'], 
                #                 max_size = self.user_options['mesh_max'], 
                #                 mesh_sampling = self.user_options['mesh_sampling'])
                
                pgr.fine_mesh(self._fine_meshes)

                self._save_mesh_gmsh()

            if self.view_design_gmsh_gui == True:
                #plot design in gmsh gui
                pgr.view_design_components()