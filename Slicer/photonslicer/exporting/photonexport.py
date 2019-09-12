# Package that prepares a set of layers for export to a .photon file


def convert_layers_to_photon_code(layers, layer_height):

    # -Prepare header-
    header_string = ':HEADER:\n' \
                    'protocol-version: "1.0";\n' \
                    'estimated-time: 100;\n' \
                    'model-name: "10 cube";\n' \
                    'layer-height: {layer_height};\n' \
                    ':END HEADER:'.format(layer_height=layer_height)

    # -Prepare body-
    # Prepare setup
    setup_string = ':SETUP:\nLASER: OFF;\nSET_LASER_POSITION: 0 0;\n:END SETUP:'

    # Prepare main layers code
    layers_string = ""

    # Iterate over each of the layers
    for layer in layers:

        # Create fresh instruction set
        instructions = ""

        # Iterate over each section in this layer path
        for path_section in layer:

            # Move the laser to the start position
            x, y = path_section[0]
            instructions = "{}\nSET_LASER_POSITION: {x} {y};".format(instructions, x=x, y=y)

            # Once the laser is in the start position turn on the laser
            instructions = "{}\nLASER: ON;".format(instructions)

            # Move the laser to each of the next positions
            path_section.pop(0)  # removes first element
            for point in path_section:
                x, y = point
                instructions = "{}\nSET_LASER_POSITION: {x} {y};".format(instructions, x=x, y=y)

            # Turn off the laser at the end of the print
            instructions = "{}\nLASER: OFF;".format(instructions)

        layers_string = layers_string + "\n:LAYER:{}\n:END LAYER:\n".format(instructions)

    # Prepare complete
    complete_string = ':COMPLETE:\nLASER: OFF;\nSET_LASER_POSITION: 0 0;\n:END COMPLETE:'

    body_string = ":BODY:\n{setup}\n{layers}\n{complete}\n:END BODY:".format(setup=setup_string,
                                                                             layers=layers_string,
                                                                             complete=complete_string)

    # Prepare final file
    file_string = "{header}\n\n{body}".format(header=header_string, body=body_string)
    print(file_string)
    return file_string
