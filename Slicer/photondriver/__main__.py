from pathlib import Path
import argparse
import photondriver


filepath = Path(__file__).parent / "../dot-photon-files/10-cube.photon"

print("Sending the file '{}' to the printer".format(filepath))
photondriver.send_file(filepath)
