import contextlib
import tkinter as tk
from tkinter.filedialog import askopenfilenames, askdirectory
from tkinter import messagebox
import os
import sys
from io import StringIO
import json

# Встроенное содержимое Template.txt
TEMPLATE_CONTENT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<bxf xsi:schemaLocation="http://www.blum.com/BXF2 http://www.blum.com/BXF2/bxf2.xsd" xmlns="http://www.blum.com/bxf2" xmlns:ns2="http://www.blum.com/bxf2/bxf2snp" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<head>
<version>2.3</version>
<date>04.09.2025 13:22:24</date>
<author></author>
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
<value xsi:type="xs:string" xmlns:xs="http://www.w3.org/2001/XMLSchema">PAI_ProductMasterPool\Machinings\V2.4\</value>
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

    x, y, z = 0.0, 0.0, 0.0  # detail dimensions
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

    # Use in-memory template
    template = StringIO(TEMPLATE_CONTENT)
    with open(new_bxf_path, "w", encoding="utf-8") as new_bxf:
        line = template.readline()
        while line:
            line = template.readline()
            if "MACHININGS" in line and machinings:
                line = "\n".join(machinings)
            if "PARTLINKS" in line:
                line = "\n".join(partlinks)
            if "PARTS" in line:
                line = "\n".join(parts)
            if "ORDERNAME" in line:
                line = line.replace("ORDERNAME", order_name)
            new_bxf.write(line)

    os.startfile(order_path)


def select_files(initial_dir):
    root = tk.Tk()
    root.withdraw()
    files = askopenfilenames(
        initialdir=initial_dir,
        title="Choose bxf2 files",
        filetypes=[("BXF2", "*.bxf2")],
    )
    root.destroy()
    return files


def select_directory():
    root = tk.Tk()
    root.withdraw()
    directory = askdirectory(
        title="Select orders folder",
        initialdir=r"E:\Работа\РАБОЧИЕ ПРОЕКТЫ\bazis_import\ORD",
    )
    root.destroy()
    return directory


def input_order_number(parent, base_path):
    dialog = tk.Tk() if parent is None else tk.Toplevel(parent)
    dialog.title("Enter Order Number")
    dialog.geometry("300x150")
    dialog.resizable(False, False)

    tk.Label(dialog, text="Enter order number (e.g., 1234):").pack(pady=10)
    entry = tk.Entry(dialog)
    entry.pack(pady=5)
    entry.focus_set()

    error_label = tk.Label(dialog, text="", fg="red")
    error_label.pack(pady=5)

    result = []

    def on_submit():
        order_number = entry.get()
        if not order_number:
            dialog.destroy()
            return

        order_path = os.path.join(base_path, order_number)
        if not os.path.exists(order_path):
            error_label.config(text="Папка не найдена. Попробуйте снова.")
            return

        bxf_paths = [
            os.path.join(order_path, f)
            for f in os.listdir(order_path)
            if f.lower().endswith(".bxf2") and not f.lower().startswith("-")
        ]
        if not bxf_paths:
            error_label.config(text="Файлы .bxf2 не найдены. Попробуйте снова.")
            return

        result.append(order_number)
        dialog.destroy()

    def on_cancel():
        dialog.destroy()

    frame = tk.Frame(dialog)
    frame.pack(pady=5)
    tk.Button(frame, text="Cancel", command=on_cancel).pack(side="left", padx=10)
    tk.Button(frame, text="OK", command=on_submit).pack(side="right", padx=10)
    dialog.bind("<Return>", lambda event: on_submit())

    if parent:
        dialog.transient(parent)
        dialog.grab_set()
        parent.wait_window(dialog)
    else:
        dialog.mainloop()

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
            order_number = input_order_number(None, config["path"])
            if order_number:
                order_path = os.path.join(config["path"], order_number)
                bxf_paths = [
                    os.path.join(order_path, f)
                    for f in os.listdir(order_path)
                    if f.lower().endswith(".bxf2") and not f.lower().startswith("-")
                ]
                process_bxf_files(bxf_paths, order_number, order_path)
        sys.exit(0)
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
        if not os.path.exists(selected_path.get()):
            messagebox.showerror("Ошибка", f"Папка {selected_path.get()} не найдена")
            return
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
            order_number = input_order_number(None, selected_path.get())
            if order_number:
                order_path = os.path.join(selected_path.get(), order_number)
                bxf_paths = [
                    os.path.join(order_path, f)
                    for f in os.listdir(order_path)
                    if f.lower().endswith(".bxf2") and not f.lower().startswith("-")
                ]
                process_bxf_files(bxf_paths, order_number, order_path)

    tk.Button(root, text="Сохранить настройки", command=save_settings).pack(pady=20)

    root.mainloop()
    sys.exit(0)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        order_name = sys.argv[1]
        base_path = r"E:\Работа\РАБОЧИЕ ПРОЕКТЫ\bazis_import\ORD"
        order_path = os.path.join(base_path, order_name)
        if os.path.exists(order_path):
            bxf_paths = [
                os.path.join(order_path, f)
                for f in os.listdir(order_path)
                if f.lower().endswith(".bxf2") and not f.lower().startswith("-")
            ]
            if bxf_paths:
                process_bxf_files(bxf_paths, order_name, order_path)
            else:
                root = tk.Tk()
                root.withdraw()
                messagebox.showerror("Ошибка", f"Файлы .bxf2 не найдены в {order_path}")
                root.destroy()
        else:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Ошибка", f"Папка {order_path} не найдена")
            root.destroy()
    else:
        main()
    sys.exit(0)
