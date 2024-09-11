import os
import time
import shutil
import glob
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Deletes old temporary files'

    def handle(self, *args, **kwargs):
        while True:
            try:
                now = time.time()
                tmp_dirs = glob.glob('/tmp/*')
                for temp_dir in tmp_dirs:
                    if os.path.isdir(temp_dir) and (now - os.path.getctime(temp_dir)) > 86400:  # 86400 seconds = 24 hours
                        try:
                            shutil.rmtree(temp_dir)
                            self.stdout.write(f"Automatically deleted old temporary directory: {temp_dir}")
                        except Exception as e:
                            self.stdout.write(f"Error deleting {temp_dir}: {str(e)}")

                var_tmp_dirs = glob.glob('/var/tmp/*')
                for temp_dir in var_tmp_dirs:
                    if os.path.isdir(temp_dir) and (now - os.path.getctime(temp_dir)) > 86400:
                        try:
                            shutil.rmtree(temp_dir)
                            self.stdout.write(f"Automatically deleted old temporary directory: {temp_dir}")
                        except Exception as e:
                            self.stdout.write(f"Error deleting {temp_dir}: {str(e)}")
            except Exception as e:
                self.stdout.write(f"Error during automatic deletion of temporary files: {str(e)}")

            time.sleep(3600)  # Check every hour

