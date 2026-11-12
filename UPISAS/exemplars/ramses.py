import platform

from UPISAS.exemplar import Exemplar

# ADDED AFTERWARDS:
# UPISAS/exemplars/ramses.py points UPISAS at http://localhost:50000 and starts the scenario with these settings. 
# Download the image first with docker pull, and use your own architecture in its name.

# arm64 on Apple Silicon Macs, amd64 on Intel/AMD (Windows, Linux, Intel Macs)
ARCH = "arm64" if platform.machine().lower() in ("arm64", "aarch64") else "amd64"


class RAMSES(Exemplar):
    """
    A class which encapsulates a self-adaptive exemplar run in a docker container.
    """
    def __init__(self, auto_start=False, container_name="upisas-demo"):
        docker_config = {
            "name": "simulation-scenario",
            "image": f"giamburrasca/scenario1:{ARCH}",
            "network": "ramses-sas-net",
            "environment": {
                "ADAPT": "0",
                "FAILURE_INJECTION_1_START": "120",
            },
        }

        super().__init__("http://localhost:50000", docker_config, auto_start)

    def start_run(self):
        self.start_container()
