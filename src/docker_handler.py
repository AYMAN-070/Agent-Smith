"""Docker container manager for isolated benchmark evaluation."""

import os
import subprocess
import sys
import time
import uuid


class DockerContainer:
    """Manages Docker container lifecycle for SWE-bench evaluation."""

    def __init__(self, image_name: str) -> None:
        """Initialize Docker container manager with the target image name."""
        self.image_name = image_name
        self.container_id: str | None = None
        self._proc: subprocess.Popen[str] | None = None

    def start(self) -> str:
        """Pull the image if necessary, start the container,
        and link its lifecycle to the parent process.
        """
        subprocess.run(["docker", "pull", self.image_name], check=True)
        container_name = f"sweb_eval_{uuid.uuid4().hex[:12]}"

        # Start container with --rm and open stdin (-i)
        self._proc = subprocess.Popen(
            [
                "docker",
                "run",
                "--rm",
                "-i",
                "--name",
                container_name,
                self.image_name,
                "sh",
                "-c",
                "cat > /dev/null",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        self.container_id = container_name

        # Wait until the container is running and ready for docker exec
        for _ in range(50):
            res = subprocess.run(
                [
                    "docker",
                    "inspect",
                    "-f",
                    "{{.State.Running}}",
                    container_name,
                ],
                capture_output=True,
                text=True,
            )
            if res.stdout.strip() == "true":
                break
            time.sleep(0.1)

        # Launch a detached watchdog process to ensure cleanup even after kill -9
        ppid = os.getpid()
        watchdog_code = (
            f"import os, time, subprocess\n"
            f"ppid = {ppid}\n"
            f"cname = '{container_name}'\n"
            f"while True:\n"
            f"    try:\n"
            f"        os.kill(ppid, 0)\n"
            f"    except OSError:\n"
            f"        subprocess.run(['docker', 'rm', '-f', cname], "
            f"stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
            f"        break\n"
            f"    time.sleep(1)\n"
        )
        subprocess.Popen(
            [sys.executable, "-c", watchdog_code],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        return self.container_id

    def write_file(self, path_in_container: str, content: str) -> None:
        """Writes text content into a file inside the container."""
        if not self.container_id:
            raise RuntimeError("Container is not running.")
        subprocess.run(
            [
                "docker",
                "exec",
                "-i",
                self.container_id,
                "tee",
                path_in_container,
            ],
            input=content,
            text=True,
            check=True,
            stdout=subprocess.DEVNULL,
        )

    def setup_eval_script(self, script_content: str) -> None:
        """Injects eval script into /eval.sh and marks it executable."""
        self.write_file("/eval.sh", script_content)
        if not self.container_id:
            raise RuntimeError("Container is not running.")
        subprocess.run(
            ["docker", "exec", self.container_id, "chmod", "+x", "/eval.sh"],
            check=True,
        )

    def stop_and_remove(self) -> None:
        """Stops and removes the container to guarantee clean workspace."""
        if self.container_id:
            subprocess.run(
                ["docker", "rm", "-f", self.container_id],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if self._proc:
                try:
                    if self._proc.stdin:
                        self._proc.stdin.close()
                    self._proc.terminate()
                except Exception:
                    pass
                self._proc = None
            self.container_id = None
