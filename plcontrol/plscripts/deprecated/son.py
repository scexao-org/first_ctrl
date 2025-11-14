from datetime import datetime, timezone
import os

#STart of night, creating coupling maps
class Son(Base):
    def __init__(self, *args, **kwargs):
        super(Son, self).__init__(*args, **kwargs)
    
    def get_fits_for_coupling(list_of_fits):
        return
    
    def _default_FIRST_raw_folder(self):
        """ Explicit """
        base = "/mnt/datazpool/PL/"
        today = datetime.now(timezone.utc)
        use = base + f"{today:%Y%m%d}"+"/"
        test = base + "20250502"+"/"
        return use
    
    def define_path_for_reduction(self):
        current_path = self._default_FIRST_raw_folder()
        os.mkdir(current_path+"couplingmap", exist_ok=True)

    def move_files_if_folder_exists(source_folder, destination_folder):
        # Check if the source folder exists
        if not os.path.isdir(source_folder):
            print(f"Source folder '{source_folder}' does not exist.")
            return

        # Create destination folder if it doesn't exist
        os.makedirs(destination_folder, exist_ok=True)

        # Loop through items in the source folder
        for filename in os.listdir(source_folder):
            source_path = os.path.join(source_folder, filename)

            # Only move files (not subdirectories)
            if os.path.isfile(source_path):
                dest_path = os.path.join(destination_folder, filename)
                shutil.move(source_path, dest_path)
                print(f"Moved: {source_path} → {dest_path}")

        print("Done.")


