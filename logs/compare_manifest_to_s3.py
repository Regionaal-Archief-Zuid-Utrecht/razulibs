# load two logs text files generated from delete_objects_from_manifest method in edepot.py and compare line-by-line

file_a = "logs/objects_in_manifest.txt"
file_b = "logs/s3_objects_found_from_manifest.txt"

def load_list(path):
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

list_a = load_list(file_a)
list_b = load_list(file_b)

set_a = set(list_a)
set_b = set(list_b)

only_in_a = sorted(set_a - set_b)
only_in_b = sorted(set_b - set_a)

print("Items only in manifest:")
for x in only_in_a:
    print(x)

print("\nItems only in s3::")
for x in only_in_b:
    print(x)
