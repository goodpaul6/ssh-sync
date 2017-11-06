import time, os
from paramiko import SSHClient, ssh_exception
import argparse, scp, getpass
from scp import SCPClient, SCPException

scp = None

def copy_to_remote(local_path, remote_path):
    scp.put(local_path, remote_path=remote_path, preserve_times=True, recursive=True)

def copy_from_remote(local_path, remote_path):
    scp.get(remote_path, local_path=local_path, preserve_times=True, recursive=True)

def get_mod_times(dir_path):
    times = {}

    for dirname, subdirnames, filenames in os.walk(dir_path):
        for filename in filenames:
            path = os.path.join(dirname, filename)
            mod_time = os.path.getmtime(path)

            times[path] = mod_time

    return times

def main():
    parser = argparse.ArgumentParser(description="Tool for synchronizing changes between local filesystem and remote shell")

    parser.add_argument("-u", "--user-id", type=str, required=True, help="Your user id.")
    parser.add_argument("-r", "--remote-domain", type=str, required=True, help="Remote machine domain.")
    parser.add_argument("-w", "--wait-time", type=int, default=5, help="Number of seconds between each sync.")
    parser.add_argument("-d", "--remote-dir", type=str, required=True, help="Remote path to directory to sync (MUST be absolute).")
    parser.add_argument("-c", "--copy", action="store_true", help="Copies remote directory to current directory.")
    parser.add_argument("-t", "--transfer", action="store_true", help="Copies local directory to remote.")
    parser.add_argument("--assume-sync", action="store_true", help="Do not force synchronization at startup.")
    parser.add_argument("-k", "--keep-alive", action="store_true", help="Attempt to reconnect if SSH session is forcibly closed by remote host.")
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

    if args.copy and args.transfer:
        print("ERROR: Cannot --copy and --transfer. Pick one.")
        return
    
    if args.copy:
        print("Copying directory from remote...")
        copy_from_remote(".", args.remote_dir)
        print("Successfully copied directory from remote.")
    elif args.transfer:
        print("Copying directory to remote...")
        copy_to_remote(local_dir, args.remote_dir)
        print("Successfully copied directory to remote.")
    else:
        if not args.assume_sync:
            print("ERROR: Must either copy remote directory or transfer local directory on startup. Specify '-c' or '-t' respectively. Alternatively, specify '--assume-sync'.")
            return
        else:
            print("WARNING: Assuming local and remote directories are synchronized.")

    if not os.path.exists(local_dir):
        print("ERROR: No local copy exists. Invoke with '-c'.".format(local_dir))
        return

    prev_times = get_mod_times(local_dir)

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

    def loop():
        while True:
            if args.verbose:
                print("Polling for changes...")

            cur_times = get_mod_times(local_dir)
            
            nonlocal prev_times

            # Check for deleted files
            for path in prev_times:
                if not path in cur_times:
                    remote_path = "{}/{}".format(remote_dir_dir, path.replace("\\", "/"))

                    print("Detected file '{}' was deleted, deleting on remote machine...".format(path))
                    _, _, stderr = ssh.exec_command("rm {}".format(remote_path))

                    lines = list(stderr.readlines())
                    if len(lines):
                        print("ERROR:")
                        for line in lines:
                            print(line, end='')
                    else:
                        print("Successfully deleted file on remote machine.")

            # Synchronize and add files
            for path in cur_times:
                dirname = os.path.dirname(path)
                filename = os.path.basename(path)
                remote_path = "{}/{}".format(remote_dir_dir, path.replace("\\", "/"))

                if filename.endswith(".swp") or filename.endswith(".swm"): continue

                if path in prev_times:
                    if prev_times[path] < cur_times[path]:
                        if filename == ".command":
                            print("Detected change in command file in '{}'".format(dirname))
                            run_command_file(path, dirname)
                        else:
                            print("Detected change in '{}', copying to remote...".format(path))
                            copy_to_remote(path, remote_path)
                            print("Successfully copied to remote.")
                else:
                    if filename == ".command":
                        print("Detected  command file in '{}'".format(dirname))
                        print("Modify this to run it.")
                    else:
                        print("Detected new file '{}', copying to remote...".format(path))
                        copy_to_remote(path, remote_path)
                        print("Successfully copied to remote.")

            prev_times = cur_times

            if args.verbose:
                print("Waiting...")
            time.sleep(args.wait_time)

    try:
        loop()
    except (ssh_exception.SSHException, SCPException, ConnectionResetError):
        if args.keep_alive:
            print("Encountered SSH Error")
            print("Attempting to reconnect...")
            ssh.connect(args.remote_domain, username=args.user_id, password=args.password)
            print("Successfully reconnected.")
            loop()

    scp.close()

if __name__ == "__main__":
    main()
