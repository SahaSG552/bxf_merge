import contextlib
import tkinter as tk
import os
import sys
from io import StringIO
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


# Встроенное содержимое Template.txt
TEMPLATE_CONTENT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<bxf xsi:schemaLocation="http://www.blum.com/BXF2 http://www.blum.com/BXF2/bxf2.xsd" xmlns="http://www.blum.com/bxf2" xmlns:ns2="http://www.blum.com/bxf2/bxf2snp" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<head>
<version>2.3</version>
<date>23.12.2022 13:56:05</date>
<author>PIDOR</author>
<copyright></copyright>
<unit meter="0.001" name="meter"/>
<angularUnit>degree</angularUnit>
<country>RU</country>
<language>ru</language>
<s>
<parameter name="testmode">
<value xsi:type="xs:boolean" xmlns:xs="http://www.w3.org/2001/XMLSchema">false</value>
</parameter
<parameter name="converterVersion">
<value xsi:type="xs:string" xmlns:xs="http://www.w3.org/2001/XMLSchema">1.3.0</value>
</parameter
<parameter name="snippetPath">
<value xsi:type="xs:string" xmlns:xs="http://www.w3.org/2001/XMLSchema">PAI_ProductMasterPool\\Machinings\\V2.4\\</value>
</parameter
</s>
</head>
<scene>
<nodes>
<node>
<cabinetLinks>
<cabinetLink referenceId="ORDERNAME">
</cabinetLink>
</cabinetLinks>
</node>
</nodes>
</scene>
<library>
<machinings>
MACHININGS
</machinings>
<cabinets>
<cabinet id="ORDERNAME" uid="1">
<partLinks>
PARTLINKS
</partLinks>
</cabinet>
</cabinets>
<parts>
PARTS
</parts>
</library>
</bxf>"""


def main():
    if len(sys.argv) > 1:
        order_name = sys.argv[1]
        base_path = r"E:\Работа\РАБОЧИЕ ПРОЕКТЫ\bazis_import\ORD"
        order_path = os.path.join(base_path, order_name)

        if not os.path.exists(order_path):
            print(f"Folder not found: {order_path}")
            return

        bxf_paths = [
            os.path.join(order_path, f)
            for f in os.listdir(order_path)
            if f.lower().endswith(".bxf2")
        ]

        if not bxf_paths:
            print(f"No .bxf2 files found in {order_path}")
            return
    else:
        # if user cancel to open files, don't raise an error
        with contextlib.suppress(IndexError):
            bxf_paths = open_bxf_files()
            if not bxf_paths:
                return

            order_name = os.path.basename(os.path.dirname(bxf_paths[0]))
            order_path = os.path.dirname(bxf_paths[0])

    new_bxf_path = os.path.join(order_path, f"-{order_name} ({len(bxf_paths)}).bxf2")

    # combine info from files
    machinings = []
    partlinks = []
    parts = []
    offset = 150

    move_x = [0.0]  # move every detail + 150 mm next to previous along x axis
    zero_x = [0.0]  # calculate x coordinate of each detail after moving
    for i, bxf_path in enumerate(bxf_paths):
        machining = []
        partlink = []
        part = []
        with open(bxf_path, "r", encoding="utf-8") as bxf:
            part_flag = 0  # flag when to start record part information
            for line in bxf:
                if "</part>" in line:
                    part.append(line.rstrip("\n"))
                    break  # no need to read the rest
                # collecting machining operations of part
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
                        (line.lstrip("<extent>")).rstrip("</extent>\n").split(" "),
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

    # Use in-memory template
    template = StringIO(TEMPLATE_CONTENT)
    with open(new_bxf_path, "w", encoding="utf-8") as new_bxf:
        for line in template:
            if "MACHININGS" in line and machinings:
                new_bxf.write("\n".join(machinings) + "\n")
                continue
            if "PARTLINKS" in line:
                new_bxf.write("\n".join(partlinks) + "\n")
                continue
            if "PARTS" in line:
                new_bxf.write("\n".join(parts) + "\n")
                continue
            if "ORDERNAME" in line:
                line = line.replace("ORDERNAME", order_name)
            new_bxf.write(line)

    os.startfile(order_path)  # open destination folder after processing


if __name__ == "__main__":
    main()
