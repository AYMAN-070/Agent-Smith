"""Docker container manager for isolated benchmark evaluation."""

import subprocess


class DockerContainer:
    """Manages Docker container lifecycle for SWE-bench evaluation."""

    def __init__(self, image_name: str) -> None:
        """Initialize Docker container manager with the target image name."""
        self.image_name = image_name
        self.container_id: str | None = None

    def start(self) -> str:
        """Pulls the image if necessary, starts the container,
        and keeps it alive with tail -f /dev/null."""
        subprocess.run(["docker", "pull", self.image_name], check=True)
        res = subprocess.run(
            [
                "docker",
                "run",
                "-d",
                self.image_name,
                "tail",
                "-f",
                "/dev/null",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        self.container_id = res.stdout.strip()
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
                ["docker", "rm", "-f", self.container_id], check=False
            )
            self.container_id = None
