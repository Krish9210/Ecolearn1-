import os
import shutil

def rename_files(directory):
    # Change to the target directory
    os.chdir(directory)
    
    # List all files in the directory
    for filename in os.listdir('.'):
        if '-' in filename and filename.endswith('.py'):
            # Create new filename with underscores
            new_name = filename.replace('-', '_')
            
            # Skip if the file is already in the correct format
            if new_name == filename:
                continue
                
            print(f"Renaming {filename} to {new_name}")
            
            # Rename the file
            try:
                shutil.move(filename, new_name)
                print(f"Successfully renamed {filename} to {new_name}")
            except Exception as e:
                print(f"Error renaming {filename}: {e}")

if __name__ == "__main__":
    # Rename files in the services directory
    services_dir = os.path.join(os.path.dirname(__file__), 'services')
    if os.path.exists(services_dir):
        print(f"Renaming files in {services_dir}")
        rename_files(services_dir)
    
    # Rename files in the utils directory
    utils_dir = os.path.join(os.path.dirname(__file__), 'utils')
    if os.path.exists(utils_dir):
        print(f"\nRenaming files in {utils_dir}")
        rename_files(utils_dir)
    
    print("\nFile renaming completed!")
