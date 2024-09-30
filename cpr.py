import os
import rdflib
import sys
import shutil
import hashlib

# Namespaces
MDTO = rdflib.Namespace("http://www.nationaalarchief.nl/mdto#")

def md5_checksum(file_path):
    """Calculate MD5 checksum of a file."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def extract_filenames(metadata_directory):
    result = {}

    # Loop through all files in the specified directory
    for filename in os.listdir(metadata_directory):
        if filename.endswith(".json"):
            filepath = os.path.join(metadata_directory, filename)
            graph = rdflib.Graph()

            # Parse the JSON-LD file
            graph.parse(filepath, format="json-ld")
            
            # Query for mdto:Bestand entities
            for bestand in graph.subjects(rdflib.RDF.type, MDTO.Bestand):
                # Extract original_filename
                identificatie_node = graph.value(bestand, MDTO.identificatie)
                original_filename = str(graph.value(identificatie_node, MDTO.identificatieKenmerk))

                # Extract hash
                checksum_node = graph.value(bestand, MDTO.checksum)
                checksum_value = str(graph.value(checksum_node, MDTO.checksumWaarde))
                checksum_date = str(graph.value(checksum_node, MDTO.checksumDatum))
                
                # Extract the filename part from mdto:URLBestand
                file_url = graph.value(bestand, MDTO.URLBestand)
                if file_url:
                    destination_filename = os.path.basename(str(file_url))
                    # Add to the result dictionary
                    if original_filename and destination_filename:
                        result[original_filename] = {
                            "destination": destination_filename,
                            "checksum": checksum_value
                        }

    return result

def copy_and_verify_files(file_info, file_source_directory, file_destination_directory):
    for original_filename, data in file_info.items():
        source_file = os.path.join(file_source_directory, original_filename)
        destination_file = os.path.join(file_destination_directory, data['destination'])

        # Copy file from source to destination
        shutil.copy2(source_file, destination_file)
        print(f"Copied {original_filename} to {destination_file}")

        # Verify the checksum
        calculated_checksum = md5_checksum(destination_file)
        if calculated_checksum == data['checksum']:
            print(f"Checksum verified for {destination_file}")
        else:
            print(f"Checksum mismatch for {destination_file}. Expected {data['checksum']}, but got {calculated_checksum}.")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python script.py <metadata_directory> <file_source_directory> <file_destination_directory>")
    else:
        metadata_directory = sys.argv[1]
        file_source_directory = sys.argv[2]
        file_destination_directory = sys.argv[3]

        # Check if all directories exist
        if not os.path.isdir(metadata_directory):
            print(f"Error: Metadata directory '{metadata_directory}' does not exist.")
            sys.exit(1)
        if not os.path.isdir(file_source_directory):
            print(f"Error: File source directory '{file_source_directory}' does not exist.")
            sys.exit(1)
        if not os.path.isdir(file_destination_directory):
            print(f"Error: File destination directory '{file_destination_directory}' does not exist.")
            sys.exit(1)

        # Extract filenames and checksums from JSON-LD files
        result_dict = extract_filenames(metadata_directory)
        
        # Copy files and verify checksum
        copy_and_verify_files(result_dict, file_source_directory, file_destination_directory)
