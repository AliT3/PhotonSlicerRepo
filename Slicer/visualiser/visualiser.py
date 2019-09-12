# Package for visualising the output of .photon files
import math
import turtle
from helpers.photonfileparser import Command
from helpers.photonfileparser import parse_file as parse_photon_file


def visualise(contents):
    # Receives the contents of a text file
    commands, metadata = parse_photon_file(contents)
    _visualise_commands(commands, metadata)


def _visualise_commands(command_list, metadata):
    # Extract metadata
    protocol_version, estimated_time, model_name, layer_height = metadata

    # Setup screen
    screen = turtle.Screen()
    screen.colormode(255)

    # Write meta data text
    text_writer = turtle.Turtle()
    text_writer.penup()
    text_writer.setpos(-screen.window_width()/2+20, screen.window_height()/2-60)
    text_writer.write("Protocol Version: {}\n"
                      "Model Name: {}\n"
                      "Layer Height: {}".format(protocol_version, model_name, layer_height), True, align="left")
    text_writer.hideturtle()

    # Top down laser
    top_down_laser = turtle.Turtle()

    # Side view laser
    side_view_laser = turtle.Turtle()
    side_view_laser.pensize(2)
    layer_index = 0
    colours = [(110, 0, 0), (220, 0, 0), (180, 0, 0), (220, 0, 0), (230, 50, 50),
               (160, 0, 0), (110, 0, 0), (180, 0, 0), (210, 0, 0), (190, 0, 0)]

    # Iterate over each command sequentially
    for command, args in command_list:
        if command == Command.SET_LASER_POSITION:
            x, y = args

            # Top down visualisation
            print("Setting position to: {x} {y}".format(x=x, y=y))
            top_down_laser.setpos(x-100, y)

            # Side view laser visualisation
            angle = math.pi/4
            x_rotated = x * math.cos(angle) - y * math.sin(angle)
            y_rotated = x * math.sin(angle) + y * math.cos(angle)
            screen.tracer(False)
            side_view_laser.setpos(x_rotated*1+150, (y_rotated*0.5 + layer_index*layer_height)*1)
            screen.tracer(True)

        elif command == Command.RAISE_LAYER:
            z = args[0]

            # Top down visualisation
            print("Raising layer by {z}".format(z=z))
            top_down_laser.clear()

            # Side view laser visualisation
            layer_index += z
            side_view_laser.pencolor(colours[layer_index % len(colours)])

        elif command == Command.LASER:
            turn_on = args[0]
            if turn_on:
                print("Turning laser on")
                top_down_laser.pendown()
                side_view_laser.pendown()
            else:
                print("Turning laser off")
                top_down_laser.penup()
                side_view_laser.penup()

    screen.exitonclick()
