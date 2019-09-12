import re
from enum import Enum


class Command(Enum):
    FINISH = 0
    SET_LASER_POSITION = 1
    LASER = 2
    RAISE_LAYER = 3


def parse_file(contents):
    # Extract header
    header = re.search(r':HEADER:(.+):END HEADER:', contents, re.DOTALL).group(1)
    protocol_version = re.search(r'protocol-version: "(.+)";', header).group(1)
    estimated_time = re.search(r'estimated-time: (.+);', header).group(1)
    model_name = re.search(r'model-name: "(.+)";', header).group(1)
    layer_height = float(re.search(r'layer-height: (.+);', header).group(1))
    # print("Protocol version: {}\nEstimated Time: {}\nModel Name: {}\nLayer Height: {}".format(protocol_version,
    #                                                                                          estimated_time,
    #                                                                                          model_name,
    #                                                                                          layer_height))

    # Extract body
    body = re.search(r':BODY:(.+):END BODY:', contents, re.DOTALL).group(1)

    # Extract setup
    setup = re.search(r':SETUP:(.+):END SETUP:', body, re.DOTALL).group(1)

    # Extract layers
    layers = re.findall(r':LAYER:(.*?):END LAYER:', body, re.DOTALL)

    # Extract teardown
    complete = re.search(r':COMPLETE:(.+):END COMPLETE:', body, re.DOTALL).group(1)

    # Parse text into commands
    commands = _parse_layer(setup)
    for layer in layers:
        # Add a raise layer command at the start of each new layer
        new_layer_command = (Command.RAISE_LAYER, [1])
        commands.append(new_layer_command)

        # Commands to draw layer
        commands = commands + _parse_layer(layer)
    commands = commands + _parse_layer(complete)

    return commands, (protocol_version, estimated_time, model_name, layer_height)


def _parse_layer(layer_instructions):
    command_list = []
    layer_instructions = layer_instructions.replace(';', '')
    for line in layer_instructions.splitlines():
        instruction = line.split(" ")

        if instruction[0] == "SET_LASER_POSITION:":
            command = (Command.SET_LASER_POSITION, [float(instruction[1]), float(instruction[2])])
            command_list.append(command)
        elif instruction[0] == "LASER:":
            if instruction[1] == "ON":
                command = (Command.LASER, [True])
                command_list.append(command)
            elif instruction[1] == "OFF":
                command = (Command.LASER, [False])
                command_list.append(command)

    return command_list
