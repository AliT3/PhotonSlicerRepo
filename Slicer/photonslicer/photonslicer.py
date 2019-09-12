# Main package

import exporting.photonexport as photon_export
import core.slicer as slicer


def run_slicer(filepath, layer_height=1):
    print("Running the slicer using the file at '{}' as input".format(filepath))
    layer_paths = slicer.model_to_layer_paths(filepath, layer_height)
    output_file = photon_export.convert_layers_to_photon_code(layer_paths, layer_height)
    return output_file
