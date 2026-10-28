import json, sys
sys.path.insert(0, "/Users/zhangyang/Downloads/fastfill-v4/related work code/baselines/adapters")
import directlayout_run as D
dl = D.load_directlayout(D.RW / "DirectLayout-main")
rows = [json.loads(l) for l in open("/Users/zhangyang/Downloads/fastfill-v4/test300/rows.jsonl")]
row = rows[45]; info = D.room_info(row)
good = [D.css_line(o["id"], D.to_theirs(o["target_size_local_m"], o, info["x0"], info["y0"], info["z0"])) for o in row["target"]["objects"]]
fixed = [f["id"] for f in info["fixed"]]
def chk(name, lines):
    f, fb = D.parse_layout("\n".join(lines), row, dl, fixed)
    lay, miss = D.to_ours(f, row, info)
    complete = not (miss or f.duplicates or f.invalid or f.extra)
    print(f"{name:34s} complete={complete!s:5s} missing={miss} dup={f.duplicates} invalid={f.invalid} extra={f.extra} fixed_out={f.fixed_output} fallback={fb}")
chk("clean", good)
chk("reordered fields / spacing", [good[0], "obj_0001   {width: 40px;length: 50px; height:45px; center_z: 22px; center_x: 300px; center_y: 200px; orientation: 90 degrees;}"])
chk("numbered list + label", ["1. " + good[0].replace(" {", " (chair) {"), good[1]])
chk("duplicate, other format", good + [good[0].replace(" {", "  (again) {").replace("; ", ";")])
chk("no orientation", [good[0], good[1].replace(" orientation: 0 degrees;", "").split(" orientation")[0] + "}"])
chk("metres instead of px", [good[0], good[1].replace("px", "m")])
chk("extra unknown id", good + ["obj_0099 {length: 10px; width: 10px; height: 10px; center_x: 1px; center_y: 1px; center_z: 5px; orientation: 0 degrees;}"])
chk("extra non-obj name", good + ["bed_1 {length: 10px; width: 10px; height: 10px; center_x: 1px; center_y: 1px; center_z: 5px; orientation: 0 degrees;}"])
chk("fixed echoed", good + [D.css_line(info["fixed"][0]["id"], info["fixed"][0])])
chk("zero size", [good[0], good[1].replace("height: ", "height: 0px; h0: ").split("; h0")[0] + good[1].split("height:")[1].split(";",1)[1]])
chk("one missing", good[:1])
chk("css comment inside", [good[0], good[1].replace(" orientation", " /* facing the bed */ orientation")])
