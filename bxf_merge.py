import contextlib
import tkinter as tk
import os
from tkinter.filedialog import askopenfilenames


def open_bxf_files():
    root = tk.Tk()
    root.withdraw()
    return askopenfilenames(
        parent=root,
        initialdir="",
        title="Choose bxf2 files",
        filetypes=[("BXF2", "*.bxf2")],
    )


# if user cancel to open files, don't raise an error
with contextlib.suppress(IndexError):
    bxf_paths = open_bxf_files()

    order_name = bxf_paths[0].split("/")[-2]
    order_path = ("/").join((bxf_paths[0].split("/"))[:-1])
    new_bxf_path = f"{order_path}/-{order_name} ({len(bxf_paths)}).bxf2"

    # combine info from files
    machinings = []
    partlinks = []
    parts = []
    offset = 150

    x, y, z = 0, 0, 0  # detail dimensions
    move_x = [0.0]  # move every detail + 150 mm next to previous along x axis
    zero_x = [0.0]  # calculate x coordinate of each detail after moving
    for i, bxf_path in enumerate(bxf_paths):
        machining = []
        partlink = []
        part = []
        with open(bxf_path, "r", encoding="utf-8") as bxf:
            counter = 0  # counting down lines in file
            part_flag = 0  # flag when to start record part information
            line = bxf.readline()
            while "</part>" not in line:  # in this case no need to read the rest lines
                line = bxf.readline()
                # collecting machinning operations of part
                # sourcery skip: merge-nested-ifs
                if "<machining " in line:
                    # filter unnecessary machining
                    if line.find('id="VERT_5.0x9.3"') == -1:
                        machining.append(line.rstrip("\n"))
                # collecting part name
                if "<partLink " in line:
                    partlink.append(line.rstrip("\n"))
                # collecting part dimensions
                if "<extent>" in line:
                    x, y, z = map(
                        float,
                        ((line.lstrip("<extent>")).rstrip("</extent>\n")).split(" "),
                    )
                    move_x.append(x + offset)  # offset
                    # accumulate offsets to get x coordinate of part
                    zero_x.append(sum(move_x))

                # collecting multiline data about machining position
                if "<part " in line:
                    part_flag = 1
                if part_flag:
                    part.append(line.rstrip("\n"))

            # writing down zero_x coordinate to partlink
            partlink.extend(
                [
                    "<transformations>",
                    f'<transformation translation="{zero_x[i]} 0 0"/>',
                    "</transformations>",
                    "</partLink>",
                ]
            )

        machinings.extend(machining)
        machinings = list(set(machinings))
        partlinks.extend(partlink)
        parts.extend(part)

    # open template file, complete missing parts and save as new_bxf
    with open("Template.txt", "r", encoding="utf-8") as template, open(
        new_bxf_path, "w", encoding="utf-8"
    ) as new_bxf:
        line = template.readline()
        while line:
            line = template.readline()
            if "MACHININGS" in line:
                line = "\n".join(machinings)
            if "PARTLINKS" in line:
                line = "\n".join(partlinks)
            if "PARTS" in line:
                line = "\n".join(parts)
            new_bxf.write(line)
        os.startfile(order_path)  # open destination folder after processing
