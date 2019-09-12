from pathlib import Path
import argparse
import photonslicer
from visualiser import visualiser

# Define and process arguments
parser = argparse.ArgumentParser(description='Software for converting 3d stl file into a '
                                             'sliced layer by layer .photon file')
parser.add_argument("-v", "--visualise", help="Whether or not to visualise the output",
                    action="store_true", required=False)
args = parser.parse_args()

# Startup message
print("")
print("--Welcome, Executing the Photon Slicer program--")
print("")

# Run slicer
#filepath = Path(__file__).parent / "../models/single-wall-pyramid.stl"
#filepath = Path(__file__).parent / "../models/bunny.stl"
#filepath = Path(__file__).parent / "../models/cube-with-hole.stl"
#filepath = Path(__file__).parent / "../models/concave-shape.stl"
#filepath = Path(__file__).parent / "../models/concave-shape-with-holes.stl"
#filepath = Path(__file__).parent / "../models/very-irregular-shape.stl"
#filepath = Path(__file__).parent / "../models/very-irregular-shape-with-holes.stl"
#filepath = Path(__file__).parent / "../models/heart-p.stl"
filepath = Path(__file__).parent / "../models/eiffel-tower.stl"
output = photonslicer.run_slicer(str(filepath))

# Handle output
if args.visualise:
    # If the visualise flag is set then visualise
    visualiser.visualise(output)
else:
    # Otherwise just print output
    print("\nOutput:\n\n{}\n".format(output))
