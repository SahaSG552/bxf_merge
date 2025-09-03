import contextlib
import tkinter as tk
from tkinter.filedialog import askopenfilenames, askdirectory
import os
import sys
from io import StringIO
import json

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
<parameters>
<parameter name="testmode">
<value xsi:type="xs:boolean" xmlns:xs="http://www.w3.org/2001/XMLSchema">false</value>
</parameter>
<parameter name="converterVersion">
<value xsi:type="xs:string" xmlns:xs="http://www.w3.org/2001/XMLSchema">1.3.0</value>
</parameter>
<parameter name="snippetPath">
<value xsi:type="xs:string" xmlns:xs="http://www.w3.org/2001/XMLSchema">PAI_ProductMasterPool\\Machinings\\V2.4\\</value>
</parameter>
</parameters>
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

CONFIG_FILE = "config.json"


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}


def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def process_bxf_files(bxf_paths, order_name, order_path):
    new_bxf_path = os.path.join(order_path, f"-{order_name} ({len(bxf_paths)}).bxf2")

    # combine info from files
    machinings = []
    partlinks = []
    parts = []
    offset = 150
    move_x = [0.0]
    zero_x = [0.0]
    for i, bxf_path in enumerate(bxf_paths):
        machining = []
        partlink = []
        part = []
        with open(bxf_path, "r", encoding="utf-8") as bxf:
            part_flag = 0
            for line in bxf:
                if "</part>" in line:
                    part.append(line.rstrip("\n"))
                    break
                if "<machining " in line and 'id="VERT_5.0x9.3"' not in line:
                    machining.append(line.rstrip("\n"))
                if "<partLink " in line:
                    partlink.append(line.rstrip("\n"))
                if "<extent>" in line:
                    x, y, z = map(
                        float,
                        (line.lstrip("<extent>")).rstrip("</extent>\n").split(" "),
                    )
                    move_x.append(x + offset)
                    zero_x.append(sum(move_x))
                if "<part " in line:
                    part_flag = 1
                if part_flag:
                    part.append(line.rstrip("\n"))

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
            elif "PARTLINKS" in line:
                new_bxf.write("\n".join(partlinks) + "\n")
            elif "PARTS" in line:
                new_bxf.write("\n".join(parts) + "\n")
            elif "ORDERNAME" in line:
                new_bxf.write(line.replace("ORDERNAME", order_name))
            else:
                new_bxf.write(line)

    os.startfile(order_path)


def select_files(initial_dir):
    root = tk.Tk()
    root.withdraw()
    return askopenfilenames(
        parent=root,
        initialdir=initial_dir,
        title="Choose bxf2 files",
        filetypes=[("BXF2", "*.bxf2")],
    )


def select_directory():
    root = tk.Tk()
    root.withdraw()
    return askdirectory(
        parent=root,
        title="Select orders folder",
        initialdir=r"E:\Работа\РАБОЧИЕ ПРОЕКТЫ\bazis_import\ORD",
    )


def input_order_number(parent):
    dialog = tk.Toplevel(parent)
    dialog.title("Enter Order Number")
    dialog.geometry("300x100")
    dialog.resizable(False, False)

    tk.Label(dialog, text="Enter order number (e.g., 1234):").pack(pady=10)
    entry = tk.Entry(dialog)
    entry.pack(pady=5)

    result = []

    def on_submit():
        result.append(entry.get())
        dialog.destroy()

    tk.Button(dialog, text="OK", command=on_submit).pack(pady=5)
    dialog.transient(parent)
    dialog.grab_set()
    parent.wait_window(dialog)
    return result[0] if result else ""


def main():
    config = load_config()

    # If config exists and has valid settings, run without GUI
    if config.get("mode") and os.path.exists(config.get("path", "")):
        if config["mode"] == "select_files":
            with contextlib.suppress(IndexError):
                bxf_paths = select_files(config["path"])
                if bxf_paths:
                    order_name = os.path.basename(os.path.dirname(bxf_paths[0]))
                    order_path = os.path.dirname(bxf_paths[0])
                    process_bxf_files(bxf_paths, order_name, order_path)
                    save_config({"mode": "select_files", "path": order_path})
        elif config["mode"] == "standard_path":
            order_number = input_order_number(tk.Tk())
            if order_number:
                order_path = os.path.join(config["path"], order_number)
                bxf_paths = [
                    os.path.join(order_path, f)
                    for f in os.listdir(order_path)
                    if f.lower().endswith(".bxf2")
                ]
                if bxf_paths:
                    process_bxf_files(bxf_paths, order_number, order_path)
        return

    # Create GUI
    root = tk.Tk()
    root.title("BXF Merger Settings")
    root.geometry("400x200")
    root.resizable(False, False)

    mode_var = tk.StringVar(value="select_files")
    selected_path = tk.StringVar(value=r"E:\Работа\РАБОЧИЕ ПРОЕКТЫ\bazis_import\ORD")

    tk.Radiobutton(
        root, text="Выбирать путь", variable=mode_var, value="select_files"
    ).pack(anchor="w", padx=10, pady=5)

    frame = tk.Frame(root)
    frame.pack(anchor="w", padx=10, pady=5)
    tk.Radiobutton(
        frame, text="Стандартный путь", variable=mode_var, value="standard_path"
    ).pack(side="left")
    tk.Label(frame, textvariable=selected_path, width=30).pack(side="left", padx=5)
    tk.Button(
        frame, text="...", command=lambda: selected_path.set(select_directory())
    ).pack(side="left")

    def save_settings():
        config = {"mode": mode_var.get(), "path": selected_path.get()}
        save_config(config)
        root.destroy()

        if mode_var.get() == "select_files":
            with contextlib.suppress(IndexError):
                bxf_paths = select_files(selected_path.get())
                if bxf_paths:
                    order_name = os.path.basename(os.path.dirname(bxf_paths[0]))
                    order_path = os.path.dirname(bxf_paths[0])
                    process_bxf_files(bxf_paths, order_name, order_path)
        elif mode_var.get() == "standard_path":
            order_number = input_order_number(tk.Tk())
            if order_number:
                order_path = os.path.join(selected_path.get(), order_number)
                bxf_paths = [
                    os.path.join(order_path, f)
                    for f in os.listdir(order_path)
                    if f.lower().endswith(".bxf2")
                ]
                if bxf_paths:
                    process_bxf_files(bxf_paths, order_number, order_path)

    tk.Button(root, text="Сохранить настройки", command=save_settings).pack(pady=20)

    root.mainloop()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        order_name = sys.argv[1]
        base_path = r"E:\Работа\РАБОЧИЕ ПРОЕКТЫ\bazis_import\ORD"
        order_path = os.path.join(base_path, order_name)
        if os.path.exists(order_path):
            bxf_paths = [
                os.path.join(order_path, f)
                for f in os.listdir(order_path)
                if f.lower().endswith(".bxf2")
            ]
            if bxf_paths:
                process_bxf_files(bxf_paths, order_name, order_path)
    else:
        main()
