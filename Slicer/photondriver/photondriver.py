import serial
from pathlib import Path
from helpers.photonfileparser import Command
from helpers.photonfileparser import parse_file as parse_photon_file


# Tip use python -m serial.tools.list_ports to check which ports are available and in use

def send_file(filepath):

    filepath = Path("C:/Users/Alistair/Documents/Dark Materials/SLA1/Slicer/dot-photon-files/50-cube.photon")

    # Read text from file
    text = filepath.read_text()

    # Standardise line endings
    text = text.replace("\r", "")

    compressed_text = _compress_file(text)
    _send_file(compressed_text)


# Converts a plaintext file into a binary stream
# Format: [<instruction>:1 byte | <arg 1>:2 bytes | <arg 2>: 2 bytes]
# Arguments are converted to 2 decimal places and then mapped onto the range -10,000 -> +10,000
# Meaning that the print area has a resolution of 20,000 x 20,000 and max model size of 100 x 100
def _compress_file(text):

    compressed_commands = []
    commands, metadata = parse_photon_file(text)

    # Extract metadata - currently not included in compressed file
    # protocol_version, estimated_time, model_name, layer_height = metadata

    # Compress commands
    for command, args in commands:
        if command == Command.SET_LASER_POSITION:
            x, y = args

            # Compress arguments
            if x < -100 or x > 100 or y < -100 or y > 100:
                print("ERROR: file too large")
            x = int(x*100)+10000
            y = int(y*100)+10000

            # Convert arguments into 2 separate bytes
            x1, x2 = _int_to_2_bytes(x)
            y1, y2 = _int_to_2_bytes(y)

            compressed_command = [Command.SET_LASER_POSITION.value, x1, x2, y1, y2]
            compressed_commands.extend(compressed_command)

        elif command == Command.RAISE_LAYER:
            z = args[0]

            if z != 1:
                print("WARNING, z layer raise amount is not one!")

            compressed_command = [Command.RAISE_LAYER.value, 0, z, 0, 0]
            compressed_commands.extend(compressed_command)

        elif command == Command.LASER:
            turn_on = args[0]
            value = 0
            if turn_on:
                value = 1
            compressed_command = [Command.LASER.value, 0, value, 0, 0]
            compressed_commands.extend(compressed_command)

    # Add the finish command
    compressed_commands.extend([Command.FINISH.value, 0, 0, 0, 0])

    return bytes(compressed_commands)


def _int_to_2_bytes(x):

    x1 = x >> 8
    x2 = x - (x1 << 8)

    return x1, x2


def _send_file(file_data):

    # Open the serial port
    ser = serial.Serial('COM4', 9600)
    print("Connected to serial port: {}".format(ser.name))

    # Wait for printer to be free (very primitive approach)
    while True:
        line = ser.readline()

        # Convert line from byte literal to string and remove end-line characters
        line = line.decode("utf-8").rstrip()
        print(line)

        if line == "Printer Free":
            print("Printer Free!!")
            break

    # Write the file to the serial channel one instruction at a time
    x = 0
    while x < 1 :#temp
        #x = 1
        byte_data = iter(file_data)
        for b in byte_data:
            # Prepare instruction
            instruction = bytes([b, next(byte_data), next(byte_data), next(byte_data), next(byte_data)])

            # Send instruction
            ser.write(instruction)
            print(instruction)

            # Listen for next instruction request
            line = ser.readline()
            print(line)

    # Close the serial port
    ser.close()
