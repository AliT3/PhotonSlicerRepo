from pathlib import Path
import sys
import argparse
from visualiser import visualiser

# Define and process arguments
parser = argparse.ArgumentParser(description='Tool for visualising .photon files')
parser.add_argument("-f", "--filename", help="The name of the file you want to visualise "
                                             "e.g ../dot-photon-files/50-cube.photon", required=False)
args = parser.parse_args()

# Startup message
print("")
print("--Welcome, Running the .photon file visualiser--")
print("")

# Check whether a filename was supplied
if args.filename:
    filepath = Path(__file__).parent / args.filename

    print("Trying to visualise output of file at ({})".format(filepath))

    file = filepath.open(mode='r')
    contents = file.read()
    visualiser.visualise(contents)

# Otherwise read from standard in
else:
    print("Trying to visualise the file passed via standard input")
    contents = sys.stdin.readlines()
    contents = ''.join(contents)
    visualiser.visualise(contents)
