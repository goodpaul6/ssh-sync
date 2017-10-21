import time, os
from paramiko import SSHClient
import argparse, scp, getpass
from scp import SCPClient

scp = None

def copy_to_remote(local_path, remote_path):
    scp.put(local_path, remote_path=remote_path, preserve_times=True, recursive=True)

def copy_from_remote(local_path, remote_path):
    scp.get(remote_path, local_path=local_path, preserve_times=True, recursive=True)

def main():
    parser = argparse.ArgumentParser(description="Tool for synchronizing changes between local filesystem and remote shell")

    parser.add_argument("-u", "--user-id", type=str, required=True, help="Your user id.")
    parser.add_argument("-r", "--remote-domain", type=str, required=True, help="Remote machine domain.")
    parser.add_argument("-w", "--wait-time", type=int, default=5, help="Number of seconds between each sync.")
    parser.add_argument("-d", "--remote-dir", type=str, required=True, help="Remote path to directory to sync.")
    parser.add_argument("-c", "--copy", action="store_true", help="Copies remote directory to current directory.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print verbose output.")

    args = parser.parse_args()

    args.password = getpass.getpass("Enter Password: ")

    print("Initializing SSH client...")

    ssh = SSHClient()
    ssh.load_system_host_keys()
    ssh.connect(args.remote_domain, username=args.user_id, password=args.password)

    print("Successfully connected to remote.")

    print("Initializing SCP client...")
    
    global scp
    scp = SCPClient(ssh.get_transport())

    print("Successfully initialized SCP client.")

    remote_dir_dir = os.path.dirname(args.remote_dir)
    local_dir = os.path.basename(args.remote_dir)

    if args.copy:
        print("Copying directory from remote...")
        copy_from_remote(".", args.remote_dir)
        print("Successfully copied directory from remote.")

    if not os.path.exists(local_dir):
        print("ERROR: No local copy exists. Invoke with '-c'.".format(local_dir))
        return

    prev_times = {}

    def run_command_file(path, dirname):
        base_cmd = "cd {}/{} && ".format(remote_dir_dir, dirname.replace('\\', '/'))

        with open(path, "r") as f:
            for line in f.readlines():
                if line.isspace(): continue

                cmd = base_cmd + line

                print("Executing '{}' on remote machine...".format(cmd.rstrip('\n')))

                _, stdout, stderr = ssh.exec_command(cmd)

                for line in stdout.readlines():
                    print(line, end='')

                for line in stderr.readlines():
                    print(line, end='')

                print("Execution finished.")

    while True:
        if args.verbose:
            print("Polling for changes...")

        for dirname, subdirnames, filenames in os.walk(local_dir):
            for filename in filenames:
                if filename.endswith(".swp"): continue

                path = os.path.join(dirname, filename)
                mod_time = os.path.getmtime(path) 
                if path in prev_times:
                    if mod_time > prev_times[path]:
                        if filename == ".command":
                            print("Detected change in command file in '{}'".format(dirname))
                            run_command_file(path, dirname)
                        else: 
                            print("Detected change in '{}', copying to remote...".format(path))
                            copy_to_remote(path, "{}/{}/{}".format(remote_dir_dir, dirname.replace("\\", "/"), filename))
                            print("Successfully copied to remote.")
                        prev_times[path] = mod_time
                else:
                    if filename == ".command":
                        print("Detected  command file in '{}'".format(dirname))
                        print("Modify this to run it.")

                    prev_times[path] = mod_time
        
        if args.verbose:
            print("Waiting...")
        time.sleep(args.wait_time)

    scp.close()

if __name__ == "__main__":
    main()
