import sys

with open("Nova-SM3_teensyNRF-v5.2b_mp3_pro.ino", "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

with open("new_step.ino", "r", encoding="utf-8") as f:
    new_step = f.readlines()

start_idx = -1
for i, line in enumerate(lines):
    if "void step_left_right(int lorr, int xdir, int ydir)" in line:
        start_idx = i
        break

if start_idx != -1:
    end_idx = -1
    braces = 0
    in_func = False
    for i in range(start_idx, len(lines)):
        if "{" in lines[i]:
            braces += lines[i].count("{")
            in_func = True
        if "}" in lines[i]:
            braces -= lines[i].count("}")
        if in_func and braces <= 0:
            end_idx = i
            break
    
    if end_idx != -1:
        # Before doing the replacement, let's verify if there is an extra closing brace
        # We need to find the `void step_left_right` function and replace it.
        # Wait, the original code had an extra closing brace inside `step_left_right` which caused compilation error earlier.
        # So maybe `braces <= 0` will match early!
        # To avoid this, let's just use the end_idx from the previous original file.
        # But wait! We can just match the next function!
        next_func = -1
        for i in range(start_idx+1, len(lines)):
            if lines[i].startswith("void async_servo()"):
                next_func = i
                break
        
        # The line before void async_servo() is the end of step_left_right.
        # Let's search upwards from next_func to find the last `}`.
        end_idx = next_func - 1
        while end_idx > start_idx and "}" not in lines[end_idx]:
            end_idx -= 1
        
        lines = lines[:start_idx] + new_step + ["\n"] + lines[next_func:]
        with open("Nova-SM3_teensyNRF-v5.2b_mp3_pro.ino", "w", encoding="utf-8") as f:
            f.writelines(lines)
        print("Success! Replaced step_left_right. Next function is at line:", next_func)
    else:
        print("Could not find end_idx")
else:
    print("Could not find start_idx")
